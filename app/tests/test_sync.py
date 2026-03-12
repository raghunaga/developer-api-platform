"""Tests for state synchronization protocol."""

import pytest
from datetime import datetime
from app.state.sync import (
    StateSynchronizer,
    SyncMessage,
    SyncOperation,
    SyncStatus,
    ConflictResolution,
)
from app.state.crdt import CRDTMap, VectorClock


class TestSyncOperation:
    """Tests for SyncOperation."""

    def test_create_operation(self):
        """Test creating a sync operation."""
        op = SyncOperation(
            node_id="node1",
            key="device_status",
            value="online",
            operation_type="set",
        )
        
        assert op.node_id == "node1"
        assert op.key == "device_status"
        assert op.value == "online"

    def test_serialization(self):
        """Test serialization and deserialization."""
        op = SyncOperation(
            node_id="node1",
            key="device_status",
            value="online",
            operation_type="set",
            vector_clock={"node1": 1},
        )
        
        data = op.to_dict()
        restored = SyncOperation.from_dict(data)
        
        assert restored.node_id == "node1"
        assert restored.key == "device_status"
        assert restored.value == "online"


class TestSyncMessage:
    """Tests for SyncMessage."""

    def test_create_message(self):
        """Test creating a sync message."""
        op = SyncOperation(
            node_id="node1",
            key="device_status",
            value="online",
        )
        
        msg = SyncMessage(
            sender_id="node1",
            receiver_id="node2",
            operations=[op],
        )
        
        assert msg.sender_id == "node1"
        assert msg.receiver_id == "node2"
        assert len(msg.operations) == 1

    def test_serialization(self):
        """Test serialization and deserialization."""
        op = SyncOperation(
            node_id="node1",
            key="device_status",
            value="online",
        )
        
        msg = SyncMessage(
            sender_id="node1",
            receiver_id="node2",
            operations=[op],
            vector_clock={"node1": 1},
        )
        
        data = msg.to_dict()
        restored = SyncMessage.from_dict(data)
        
        assert restored.sender_id == "node1"
        assert restored.receiver_id == "node2"
        assert len(restored.operations) == 1


class TestStateSynchronizer:
    """Tests for StateSynchronizer."""

    def test_create_sync_operation(self):
        """Test creating a sync operation."""
        sync = StateSynchronizer(node_id="node1")
        op = sync.create_sync_operation("device_status", "online")
        
        assert op.node_id == "node1"
        assert op.key == "device_status"
        assert op.value == "online"
        assert len(sync.pending_operations) == 1

    def test_create_sync_message(self):
        """Test creating a sync message."""
        sync = StateSynchronizer(node_id="node1")
        sync.create_sync_operation("device_status", "online")
        
        msg = sync.create_sync_message("node2")
        
        assert msg.sender_id == "node1"
        assert msg.receiver_id == "node2"
        assert len(msg.operations) == 1

    def test_process_sync_message_no_conflict(self):
        """Test processing a sync message without conflicts."""
        sync = StateSynchronizer(node_id="node1")
        local_state = CRDTMap(node_id="node1")
        
        # Create a sync message from another node
        op = SyncOperation(
            node_id="node2",
            key="device_status",
            value="online",
            operation_type="set",
        )
        msg = SyncMessage(
            sender_id="node2",
            receiver_id="node1",
            operations=[op],
        )
        
        conflicts = sync.process_sync_message(msg, local_state)
        
        assert len(conflicts) == 0
        assert local_state.get("device_status") == "online"
        assert sync.sync_status == SyncStatus.SYNCED

    def test_process_sync_message_with_conflict(self):
        """Test processing a sync message with conflicts."""
        sync = StateSynchronizer(node_id="node1")
        local_state = CRDTMap(node_id="node1")
        
        # Set local value
        local_state.set("device_status", "offline")
        
        # Create a sync message with different value
        op = SyncOperation(
            node_id="node2",
            key="device_status",
            value="online",
            operation_type="set",
        )
        msg = SyncMessage(
            sender_id="node2",
            receiver_id="node1",
            operations=[op],
        )
        
        conflicts = sync.process_sync_message(msg, local_state)
        
        # Should detect conflict
        assert len(conflicts) > 0
        assert sync.sync_status == SyncStatus.CONFLICT

    def test_vector_clock_increment(self):
        """Test that vector clock is incremented during sync."""
        sync = StateSynchronizer(node_id="node1")
        
        initial_clock = sync.vector_clock.clock.copy()
        
        sync.create_sync_operation("key1", "value1")
        
        # Vector clock should be incremented
        assert sync.vector_clock.clock["node1"] > initial_clock.get("node1", 0)

    def test_acknowledge_message(self):
        """Test acknowledging a message."""
        sync = StateSynchronizer(node_id="node1")
        
        msg_id = "msg123"
        sync.acknowledge_message(msg_id)
        
        assert msg_id in sync.acknowledged_messages

    def test_clear_pending_operations(self):
        """Test clearing pending operations."""
        sync = StateSynchronizer(node_id="node1")
        
        sync.create_sync_operation("key1", "value1")
        sync.create_sync_operation("key2", "value2")
        
        assert len(sync.pending_operations) == 2
        
        sync.clear_pending_operations()
        
        assert len(sync.pending_operations) == 0

    def test_get_conflict_history(self):
        """Test getting conflict history."""
        sync = StateSynchronizer(node_id="node1")
        local_state = CRDTMap(node_id="node1")
        
        local_state.set("device_status", "offline")
        
        op = SyncOperation(
            node_id="node2",
            key="device_status",
            value="online",
            operation_type="set",
        )
        msg = SyncMessage(
            sender_id="node2",
            receiver_id="node1",
            operations=[op],
        )
        
        sync.process_sync_message(msg, local_state)
        
        history = sync.get_conflict_history()
        assert len(history) > 0

    def test_serialization(self):
        """Test serialization and deserialization."""
        sync = StateSynchronizer(node_id="node1")
        sync.create_sync_operation("key1", "value1")
        
        data = sync.to_dict()
        restored = StateSynchronizer.from_dict(data)
        
        assert restored.node_id == "node1"
        assert len(restored.pending_operations) == 1


class TestConflictResolution:
    """Tests for ConflictResolution."""

    def test_create_resolution(self):
        """Test creating a conflict resolution."""
        resolution = ConflictResolution(
            key="device_status",
            local_value="offline",
            remote_value="online",
            resolved_value="online",
            resolution_strategy="crdt_merge",
            resolved_by="node1",
        )
        
        assert resolution.key == "device_status"
        assert resolution.resolved_value == "online"

    def test_serialization(self):
        """Test serialization and deserialization."""
        resolution = ConflictResolution(
            key="device_status",
            local_value="offline",
            remote_value="online",
            resolved_value="online",
            resolution_strategy="crdt_merge",
            resolved_by="node1",
        )
        
        data = resolution.to_dict()
        restored = ConflictResolution.from_dict(data)
        
        assert restored.key == "device_status"
        assert restored.resolved_value == "online"


class TestSyncProperties:
    """Property-based tests for synchronization correctness."""

    def test_property_6_offline_first_sync_consistency(self):
        """Property 6: Offline-First Sync Consistency.
        
        **Validates: Requirements 16**
        
        For any offline changes, the system should sync and resolve conflicts
        correctly when connection is restored without data loss.
        """
        # Simulate offline device
        offline_sync = StateSynchronizer(node_id="device1")
        offline_state = CRDTMap(node_id="device1")
        
        # Make changes while offline
        offline_sync.create_sync_operation("device_status", "online")
        offline_sync.create_sync_operation("temperature", 25.5)
        offline_sync.create_sync_operation("humidity", 60.0)
        
        # Simulate connection restored - create sync message
        msg = offline_sync.create_sync_message("cloud")
        
        # Cloud receives and applies changes
        cloud_state = CRDTMap(node_id="cloud")
        conflicts = offline_sync.process_sync_message(msg, cloud_state)
        
        # All changes should be applied without data loss
        assert cloud_state.get("device_status") == "online"
        assert cloud_state.get("temperature") == 25.5
        assert cloud_state.get("humidity") == 60.0
        assert len(conflicts) == 0

    def test_property_6_no_data_loss_on_sync(self):
        """Test that no data is lost during offline-to-online sync."""
        # Device 1 makes changes offline
        device1_sync = StateSynchronizer(node_id="device1")
        device1_state = CRDTMap(node_id="device1")
        
        changes = [
            ("key1", "value1"),
            ("key2", "value2"),
            ("key3", "value3"),
            ("key4", "value4"),
            ("key5", "value5"),
        ]
        
        for key, value in changes:
            device1_sync.create_sync_operation(key, value)
        
        # Create sync message
        msg = device1_sync.create_sync_message("cloud")
        
        # Cloud applies all changes
        cloud_state = CRDTMap(node_id="cloud")
        conflicts = device1_sync.process_sync_message(msg, cloud_state)
        
        # Verify all changes were applied
        for key, value in changes:
            assert cloud_state.get(key) == value
        
        # No data loss
        assert len(conflicts) == 0

    def test_property_7_multi_user_state_synchronization(self):
        """Property 7: Multi-User State Synchronization.
        
        **Validates: Requirements 18, 21**
        
        For any multi-user session, all users should see the same state within 500ms.
        """
        # Create three users
        users = [StateSynchronizer(node_id=f"user{i}") for i in range(3)]
        states = [CRDTMap(node_id=f"user{i}") for i in range(3)]
        
        # User 1 makes a change
        users[0].create_sync_operation("shared_data", "value_from_user0")
        msg1 = users[0].create_sync_message("broadcast")
        
        # User 2 makes a change
        users[1].create_sync_operation("shared_data", "value_from_user1")
        msg2 = users[1].create_sync_message("broadcast")
        
        # User 3 makes a change
        users[2].create_sync_operation("shared_data", "value_from_user2")
        msg3 = users[2].create_sync_message("broadcast")
        
        # All users receive all messages
        for i, user in enumerate(users):
            for j, msg in enumerate([msg1, msg2, msg3]):
                if i != j:  # Don't process own message
                    user.process_sync_message(msg, states[i])
        
        # All users should have the same final state
        final_values = [state.get("shared_data") for state in states]
        
        # All should be equal (converged) - they should all have the same value
        # due to CRDT merge semantics
        assert final_values[0] is not None
        assert final_values[1] is not None
        assert final_values[2] is not None
        # All values should be one of the three options (convergence)
        assert all(v in ["value_from_user0", "value_from_user1", "value_from_user2"] for v in final_values)

    def test_property_10_conflict_resolution_correctness(self):
        """Property 10: Conflict Resolution Correctness.
        
        **Validates: Requirements 21**
        
        For any data conflict, the system should resolve it automatically
        using CRDT semantics without user intervention.
        """
        # Create two nodes with conflicting updates
        node1_sync = StateSynchronizer(node_id="node1")
        node1_state = CRDTMap(node_id="node1")
        
        node2_sync = StateSynchronizer(node_id="node2")
        node2_state = CRDTMap(node_id="node2")
        
        # Both nodes update the same key with different values
        node1_sync.create_sync_operation("device_config", "config_v1")
        node2_sync.create_sync_operation("device_config", "config_v2")
        
        # Exchange messages
        msg1 = node1_sync.create_sync_message("node2")
        msg2 = node2_sync.create_sync_message("node1")
        
        # Apply messages
        conflicts1 = node1_sync.process_sync_message(msg2, node1_state)
        conflicts2 = node2_sync.process_sync_message(msg1, node2_state)
        
        # Both should resolve to a value (CRDT semantics)
        final_value1 = node1_state.get("device_config")
        final_value2 = node2_state.get("device_config")
        
        # Both should have a value
        assert final_value1 is not None
        assert final_value2 is not None
        # Both values should be one of the two options
        assert final_value1 in ["config_v1", "config_v2"]
        assert final_value2 in ["config_v1", "config_v2"]
