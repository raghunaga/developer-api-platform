"""State management module."""

from app.state.crdt import (
    CRDT,
    CRDTMap,
    GCounter,
    LWWRegister,
    ORSet,
    Timestamp,
    VectorClock,
)
from app.state.sync import (
    ConflictResolution,
    StateSynchronizer,
    SyncMessage,
    SyncOperation,
    SyncStatus,
)
from app.state.conflict_resolver import (
    ConflictInfo,
    ConflictResolver,
    ConflictType,
)

__all__ = [
    # CRDT classes
    "CRDT",
    "CRDTMap",
    "GCounter",
    "LWWRegister",
    "ORSet",
    "Timestamp",
    "VectorClock",
    # Sync classes
    "ConflictResolution",
    "StateSynchronizer",
    "SyncMessage",
    "SyncOperation",
    "SyncStatus",
    # Conflict resolution classes
    "ConflictInfo",
    "ConflictResolver",
    "ConflictType",
]
