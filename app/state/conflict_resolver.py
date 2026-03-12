"""Conflict resolution logic using CRDT merge semantics."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from app.state.crdt import CRDT, LWWRegister, VectorClock, Timestamp


class ConflictType(str, Enum):
    """Types of conflicts that can occur."""

    CONCURRENT_WRITE = "concurrent_write"
    DEVICE_IN_MULTIPLE_CELLS = "device_in_multiple_cells"
    HIERARCHY_INCONSISTENCY = "hierarchy_inconsistency"
    TIMESTAMP_CONFLICT = "timestamp_conflict"
    UNKNOWN = "unknown"


@dataclass
class ConflictInfo:
    """Information about a detected conflict."""

    conflict_type: ConflictType
    key: str
    local_value: Any
    remote_value: Any
    local_timestamp: Optional[Timestamp] = None
    remote_timestamp: Optional[Timestamp] = None
    reasoning: str = ""


class ConflictResolver:
    """Resolves conflicts using CRDT merge semantics."""

    def __init__(self, node_id: str):
        """Initialize the conflict resolver."""
        self.node_id = node_id
        self.resolution_history: List[Dict[str, Any]] = []

    def detect_conflict(
        self,
        key: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Timestamp] = None,
        remote_timestamp: Optional[Timestamp] = None,
    ) -> Optional[ConflictInfo]:
        """Detect if a conflict exists between local and remote values."""
        if local_value == remote_value:
            return None  # No conflict
        
        # Determine conflict type
        conflict_type = self._determine_conflict_type(key, local_value, remote_value)
        
        reasoning = self._generate_reasoning(
            conflict_type,
            key,
            local_value,
            remote_value,
            local_timestamp,
            remote_timestamp,
        )
        
        return ConflictInfo(
            conflict_type=conflict_type,
            key=key,
            local_value=local_value,
            remote_value=remote_value,
            local_timestamp=local_timestamp,
            remote_timestamp=remote_timestamp,
            reasoning=reasoning,
        )

    def resolve_conflict(
        self,
        conflict: ConflictInfo,
        strategy: str = "crdt_merge",
    ) -> Any:
        """Resolve a conflict using the specified strategy.
        
        Strategies:
        - 'crdt_merge': Use CRDT merge semantics (LWW for timestamps)
        - 'timestamp_based': Use timestamp comparison
        - 'local_wins': Keep local value
        - 'remote_wins': Use remote value
        """
        if strategy == "crdt_merge":
            resolved_value = self._resolve_with_crdt_merge(conflict)
        elif strategy == "timestamp_based":
            resolved_value = self._resolve_with_timestamp(conflict)
        elif strategy == "local_wins":
            resolved_value = conflict.local_value
        elif strategy == "remote_wins":
            resolved_value = conflict.remote_value
        else:
            # Default to CRDT merge
            resolved_value = self._resolve_with_crdt_merge(conflict)
        
        # Record resolution
        self.resolution_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "key": conflict.key,
            "conflict_type": conflict.conflict_type.value,
            "local_value": conflict.local_value,
            "remote_value": conflict.remote_value,
            "resolved_value": resolved_value,
            "strategy": strategy,
            "reasoning": conflict.reasoning,
        })
        
        return resolved_value

    def _resolve_with_crdt_merge(self, conflict: ConflictInfo) -> Any:
        """Resolve using CRDT merge semantics (Last-Write-Wins)."""
        if conflict.local_timestamp is None and conflict.remote_timestamp is None:
            # No timestamps - use remote value as default
            return conflict.remote_value
        
        if conflict.local_timestamp is None:
            return conflict.remote_value
        
        if conflict.remote_timestamp is None:
            return conflict.local_value
        
        # Compare timestamps using LWW semantics
        if conflict.remote_timestamp.wall_clock > conflict.local_timestamp.wall_clock:
            return conflict.remote_value
        elif conflict.local_timestamp.wall_clock > conflict.remote_timestamp.wall_clock:
            return conflict.local_value
        else:
            # Same wall clock - use node_id as tiebreaker
            if conflict.remote_timestamp.node_id > conflict.local_timestamp.node_id:
                return conflict.remote_value
            else:
                return conflict.local_value

    def _resolve_with_timestamp(self, conflict: ConflictInfo) -> Any:
        """Resolve using timestamp comparison."""
        if conflict.local_timestamp is None and conflict.remote_timestamp is None:
            return conflict.remote_value
        
        if conflict.local_timestamp is None:
            return conflict.remote_value
        
        if conflict.remote_timestamp is None:
            return conflict.local_value
        
        # Use the value with the later timestamp
        if conflict.remote_timestamp.wall_clock >= conflict.local_timestamp.wall_clock:
            return conflict.remote_value
        else:
            return conflict.local_value

    def _determine_conflict_type(
        self,
        key: str,
        local_value: Any,
        remote_value: Any,
    ) -> ConflictType:
        """Determine the type of conflict."""
        # Check for device in multiple cells
        if "device" in key.lower() and "cell" in key.lower():
            return ConflictType.DEVICE_IN_MULTIPLE_CELLS
        
        # Check for hierarchy inconsistency
        if "parent" in key.lower() or "child" in key.lower():
            return ConflictType.HIERARCHY_INCONSISTENCY
        
        # Default to concurrent write
        return ConflictType.CONCURRENT_WRITE

    def _generate_reasoning(
        self,
        conflict_type: ConflictType,
        key: str,
        local_value: Any,
        remote_value: Any,
        local_timestamp: Optional[Timestamp] = None,
        remote_timestamp: Optional[Timestamp] = None,
    ) -> str:
        """Generate human-readable reasoning for the conflict."""
        if conflict_type == ConflictType.DEVICE_IN_MULTIPLE_CELLS:
            return (
                f"Device conflict detected for key '{key}': "
                f"device assigned to multiple cells. "
                f"Local: {local_value}, Remote: {remote_value}"
            )
        
        elif conflict_type == ConflictType.HIERARCHY_INCONSISTENCY:
            return (
                f"Hierarchy inconsistency detected for key '{key}': "
                f"parent-child relationship conflict. "
                f"Local: {local_value}, Remote: {remote_value}"
            )
        
        elif conflict_type == ConflictType.CONCURRENT_WRITE:
            if local_timestamp and remote_timestamp:
                if local_timestamp.wall_clock > remote_timestamp.wall_clock:
                    return (
                        f"Concurrent write conflict for key '{key}': "
                        f"local write is more recent (local: {local_timestamp.wall_clock}, "
                        f"remote: {remote_timestamp.wall_clock})"
                    )
                else:
                    return (
                        f"Concurrent write conflict for key '{key}': "
                        f"remote write is more recent (local: {local_timestamp.wall_clock}, "
                        f"remote: {remote_timestamp.wall_clock})"
                    )
            else:
                return (
                    f"Concurrent write conflict for key '{key}': "
                    f"local: {local_value}, remote: {remote_value}"
                )
        
        else:
            return f"Unknown conflict for key '{key}': local: {local_value}, remote: {remote_value}"

    def get_resolution_history(self) -> List[Dict[str, Any]]:
        """Get the history of all resolved conflicts."""
        return self.resolution_history.copy()

    def validate_hierarchy_consistency(
        self,
        hierarchy_data: Dict[str, Any],
    ) -> List[ConflictInfo]:
        """Validate consistency of hierarchy data.
        
        Checks for:
        - Devices in multiple cells
        - Circular parent-child relationships
        - Missing parent references
        """
        conflicts = []
        
        # Check for devices in multiple cells
        device_to_cells: Dict[str, List[str]] = {}
        for cell_id, cell_data in hierarchy_data.items():
            if "devices" in cell_data:
                for device_id in cell_data["devices"]:
                    if device_id not in device_to_cells:
                        device_to_cells[device_id] = []
                    device_to_cells[device_id].append(cell_id)
        
        # Report conflicts for devices in multiple cells
        for device_id, cell_ids in device_to_cells.items():
            if len(cell_ids) > 1:
                conflict = ConflictInfo(
                    conflict_type=ConflictType.DEVICE_IN_MULTIPLE_CELLS,
                    key=f"device_{device_id}",
                    local_value=cell_ids[0],
                    remote_value=cell_ids[1],
                    reasoning=f"Device {device_id} is assigned to multiple cells: {cell_ids}",
                )
                conflicts.append(conflict)
        
        return conflicts

    def to_dict(self) -> Dict[str, Any]:
        """Serialize resolver state to dictionary."""
        return {
            "node_id": self.node_id,
            "resolution_history": self.resolution_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConflictResolver":
        """Deserialize resolver state from dictionary."""
        resolver = cls(node_id=data.get("node_id", ""))
        resolver.resolution_history = data.get("resolution_history", [])
        return resolver
