"""CRDT (Conflict-free Replicated Data Type) implementations for distributed state management."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, Optional, Set, TypeVar, List
from uuid import uuid4

T = TypeVar("T")


@dataclass
class VectorClock:
    """Vector clock for tracking causality in distributed systems."""

    clock: Dict[str, int] = field(default_factory=dict)

    def increment(self, node_id: str) -> None:
        """Increment the clock for a node."""
        self.clock[node_id] = self.clock.get(node_id, 0) + 1

    def merge(self, other: "VectorClock") -> None:
        """Merge with another vector clock (take maximum for each node)."""
        for node_id, timestamp in other.clock.items():
            self.clock[node_id] = max(self.clock.get(node_id, 0), timestamp)

    def happens_before(self, other: "VectorClock") -> bool:
        """Check if this clock happens before another."""
        if not self.clock or not other.clock:
            return False
        
        less_or_equal = all(
            self.clock.get(node_id, 0) <= other.clock.get(node_id, 0)
            for node_id in set(self.clock.keys()) | set(other.clock.keys())
        )
        strictly_less = any(
            self.clock.get(node_id, 0) < other.clock.get(node_id, 0)
            for node_id in set(self.clock.keys()) | set(other.clock.keys())
        )
        return less_or_equal and strictly_less

    def concurrent_with(self, other: "VectorClock") -> bool:
        """Check if this clock is concurrent with another."""
        return not self.happens_before(other) and not other.happens_before(self)

    def copy(self) -> "VectorClock":
        """Create a copy of this vector clock."""
        return VectorClock(clock=self.clock.copy())


@dataclass
class Timestamp:
    """Logical timestamp combining vector clock and wall clock."""

    vector_clock: VectorClock
    wall_clock: float  # Unix timestamp
    node_id: str

    def copy(self) -> "Timestamp":
        """Create a copy of this timestamp."""
        return Timestamp(
            vector_clock=self.vector_clock.copy(),
            wall_clock=self.wall_clock,
            node_id=self.node_id,
        )


class CRDT(ABC, Generic[T]):
    """Abstract base class for CRDT implementations."""

    @abstractmethod
    def value(self) -> T:
        """Get the current value of the CRDT."""
        pass

    @abstractmethod
    def merge(self, other: "CRDT[T]") -> None:
        """Merge with another CRDT state."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize CRDT state to dictionary."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CRDT[T]":
        """Deserialize CRDT state from dictionary."""
        pass


@dataclass
class LWWRegister(CRDT[T]):
    """Last-Write-Wins Register - a CRDT that stores a single value.
    
    In case of concurrent writes, the value with the highest timestamp wins.
    If timestamps are equal, the node_id is used as a tiebreaker.
    """

    value_data: Optional[T] = None
    timestamp: Optional[Timestamp] = None
    node_id: str = field(default_factory=lambda: str(uuid4()))

    def set(self, value: T, timestamp: Optional[Timestamp] = None) -> None:
        """Set the value with a timestamp."""
        if timestamp is None:
            vc = VectorClock()
            vc.increment(self.node_id)
            timestamp = Timestamp(
                vector_clock=vc,
                wall_clock=datetime.utcnow().timestamp(),
                node_id=self.node_id,
            )
        
        # Update if this is the first value or if the new timestamp is greater
        if self.timestamp is None or self._is_greater_timestamp(timestamp, self.timestamp):
            self.value_data = value
            self.timestamp = timestamp

    def value(self) -> Optional[T]:
        """Get the current value."""
        return self.value_data

    def merge(self, other: "LWWRegister[T]") -> None:
        """Merge with another LWWRegister."""
        if other.timestamp is None:
            return
        
        if self.timestamp is None:
            self.value_data = other.value_data
            self.timestamp = other.timestamp.copy()
        elif self._is_greater_timestamp(other.timestamp, self.timestamp):
            self.value_data = other.value_data
            self.timestamp = other.timestamp.copy()
        
        # Merge vector clocks
        if self.timestamp and other.timestamp:
            self.timestamp.vector_clock.merge(other.timestamp.vector_clock)

    def _is_greater_timestamp(self, ts1: Timestamp, ts2: Timestamp) -> bool:
        """Check if ts1 is greater than ts2 using LWW semantics."""
        # Compare wall clocks first
        if ts1.wall_clock != ts2.wall_clock:
            return ts1.wall_clock > ts2.wall_clock
        # If equal, use node_id as tiebreaker
        return ts1.node_id > ts2.node_id

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "LWWRegister",
            "value": self.value_data,
            "timestamp": {
                "vector_clock": self.timestamp.vector_clock.clock if self.timestamp else {},
                "wall_clock": self.timestamp.wall_clock if self.timestamp else 0,
                "node_id": self.timestamp.node_id if self.timestamp else "",
            } if self.timestamp else None,
            "node_id": self.node_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LWWRegister":
        """Deserialize from dictionary."""
        register = cls(node_id=data.get("node_id", str(uuid4())))
        register.value_data = data.get("value")
        
        ts_data = data.get("timestamp")
        if ts_data:
            vc = VectorClock(clock=ts_data.get("vector_clock", {}))
            register.timestamp = Timestamp(
                vector_clock=vc,
                wall_clock=ts_data.get("wall_clock", 0),
                node_id=ts_data.get("node_id", ""),
            )
        
        return register


@dataclass
class GCounter(CRDT[int]):
    """Grow-only Counter - a CRDT that only increases.
    
    Each node maintains its own counter, and the total value is the sum of all counters.
    """

    counters: Dict[str, int] = field(default_factory=dict)
    node_id: str = field(default_factory=lambda: str(uuid4()))

    def increment(self, amount: int = 1) -> None:
        """Increment the counter for this node."""
        if amount < 0:
            raise ValueError("GCounter can only be incremented, not decremented")
        self.counters[self.node_id] = self.counters.get(self.node_id, 0) + amount

    def value(self) -> int:
        """Get the total value (sum of all counters)."""
        return sum(self.counters.values())

    def merge(self, other: "GCounter") -> None:
        """Merge with another GCounter."""
        for node_id, count in other.counters.items():
            self.counters[node_id] = max(self.counters.get(node_id, 0), count)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "GCounter",
            "counters": self.counters,
            "node_id": self.node_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GCounter":
        """Deserialize from dictionary."""
        counter = cls(node_id=data.get("node_id", str(uuid4())))
        counter.counters = data.get("counters", {})
        return counter


@dataclass
class ORSet(CRDT[Set[T]]):
    """Observed-Remove Set - a CRDT for sets that supports add and remove operations.
    
    Each element is tagged with a unique identifier to distinguish between different
    instances of the same value. Removes only affect elements that have been seen.
    """

    elements: Dict[T, Set[str]] = field(default_factory=dict)  # value -> set of unique IDs
    node_id: str = field(default_factory=lambda: str(uuid4()))

    def add(self, value: T) -> str:
        """Add an element to the set and return its unique ID."""
        unique_id = str(uuid4())
        if value not in self.elements:
            self.elements[value] = set()
        self.elements[value].add(unique_id)
        return unique_id

    def remove(self, value: T, unique_id: Optional[str] = None) -> None:
        """Remove an element from the set.
        
        If unique_id is provided, only that instance is removed.
        If not provided, all instances are removed.
        """
        if value not in self.elements:
            return
        
        if unique_id is None:
            # Remove all instances
            self.elements[value].clear()
        else:
            # Remove specific instance
            self.elements[value].discard(unique_id)
        
        # Clean up empty entries
        if not self.elements[value]:
            del self.elements[value]

    def value(self) -> Set[T]:
        """Get the current set of elements."""
        return set(self.elements.keys())

    def merge(self, other: "ORSet[T]") -> None:
        """Merge with another ORSet."""
        for value, unique_ids in other.elements.items():
            if value not in self.elements:
                self.elements[value] = set()
            # Union of unique IDs for each value
            self.elements[value].update(unique_ids)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        # Convert set values to lists for JSON serialization
        elements_serializable = {}
        for value, unique_ids in self.elements.items():
            # Convert value to string for JSON compatibility
            key = str(value)
            elements_serializable[key] = list(unique_ids)
        
        return {
            "type": "ORSet",
            "elements": elements_serializable,
            "node_id": self.node_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ORSet":
        """Deserialize from dictionary."""
        orset = cls(node_id=data.get("node_id", str(uuid4())))
        
        # Reconstruct elements from serialized form
        for key, unique_ids in data.get("elements", {}).items():
            # Try to convert key back to original type
            try:
                value = eval(key)  # This is a simplification; in production use proper deserialization
            except:
                value = key
            orset.elements[value] = set(unique_ids)
        
        return orset


@dataclass
class CRDTMap(CRDT[Dict[str, T]]):
    """A CRDT Map that uses LWWRegister for each value.
    
    This allows concurrent updates to different keys without conflicts.
    """

    data: Dict[str, LWWRegister[T]] = field(default_factory=dict)
    node_id: str = field(default_factory=lambda: str(uuid4()))

    def set(self, key: str, value: T) -> None:
        """Set a value in the map."""
        if key not in self.data:
            self.data[key] = LWWRegister(node_id=self.node_id)
        self.data[key].set(value)

    def get(self, key: str) -> Optional[T]:
        """Get a value from the map."""
        if key not in self.data:
            return None
        return self.data[key].value()

    def remove(self, key: str) -> None:
        """Remove a key from the map."""
        if key in self.data:
            del self.data[key]

    def value(self) -> Dict[str, T]:
        """Get the current map as a dictionary."""
        return {key: register.value() for key, register in self.data.items()}

    def merge(self, other: "CRDTMap[T]") -> None:
        """Merge with another CRDTMap."""
        for key, other_register in other.data.items():
            if key not in self.data:
                self.data[key] = LWWRegister(node_id=self.node_id)
            self.data[key].merge(other_register)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "CRDTMap",
            "data": {key: register.to_dict() for key, register in self.data.items()},
            "node_id": self.node_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CRDTMap":
        """Deserialize from dictionary."""
        crdt_map = cls(node_id=data.get("node_id", str(uuid4())))
        
        for key, register_data in data.get("data", {}).items():
            crdt_map.data[key] = LWWRegister.from_dict(register_data)
        
        return crdt_map
