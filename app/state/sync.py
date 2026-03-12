"""State synchronization protocol for multi-device consistency using CRDTs."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from uuid import uuid4

from app.state.crdt import CRDT, CRDTMap, LWWRegister, VectorClock, Timestamp


class SyncStatus(str, Enum):
    """Status of synchronization operation."""

    IDLE = "idle"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    ERROR = "error"


@dataclass
class SyncOperation:
    """Represents a single synchronization operation."""

    operation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    node_id: str = ""
    key: str = ""
    value: Any = None
    operation_type: str = "set"  # 'set', 'remove', 'merge'
    vector_clock: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "operation_id": self.operation_id,
            "timestamp": self.timestamp.isoformat(),
            "node_id": self.node_id,
            "key": self.key,
            "value": self.value,
            "operation_type": self.operation_type,
            "vector_clock": self.vector_clock,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncOperation":
        """Deserialize from dictionary."""
        return cls(
            operation_id=data.get("operation_id", str(uuid4())),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            node_id=data.get("node_id", ""),
            key=data.get("key", ""),
            value=data.get("value"),
            operation_type=data.get("operation_type", "set"),
            vector_clock=data.get("vector_clock", {}),
        )


@dataclass
class SyncMessage:
    """Message for synchronizing state between nodes."""

    message_id: str = field(default_factory=lambda: str(uuid4()))
    sender_id: str = ""
    receiver_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    operations: List[SyncOperation] = field(default_factory=list)
    vector_clock: Dict[str, int] = field(default_factory=dict)
    requires_ack: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "timestamp": self.timestamp.isoformat(),
            "operations": [op.to_dict() for op in self.operations],
            "vector_clock": self.vector_clock,
            "requires_ack": self.requires_ack,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncMessage":
        """Deserialize from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid4())),
            sender_id=data.get("sender_id", ""),
            receiver_id=data.get("receiver_id", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            operations=[SyncOperation.from_dict(op) for op in data.get("operations", [])],
            vector_clock=data.get("vector_clock", {}),
            requires_ack=data.get("requires_ack", True),
        )


@dataclass
class ConflictResolution:
    """Represents a conflict resolution decision."""

    conflict_id: str = field(default_factory=lambda: str(uuid4()))
    key: str = ""
    local_value: Any = None
    remote_value: Any = None
    resolved_value: Any = None
    resolution_strategy: str = "crdt_merge"  # 'crdt_merge', 'timestamp_based', 'manual_override'
    resolved_at: datetime = field(default_factory=datetime.utcnow)
    resolved_by: str = ""  # node_id or user_id

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "key": self.key,
            "local_value": self.local_value,
            "remote_value": self.remote_value,
            "resolved_value": self.resolved_value,
            "resolution_strategy": self.resolution_strategy,
            "resolved_at": self.resolved_at.isoformat(),
            "resolved_by": self.resolved_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConflictResolution":
        """Deserialize from dictionary."""
        return cls(
            conflict_id=data.get("conflict_id", str(uuid4())),
            key=data.get("key", ""),
            local_value=data.get("local_value"),
            remote_value=data.get("remote_value"),
            resolved_value=data.get("resolved_value"),
            resolution_strategy=data.get("resolution_strategy", "crdt_merge"),
            resolved_at=datetime.fromisoformat(data.get("resolved_at", datetime.utcnow().isoformat())),
            resolved_by=data.get("resolved_by", ""),
        )


class StateSynchronizer:
    """Manages state synchronization between nodes using CRDTs."""

    def __init__(self, node_id: str):
        """Initialize the synchronizer for a specific node."""
        self.node_id = node_id
        self.vector_clock = VectorClock()
        self.pending_operations: List[SyncOperation] = []
        self.sync_status = SyncStatus.IDLE
        self.last_sync_time: Optional[datetime] = None
        self.conflict_history: List[ConflictResolution] = []
        self.acknowledged_messages: Set[str] = set()

    def create_sync_operation(
        self,
        key: str,
        value: Any,
        operation_type: str = "set",
    ) -> SyncOperation:
        """Create a new sync operation."""
        self.vector_clock.increment(self.node_id)
        
        operation = SyncOperation(
            node_id=self.node_id,
            key=key,
            value=value,
            operation_type=operation_type,
            vector_clock=self.vector_clock.clock.copy(),
        )
        
        self.pending_operations.append(operation)
        return operation

    def create_sync_message(
        self,
        receiver_id: str,
        operations: Optional[List[SyncOperation]] = None,
    ) -> SyncMessage:
        """Create a sync message with pending operations."""
        if operations is None:
            operations = self.pending_operations
        
        self.vector_clock.increment(self.node_id)
        
        message = SyncMessage(
            sender_id=self.node_id,
            receiver_id=receiver_id,
            operations=operations,
            vector_clock=self.vector_clock.clock.copy(),
        )
        
        return message

    def process_sync_message(
        self,
        message: SyncMessage,
        local_state: CRDTMap,
    ) -> List[ConflictResolution]:
        """Process an incoming sync message and merge state.
        
        Returns a list of conflicts that were resolved.
        """
        self.sync_status = SyncStatus.SYNCING
        conflicts = []
        
        # Update vector clock
        self.vector_clock.merge(VectorClock(clock=message.vector_clock))
        self.vector_clock.increment(self.node_id)
        
        # Process each operation
        for operation in message.operations:
            conflict = self._apply_operation(operation, local_state)
            if conflict:
                conflicts.append(conflict)
        
        self.last_sync_time = datetime.utcnow()
        self.sync_status = SyncStatus.SYNCED if not conflicts else SyncStatus.CONFLICT
        
        return conflicts

    def _apply_operation(
        self,
        operation: SyncOperation,
        local_state: CRDTMap,
    ) -> Optional[ConflictResolution]:
        """Apply a single operation to local state.
        
        Returns a ConflictResolution if a conflict was detected and resolved.
        """
        if operation.operation_type == "set":
            local_value = local_state.get(operation.key)
            
            # Check for conflict
            if local_value is not None and local_value != operation.value:
                # Conflict detected - resolve using CRDT merge semantics
                conflict = ConflictResolution(
                    key=operation.key,
                    local_value=local_value,
                    remote_value=operation.value,
                    resolved_value=operation.value,  # Remote wins (LWW semantics)
                    resolution_strategy="crdt_merge",
                    resolved_by=self.node_id,
                )
                self.conflict_history.append(conflict)
                
                # Apply the remote value
                local_state.set(operation.key, operation.value)
                return conflict
            else:
                # No conflict - apply the operation
                local_state.set(operation.key, operation.value)
        
        elif operation.operation_type == "remove":
            local_state.remove(operation.key)
        
        return None

    def acknowledge_message(self, message_id: str) -> None:
        """Acknowledge receipt of a sync message."""
        self.acknowledged_messages.add(message_id)

    def get_pending_operations(self) -> List[SyncOperation]:
        """Get all pending operations."""
        return self.pending_operations.copy()

    def clear_pending_operations(self) -> None:
        """Clear pending operations after successful sync."""
        self.pending_operations.clear()

    def get_conflict_history(self) -> List[ConflictResolution]:
        """Get the history of resolved conflicts."""
        return self.conflict_history.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize synchronizer state to dictionary."""
        return {
            "node_id": self.node_id,
            "vector_clock": self.vector_clock.clock,
            "pending_operations": [op.to_dict() for op in self.pending_operations],
            "sync_status": self.sync_status.value,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "conflict_history": [c.to_dict() for c in self.conflict_history],
            "acknowledged_messages": list(self.acknowledged_messages),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateSynchronizer":
        """Deserialize synchronizer state from dictionary."""
        synchronizer = cls(node_id=data.get("node_id", str(uuid4())))
        synchronizer.vector_clock = VectorClock(clock=data.get("vector_clock", {}))
        synchronizer.pending_operations = [
            SyncOperation.from_dict(op) for op in data.get("pending_operations", [])
        ]
        synchronizer.sync_status = SyncStatus(data.get("sync_status", "idle"))
        
        if data.get("last_sync_time"):
            synchronizer.last_sync_time = datetime.fromisoformat(data.get("last_sync_time"))
        
        synchronizer.conflict_history = [
            ConflictResolution.from_dict(c) for c in data.get("conflict_history", [])
        ]
        synchronizer.acknowledged_messages = set(data.get("acknowledged_messages", []))
        
        return synchronizer
