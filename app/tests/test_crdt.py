"""Tests for CRDT implementations."""

import pytest
from datetime import datetime
from app.state.crdt import (
    LWWRegister,
    GCounter,
    ORSet,
    CRDTMap,
    VectorClock,
    Timestamp,
)


class TestVectorClock:
    """Tests for VectorClock."""

    def test_increment(self):
        """Test incrementing a vector clock."""
        vc = VectorClock()
        vc.increment("node1")
        assert vc.clock["node1"] == 1
        
        vc.increment("node1")
        assert vc.clock["node1"] == 2
        
        vc.increment("node2")
        assert vc.clock["node2"] == 1

    def test_merge(self):
        """Test merging vector clocks."""
        vc1 = VectorClock(clock={"node1": 2, "node2": 1})
        vc2 = VectorClock(clock={"node1": 1, "node2": 3, "node3": 1})
        
        vc1.merge(vc2)
        
        assert vc1.clock["node1"] == 2
        assert vc1.clock["node2"] == 3
        assert vc1.clock["node3"] == 1

    def test_happens_before(self):
        """Test happens-before relationship."""
        vc1 = VectorClock(clock={"node1": 1, "node2": 0})
        vc2 = VectorClock(clock={"node1": 2, "node2": 0})
        
        assert vc1.happens_before(vc2)
        assert not vc2.happens_before(vc1)

    def test_concurrent_with(self):
        """Test concurrent relationship."""
        vc1 = VectorClock(clock={"node1": 1, "node2": 0})
        vc2 = VectorClock(clock={"node1": 0, "node2": 1})
        
        assert vc1.concurrent_with(vc2)
        assert vc2.concurrent_with(vc1)

    def test_copy(self):
        """Test copying a vector clock."""
        vc1 = VectorClock(clock={"node1": 1, "node2": 2})
        vc2 = vc1.copy()
        
        assert vc1.clock == vc2.clock
        assert vc1.clock is not vc2.clock  # Different objects


class TestLWWRegister:
    """Tests for Last-Write-Wins Register."""

    def test_set_and_get(self):
        """Test setting and getting values."""
        register = LWWRegister(node_id="node1")
        register.set("value1")
        
        assert register.value() == "value1"

    def test_lww_semantics_wall_clock(self):
        """Test LWW semantics based on wall clock."""
        register = LWWRegister(node_id="node1")
        
        # Set initial value
        vc1 = VectorClock()
        vc1.increment("node1")
        ts1 = Timestamp(vector_clock=vc1, wall_clock=100.0, node_id="node1")
        register.set("value1", ts1)
        
        # Set newer value
        vc2 = VectorClock()
        vc2.increment("node1")
        ts2 = Timestamp(vector_clock=vc2, wall_clock=200.0, node_id="node1")
        register.set("value2", ts2)
        
        assert register.value() == "value2"

    def test_lww_semantics_node_id_tiebreaker(self):
        """Test LWW semantics with node_id tiebreaker."""
        register = LWWRegister(node_id="node1")
        
        # Set value from node1
        vc1 = VectorClock()
        vc1.increment("node1")
        ts1 = Timestamp(vector_clock=vc1, wall_clock=100.0, node_id="node1")
        register.set("value1", ts1)
        
        # Set value from node2 with same wall clock
        vc2 = VectorClock()
        vc2.increment("node2")
        ts2 = Timestamp(vector_clock=vc2, wall_clock=100.0, node_id="node2")
        register.set("value2", ts2)
        
        # node2 > node1, so value2 should win
        assert register.value() == "value2"

    def test_merge(self):
        """Test merging two registers."""
        register1 = LWWRegister(node_id="node1")
        register2 = LWWRegister(node_id="node2")
        
        vc1 = VectorClock()
        vc1.increment("node1")
        ts1 = Timestamp(vector_clock=vc1, wall_clock=100.0, node_id="node1")
        register1.set("value1", ts1)
        
        vc2 = VectorClock()
        vc2.increment("node2")
        ts2 = Timestamp(vector_clock=vc2, wall_clock=200.0, node_id="node2")
        register2.set("value2", ts2)
        
        register1.merge(register2)
        
        # value2 has later timestamp, so it should win
        assert register1.value() == "value2"

    def test_serialization(self):
        """Test serialization and deserialization."""
        register = LWWRegister(node_id="node1")
        register.set("test_value")
        
        data = register.to_dict()
        restored = LWWRegister.from_dict(data)
        
        assert restored.value() == "test_value"
        assert restored.node_id == "node1"


class TestGCounter:
    """Tests for Grow-only Counter."""

    def test_increment(self):
        """Test incrementing counter."""
        counter = GCounter(node_id="node1")
        counter.increment()
        
        assert counter.value() == 1
        
        counter.increment(5)
        assert counter.value() == 6

    def test_increment_negative_raises_error(self):
        """Test that negative increments raise error."""
        counter = GCounter(node_id="node1")
        
        with pytest.raises(ValueError):
            counter.increment(-1)

    def test_merge(self):
        """Test merging two counters."""
        counter1 = GCounter(node_id="node1")
        counter2 = GCounter(node_id="node2")
        
        counter1.increment(3)
        counter2.increment(5)
        
        counter1.merge(counter2)
        
        # Total should be 3 + 5 = 8
        assert counter1.value() == 8

    def test_merge_idempotent(self):
        """Test that merge is idempotent."""
        counter1 = GCounter(node_id="node1")
        counter2 = GCounter(node_id="node2")
        
        counter1.increment(3)
        counter2.increment(5)
        
        counter1.merge(counter2)
        value_after_first_merge = counter1.value()
        
        counter1.merge(counter2)
        value_after_second_merge = counter1.value()
        
        assert value_after_first_merge == value_after_second_merge

    def test_serialization(self):
        """Test serialization and deserialization."""
        counter = GCounter(node_id="node1")
        counter.increment(10)
        
        data = counter.to_dict()
        restored = GCounter.from_dict(data)
        
        assert restored.value() == 10
        assert restored.node_id == "node1"


class TestORSet:
    """Tests for Observed-Remove Set."""

    def test_add(self):
        """Test adding elements to set."""
        orset = ORSet(node_id="node1")
        
        id1 = orset.add("element1")
        id2 = orset.add("element2")
        
        assert "element1" in orset.value()
        assert "element2" in orset.value()
        assert len(orset.value()) == 2

    def test_remove_specific(self):
        """Test removing specific element instance."""
        orset = ORSet(node_id="node1")
        
        id1 = orset.add("element1")
        id2 = orset.add("element1")  # Add same element twice
        
        assert len(orset.value()) == 1
        assert "element1" in orset.value()
        
        orset.remove("element1", id1)
        
        # Element should still be in set because id2 is still there
        assert "element1" in orset.value()

    def test_remove_all(self):
        """Test removing all instances of an element."""
        orset = ORSet(node_id="node1")
        
        id1 = orset.add("element1")
        id2 = orset.add("element1")
        
        orset.remove("element1")
        
        assert "element1" not in orset.value()

    def test_merge(self):
        """Test merging two sets."""
        orset1 = ORSet(node_id="node1")
        orset2 = ORSet(node_id="node2")
        
        orset1.add("element1")
        orset2.add("element2")
        
        orset1.merge(orset2)
        
        assert "element1" in orset1.value()
        assert "element2" in orset1.value()

    def test_merge_commutative(self):
        """Test that merge is commutative."""
        orset1 = ORSet(node_id="node1")
        orset2 = ORSet(node_id="node2")
        
        orset1.add("element1")
        orset2.add("element2")
        
        orset1_copy = ORSet(node_id="node1")
        orset1_copy.add("element1")
        
        orset1.merge(orset2)
        orset2.merge(orset1_copy)
        
        assert orset1.value() == orset2.value()

    def test_serialization(self):
        """Test serialization and deserialization."""
        orset = ORSet(node_id="node1")
        orset.add("element1")
        orset.add("element2")
        
        data = orset.to_dict()
        restored = ORSet.from_dict(data)
        
        assert restored.value() == orset.value()


class TestCRDTMap:
    """Tests for CRDT Map."""

    def test_set_and_get(self):
        """Test setting and getting values."""
        crdt_map = CRDTMap(node_id="node1")
        crdt_map.set("key1", "value1")
        
        assert crdt_map.get("key1") == "value1"

    def test_remove(self):
        """Test removing keys."""
        crdt_map = CRDTMap(node_id="node1")
        crdt_map.set("key1", "value1")
        crdt_map.remove("key1")
        
        assert crdt_map.get("key1") is None

    def test_merge(self):
        """Test merging two maps."""
        map1 = CRDTMap(node_id="node1")
        map2 = CRDTMap(node_id="node2")
        
        map1.set("key1", "value1")
        map2.set("key2", "value2")
        
        map1.merge(map2)
        
        assert map1.get("key1") == "value1"
        assert map1.get("key2") == "value2"

    def test_merge_conflict_resolution(self):
        """Test merge with conflicting values."""
        map1 = CRDTMap(node_id="node1")
        map2 = CRDTMap(node_id="node2")
        
        map1.set("key1", "value1")
        map2.set("key1", "value2")
        
        map1.merge(map2)
        
        # Should have one of the values (LWW semantics)
        assert map1.get("key1") in ["value1", "value2"]

    def test_value_returns_dict(self):
        """Test that value() returns a dictionary."""
        crdt_map = CRDTMap(node_id="node1")
        crdt_map.set("key1", "value1")
        crdt_map.set("key2", "value2")
        
        result = crdt_map.value()
        
        assert isinstance(result, dict)
        assert result["key1"] == "value1"
        assert result["key2"] == "value2"

    def test_serialization(self):
        """Test serialization and deserialization."""
        crdt_map = CRDTMap(node_id="node1")
        crdt_map.set("key1", "value1")
        crdt_map.set("key2", "value2")
        
        data = crdt_map.to_dict()
        restored = CRDTMap.from_dict(data)
        
        assert restored.get("key1") == "value1"
        assert restored.get("key2") == "value2"


class TestCRDTProperties:
    """Property-based tests for CRDT correctness properties."""

    def test_property_5_crdt_state_convergence(self):
        """Property 5: CRDT State Convergence.
        
        **Validates: Requirements 16, 21**
        
        For any concurrent updates across edge devices, the CRDT state should
        converge to the same value across all replicas within 1 second.
        """
        # Create three replicas
        map1 = CRDTMap(node_id="device1")
        map2 = CRDTMap(node_id="device2")
        map3 = CRDTMap(node_id="device3")
        
        # Perform concurrent updates
        map1.set("device_status", "online")
        map2.set("device_status", "offline")
        map3.set("device_status", "error")
        
        # Merge all states
        map1.merge(map2)
        map1.merge(map3)
        
        map2.merge(map1)
        map2.merge(map3)
        
        map3.merge(map1)
        map3.merge(map2)
        
        # All replicas should converge to the same state
        final_state1 = map1.value()
        final_state2 = map2.value()
        final_state3 = map3.value()
        
        assert final_state1 == final_state2 == final_state3

    def test_property_5_merge_idempotent(self):
        """Test that CRDT merge is idempotent.
        
        Merging the same state multiple times should produce the same result.
        """
        map1 = CRDTMap(node_id="device1")
        map2 = CRDTMap(node_id="device2")
        
        map1.set("key1", "value1")
        map2.set("key2", "value2")
        
        # First merge
        map1.merge(map2)
        state_after_first = map1.value().copy()
        
        # Second merge (idempotent)
        map1.merge(map2)
        state_after_second = map1.value().copy()
        
        assert state_after_first == state_after_second

    def test_property_5_merge_commutative(self):
        """Test that CRDT merge is commutative.
        
        The order of merges should not affect the final state.
        """
        # First order: map1 merge map2, then merge map3
        map1a = CRDTMap(node_id="device1")
        map2a = CRDTMap(node_id="device2")
        map3a = CRDTMap(node_id="device3")
        
        map1a.set("key1", "value1")
        map2a.set("key2", "value2")
        map3a.set("key3", "value3")
        
        map1a.merge(map2a)
        map1a.merge(map3a)
        
        # Second order: map1 merge map3, then merge map2
        map1b = CRDTMap(node_id="device1")
        map2b = CRDTMap(node_id="device2")
        map3b = CRDTMap(node_id="device3")
        
        map1b.set("key1", "value1")
        map2b.set("key2", "value2")
        map3b.set("key3", "value3")
        
        map1b.merge(map3b)
        map1b.merge(map2b)
        
        # Final states should be the same
        assert map1a.value() == map1b.value()

    def test_property_5_concurrent_updates_converge(self):
        """Test that concurrent updates from multiple devices converge.
        
        Simulates multiple devices making concurrent updates to the same key.
        """
        devices = [CRDTMap(node_id=f"device{i}") for i in range(5)]
        
        # Each device updates the same key with different values
        for i, device in enumerate(devices):
            device.set("shared_state", f"value{i}")
        
        # Simulate network propagation - each device receives updates from all others
        for device in devices:
            for other_device in devices:
                if device.node_id != other_device.node_id:
                    device.merge(other_device)
        
        # All devices should have the same final state
        final_states = [device.value() for device in devices]
        
        # All should be equal
        for state in final_states[1:]:
            assert state == final_states[0]
