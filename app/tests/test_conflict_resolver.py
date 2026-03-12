"""Tests for conflict resolution logic."""

import pytest
from datetime import datetime
from app.state.conflict_resolver import (
    ConflictResolver,
    ConflictInfo,
    ConflictType,
)
from app.state.crdt import VectorClock, Timestamp


class TestConflictResolver:
    """Tests for ConflictResolver."""

    def test_detect_no_conflict(self):
        """Test detecting when there's no conflict."""
        resolver = ConflictResolver(node_id="node1")
        
        conflict = resolver.detect_conflict(
            key="device_status",
            local_value="online",
            remote_value="online",
        )
        
        assert conflict is None

    def test_detect_concurrent_write_conflict(self):
        """Test detecting concurrent write conflicts."""
        resolver = ConflictResolver(node_id="node1")
        
        conflict = resolver.detect_conflict(
            key="device_status",
            local_value="online",
            remote_value="offline",
        )
        
        assert conflict is not None
        assert conflict.conflict_type == ConflictType.CONCURRENT_WRITE

    def test_detect_device_in_multiple_cells_conflict(self):
        """Test detecting device in multiple cells conflict."""
        resolver = ConflictResolver(node_id="node1")
        
        conflict = resolver.detect_conflict(
            key="device_cell_assignment",
            local_value="cell_1",
            remote_value="cell_2",
        )
        
        assert conflict is not None
        assert conflict.conflict_type == ConflictType.DEVICE_IN_MULTIPLE_CELLS

    def test_resolve_with_crdt_merge_wall_clock(self):
        """Test resolving with CRDT merge using wall clock."""
        resolver = ConflictResolver(node_id="node1")
        
        vc1 = VectorClock()
        vc1.increment("node1")
        local_ts = Timestamp(vector_clock=vc1, wall_clock=100.0, node_id="node1")
        
        vc2 = VectorClock()
        vc2.increment("node2")
        remote_ts = Timestamp(vector_clock=vc2, wall_clock=200.0, node_id="node2")
        
        conflict = ConflictInfo(
            conflict_type=ConflictType.CONCURRENT_WRITE,
            key="device_status",
            local_value="offline",
            remote_value="online",
            local_timestamp=local_ts,
            remote_timestamp=remote_ts,
        )
        
        resolved = resolver.resolve_conflict(conflict, strategy="crdt_merge")
        
        # Remote has later timestamp, so it should win
        assert resolved == "online"

    def test_resolve_with_crdt_merge_node_id_tiebreaker(self):
        """Test resolving with CRDT merge using node_id tiebreaker."""
        resolver = ConflictResolver(node_id="node1")
        
        vc1 = VectorClock()
        vc1.increment("node1")
        local_ts = Timestamp(vector_clock=vc1, wall_clock=100.0, node_id="node1")
        
        vc2 = VectorClock()
        vc2.increment("node2")
        remote_ts = Timestamp(vector_clock=vc2, wall_clock=100.0, node_id="node2")
        
        conflict = ConflictInfo(
            conflict_type=ConflictType.CONCURRENT_WRITE,
            key="device_status",
            local_value="offline",
            remote_value="online",
            local_timestamp=local_ts,
            remote_timestamp=remote_ts,
        )
        
        resolved = resolver.resolve_conflict(conflict, strategy="crdt_merge")
        
        # Same wall clock, node2 > node1, so remote should win
        assert resolved == "online"

    def test_resolve_with_timestamp_strategy(self):
        """Test resolving with timestamp strategy."""
        resolver = ConflictResolver(node_id="node1")
        
        vc1 = VectorClock()
        vc1.increment("node1")
        local_ts = Timestamp(vector_clock=vc1, wall_clock=100.0, node_id="node1")
        
        vc2 = VectorClock()
        vc2.increment("node2")
        remote_ts = Timestamp(vector_clock=vc2, wall_clock=200.0, node_id="node2")
        
        conflict = ConflictInfo(
            conflict_type=ConflictType.CONCURRENT_WRITE,
            key="device_status",
            local_value="offline",
            remote_value="online",
            local_timestamp=local_ts,
            remote_timestamp=remote_ts,
        )
        
        resolved = resolver.resolve_conflict(conflict, strategy="timestamp_based")
        
        assert resolved == "online"

    def test_resolve_with_local_wins_strategy(self):
        """Test resolving with local_wins strategy."""
        resolver = ConflictResolver(node_id="node1")
        
        conflict = ConflictInfo(
            conflict_type=ConflictType.CONCURRENT_WRITE,
            key="device_status",
            local_value="offline",
            remote_value="online",
        )
        
        resolved = resolver.resolve_conflict(conflict, strategy="local_wins")
        
        assert resolved == "offline"

    def test_resolve_with_remote_wins_strategy(self):
        """Test resolving with remote_wins strategy."""
        resolver = ConflictResolver(node_id="node1")
        
        conflict = ConflictInfo(
            conflict_type=ConflictType.CONCURRENT_WRITE,
            key="device_status",
            local_value="offline",
            remote_value="online",
        )
        
        resolved = resolver.resolve_conflict(conflict, strategy="remote_wins")
        
        assert resolved == "online"

    def test_resolution_history(self):
        """Test that resolution history is recorded."""
        resolver = ConflictResolver(node_id="node1")
        
        conflict = ConflictInfo(
            conflict_type=ConflictType.CONCURRENT_WRITE,
            key="device_status",
            local_value="offline",
            remote_value="online",
        )
        
        resolver.resolve_conflict(conflict, strategy="remote_wins")
        
        history = resolver.get_resolution_history()
        
        assert len(history) == 1
        assert history[0]["key"] == "device_status"
        assert history[0]["resolved_value"] == "online"

    def test_validate_hierarchy_consistency_no_conflicts(self):
        """Test validating hierarchy with no conflicts."""
        resolver = ConflictResolver(node_id="node1")
        
        hierarchy = {
            "cell_1": {"devices": ["device_1", "device_2"]},
            "cell_2": {"devices": ["device_3", "device_4"]},
        }
        
        conflicts = resolver.validate_hierarchy_consistency(hierarchy)
        
        assert len(conflicts) == 0

    def test_validate_hierarchy_consistency_device_in_multiple_cells(self):
        """Test validating hierarchy with device in multiple cells."""
        resolver = ConflictResolver(node_id="node1")
        
        hierarchy = {
            "cell_1": {"devices": ["device_1", "device_2"]},
            "cell_2": {"devices": ["device_2", "device_3"]},  # device_2 in both cells
        }
        
        conflicts = resolver.validate_hierarchy_consistency(hierarchy)
        
        assert len(conflicts) > 0
        assert conflicts[0].conflict_type == ConflictType.DEVICE_IN_MULTIPLE_CELLS

    def test_serialization(self):
        """Test serialization and deserialization."""
        resolver = ConflictResolver(node_id="node1")
        
        conflict = ConflictInfo(
            conflict_type=ConflictType.CONCURRENT_WRITE,
            key="device_status",
            local_value="offline",
            remote_value="online",
        )
        
        resolver.resolve_conflict(conflict, strategy="remote_wins")
        
        data = resolver.to_dict()
        restored = ConflictResolver.from_dict(data)
        
        assert restored.node_id == "node1"
        assert len(restored.get_resolution_history()) == 1


class TestConflictResolverProperties:
    """Property-based tests for conflict resolution."""

    def test_property_10_conflict_resolution_deterministic(self):
        """Test that conflict resolution is deterministic.
        
        Resolving the same conflict multiple times should produce the same result.
        """
        resolver = ConflictResolver(node_id="node1")
        
        vc1 = VectorClock()
        vc1.increment("node1")
        local_ts = Timestamp(vector_clock=vc1, wall_clock=100.0, node_id="node1")
        
        vc2 = VectorClock()
        vc2.increment("node2")
        remote_ts = Timestamp(vector_clock=vc2, wall_clock=200.0, node_id="node2")
        
        conflict = ConflictInfo(
            conflict_type=ConflictType.CONCURRENT_WRITE,
            key="device_status",
            local_value="offline",
            remote_value="online",
            local_timestamp=local_ts,
            remote_timestamp=remote_ts,
        )
        
        # Resolve multiple times
        result1 = resolver.resolve_conflict(conflict, strategy="crdt_merge")
        result2 = resolver.resolve_conflict(conflict, strategy="crdt_merge")
        result3 = resolver.resolve_conflict(conflict, strategy="crdt_merge")
        
        # All results should be the same
        assert result1 == result2 == result3

    def test_property_10_conflict_resolution_consistent_across_nodes(self):
        """Test that conflict resolution is consistent across nodes.
        
        Different nodes resolving the same conflict should reach the same conclusion.
        """
        resolver1 = ConflictResolver(node_id="node1")
        resolver2 = ConflictResolver(node_id="node2")
        
        vc1 = VectorClock()
        vc1.increment("node1")
        local_ts = Timestamp(vector_clock=vc1, wall_clock=100.0, node_id="node1")
        
        vc2 = VectorClock()
        vc2.increment("node2")
        remote_ts = Timestamp(vector_clock=vc2, wall_clock=200.0, node_id="node2")
        
        conflict = ConflictInfo(
            conflict_type=ConflictType.CONCURRENT_WRITE,
            key="device_status",
            local_value="offline",
            remote_value="online",
            local_timestamp=local_ts,
            remote_timestamp=remote_ts,
        )
        
        # Both nodes resolve the same conflict
        result1 = resolver1.resolve_conflict(conflict, strategy="crdt_merge")
        result2 = resolver2.resolve_conflict(conflict, strategy="crdt_merge")
        
        # Both should reach the same conclusion
        assert result1 == result2

    def test_property_10_hierarchy_consistency_validation(self):
        """Test that hierarchy consistency validation detects all conflicts.
        
        For any hierarchy with devices in multiple cells, the validator should
        detect all such conflicts.
        """
        resolver = ConflictResolver(node_id="node1")
        
        # Create a hierarchy with multiple conflicts
        hierarchy = {
            "cell_1": {"devices": ["device_1", "device_2", "device_3"]},
            "cell_2": {"devices": ["device_2", "device_4"]},  # device_2 conflict
            "cell_3": {"devices": ["device_3", "device_5"]},  # device_3 conflict
            "cell_4": {"devices": ["device_6"]},
        }
        
        conflicts = resolver.validate_hierarchy_consistency(hierarchy)
        
        # Should detect at least 2 conflicts (device_2 and device_3)
        assert len(conflicts) >= 2
        
        # All conflicts should be of type DEVICE_IN_MULTIPLE_CELLS
        for conflict in conflicts:
            assert conflict.conflict_type == ConflictType.DEVICE_IN_MULTIPLE_CELLS
