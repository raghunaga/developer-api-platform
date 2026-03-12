"""Sync queue management service for offline-first synchronization."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.repositories import SyncQueueRepository, DataConflictRepository, SyncStatusRepository
from app.models.entities import SyncQueueEntry, DataConflict, SyncStatus

logger = logging.getLogger(__name__)


class SyncQueueService:
    """Service for managing sync queue with conflict detection and resolution."""

    def __init__(self, session: Session):
        """Initialize sync queue service."""
        self.session = session
        self.sync_queue_repo = SyncQueueRepository(session)
        self.conflict_repo = DataConflictRepository(session)
        self.status_repo = SyncStatusRepository(session)

    def enqueue_action(self, action_type: str, entity_type: str, entity_id: str, 
                      payload: Any, user_id: Optional[str] = None, 
                      device_id: Optional[str] = None, priority: int = 0) -> SyncQueueEntry:
        """Enqueue a user action for sync.
        
        Args:
            action_type: Type of action ('create', 'update', 'delete')
            entity_type: Type of entity
            entity_id: ID of entity
            payload: Action payload (will be JSON serialized)
            user_id: ID of user who initiated action
            device_id: ID of device that initiated action
            priority: Priority level (higher = synced first)
        
        Returns:
            SyncQueueEntry object
        """
        entry = SyncQueueEntry(
            id=str(uuid4()),
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=json.dumps(payload),
            user_id=user_id,
            device_id=device_id,
            priority=priority,
            status="pending",
            retry_count=0
        )
        self.session.add(entry)
        self.session.flush()
        logger.info(f"Enqueued {action_type} action for {entity_type}:{entity_id}")
        return entry

    def get_pending_actions(self) -> List[SyncQueueEntry]:
        """Get all pending sync queue entries ordered by priority.
        
        Returns:
            List of pending SyncQueueEntry objects
        """
        return self.sync_queue_repo.get_pending_entries()

    def get_queue_size(self) -> int:
        """Get number of pending sync queue entries.
        
        Returns:
            Number of pending entries
        """
        return self.sync_queue_repo.get_queue_size()

    def mark_synced(self, entry_id: str) -> Optional[SyncQueueEntry]:
        """Mark a sync queue entry as successfully synced.
        
        Args:
            entry_id: ID of sync queue entry
        
        Returns:
            Updated SyncQueueEntry or None
        """
        entry = self.sync_queue_repo.mark_synced(entry_id)
        if entry:
            logger.info(f"Marked sync queue entry as synced: {entry_id}")
        return entry

    def mark_failed(self, entry_id: str, error_message: str, 
                   max_retries: int = 3) -> Optional[SyncQueueEntry]:
        """Mark a sync queue entry as failed.
        
        Args:
            entry_id: ID of sync queue entry
            error_message: Error message
            max_retries: Maximum number of retries
        
        Returns:
            Updated SyncQueueEntry or None
        """
        entry = self.sync_queue_repo.get_by_id(entry_id)
        if not entry:
            return None
        
        entry.retry_count += 1
        entry.last_retry_at = datetime.utcnow()
        entry.error_message = error_message
        
        if entry.retry_count >= max_retries:
            entry.status = "failed"
            logger.error(f"Sync queue entry failed after {max_retries} retries: {entry_id}")
        else:
            entry.status = "pending"
            logger.warning(f"Sync queue entry failed, will retry: {entry_id}")
        
        self.session.flush()
        return entry

    def detect_conflict(self, entry_id: str, entity_type: str, entity_id: str,
                       local_version: Any, remote_version: Any, 
                       conflict_type: str = "update_conflict") -> DataConflict:
        """Detect and record a data conflict.
        
        Args:
            entry_id: ID of sync queue entry
            entity_type: Type of entity
            entity_id: ID of entity
            local_version: Local version of data
            remote_version: Remote version of data
            conflict_type: Type of conflict
        
        Returns:
            DataConflict object
        """
        conflict = DataConflict(
            id=str(uuid4()),
            sync_queue_entry_id=entry_id,
            entity_type=entity_type,
            entity_id=entity_id,
            local_version=json.dumps(local_version),
            remote_version=json.dumps(remote_version),
            conflict_type=conflict_type,
            resolution_strategy="pending"
        )
        self.session.add(conflict)
        self.session.flush()
        
        # Mark sync queue entry as having conflict
        self.sync_queue_repo.mark_conflict(entry_id)
        
        logger.warning(f"Detected {conflict_type} for {entity_type}:{entity_id}")
        return conflict

    def resolve_conflict(self, conflict_id: str, resolution_strategy: str, 
                        resolved_version: Any, resolved_by: str) -> Optional[DataConflict]:
        """Resolve a data conflict.
        
        Args:
            conflict_id: ID of conflict
            resolution_strategy: Strategy used ('local_wins', 'remote_wins', 'merge', 'manual')
            resolved_version: Resolved version of data
            resolved_by: User ID who resolved the conflict
        
        Returns:
            Updated DataConflict or None
        """
        conflict = self.conflict_repo.mark_resolved(
            conflict_id, 
            json.dumps(resolved_version),
            resolved_by
        )
        
        if conflict:
            conflict.resolution_strategy = resolution_strategy
            self.session.flush()
            logger.info(f"Resolved conflict {conflict_id} using {resolution_strategy}")
        
        return conflict

    def get_unresolved_conflicts(self) -> List[DataConflict]:
        """Get all unresolved conflicts.
        
        Returns:
            List of unresolved DataConflict objects
        """
        return self.conflict_repo.get_unresolved_conflicts()

    def get_conflict_count(self) -> int:
        """Get number of unresolved conflicts.
        
        Returns:
            Number of unresolved conflicts
        """
        return self.conflict_repo.get_conflict_count()

    def get_sync_status(self, device_id: Optional[str] = None) -> Optional[SyncStatus]:
        """Get sync status.
        
        Args:
            device_id: Device ID (None for global status)
        
        Returns:
            SyncStatus object or None
        """
        if device_id:
            return self.status_repo.get_device_status(device_id)
        else:
            return self.status_repo.get_global_status()

    def create_sync_status(self, device_id: Optional[str] = None) -> SyncStatus:
        """Create a new sync status entry.
        
        Args:
            device_id: Device ID (None for global status)
        
        Returns:
            SyncStatus object
        """
        status = SyncStatus(
            id=str(uuid4()),
            device_id=device_id,
            status="idle",
            total_entries=0,
            synced_entries=0,
            failed_entries=0,
            conflict_entries=0
        )
        self.session.add(status)
        self.session.flush()
        return status

    def start_sync(self, device_id: Optional[str] = None) -> SyncStatus:
        """Start a sync operation.
        
        Args:
            device_id: Device ID (None for global sync)
        
        Returns:
            Updated SyncStatus object
        """
        status = self.get_sync_status(device_id)
        if not status:
            status = self.create_sync_status(device_id)
        
        pending_count = self.get_queue_size()
        self.status_repo.mark_syncing(status.id, pending_count)
        
        logger.info(f"Started sync with {pending_count} pending entries")
        return status

    def update_sync_progress(self, device_id: Optional[str] = None, 
                            synced: int = 0, failed: int = 0, 
                            conflicts: int = 0) -> Optional[SyncStatus]:
        """Update sync progress.
        
        Args:
            device_id: Device ID (None for global status)
            synced: Number of synced entries
            failed: Number of failed entries
            conflicts: Number of conflicted entries
        
        Returns:
            Updated SyncStatus or None
        """
        status = self.get_sync_status(device_id)
        if not status:
            return None
        
        self.status_repo.update_progress(status.id, synced, failed, conflicts)
        return status

    def complete_sync(self, device_id: Optional[str] = None) -> Optional[SyncStatus]:
        """Mark sync as complete.
        
        Args:
            device_id: Device ID (None for global status)
        
        Returns:
            Updated SyncStatus or None
        """
        status = self.get_sync_status(device_id)
        if not status:
            return None
        
        self.status_repo.mark_idle(status.id)
        logger.info(f"Completed sync: {status.synced_entries} synced, {status.failed_entries} failed, {status.conflict_entries} conflicts")
        return status

    def get_sync_stats(self) -> Dict[str, Any]:
        """Get sync statistics.
        
        Returns:
            Dictionary with sync stats
        """
        pending = self.get_queue_size()
        failed = len(self.sync_queue_repo.get_failed_entries())
        conflicts = self.get_conflict_count()
        
        return {
            "pending_entries": pending,
            "failed_entries": failed,
            "unresolved_conflicts": conflicts,
            "total_queue_size": pending + failed
        }

    def get_queue_entries(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get sync queue entries.
        
        Args:
            status: Filter by status (None for all)
        
        Returns:
            List of sync queue entry data
        """
        if status:
            entries = self.sync_queue_repo.get_by_status(status)
        else:
            entries = self.session.query(SyncQueueEntry).all()
        
        return [
            {
                "id": entry.id,
                "action_type": entry.action_type,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "status": entry.status,
                "retry_count": entry.retry_count,
                "created_at": entry.created_at.isoformat(),
                "priority": entry.priority
            }
            for entry in entries
        ]
