"""Tests for cache and sync queue functionality."""

import pytest
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.entities import (
    Tenant, Customer, Site, Gateway, Device, User, DataStream,
    CacheEntry, SyncQueueEntry, DataConflict, SyncStatus
)
from app.db.database import Database
from app.db.repositories import (
    CacheRepository, SyncQueueRepository, DataConflictRepository, SyncStatusRepository
)
from app.services.cache_service import CacheService
from app.services.sync_queue_service import SyncQueueService


@pytest.fixture
def db():
    """Create an in-memory SQLite database for testing."""
    from app.models.base import Base
    from app.models import entities  # noqa: F401
    
    database = Database("sqlite:///:memory:")
    database.initialize()
    database.create_tables()
    yield database
    database.drop_tables()
    database.close()


@pytest.fixture
def session(db):
    """Create a database session for testing."""
    return db.get_session()


@pytest.fixture
def cache_service(session):
    """Create a cache service for testing."""
    return CacheService(session)


@pytest.fixture
def sync_queue_service(session):
    """Create a sync queue service for testing."""
    return SyncQueueService(session)


class TestCacheRepository:
    """Tests for CacheRepository."""

    def test_create_cache_entry(self, session):
        """Test creating a cache entry."""
        repo = CacheRepository(session)
        
        entry = repo.create(
            id="cache-1",
            key="customer:123",
            entity_type="customer",
            entity_id="123",
            data=json.dumps({"name": "Test Customer"}),
            is_valid=True
        )
        session.commit()
        
        assert entry.id == "cache-1"
        assert entry.key == "customer:123"
        assert entry.entity_type == "customer"
        assert entry.is_valid == True

    def test_get_cache_by_key(self, session):
        """Test retrieving cache entry by key."""
        repo = CacheRepository(session)
        
        entry = repo.create(
            id="cache-1",
            key="customer:123",
            entity_type="customer",
            entity_id="123",
            data=json.dumps({"name": "Test"}),
            is_valid=True
        )
        session.commit()
        
        retrieved = repo.get_by_key("customer:123")
        assert retrieved is not None
        assert retrieved.id == "cache-1"

    def test_get_cache_by_entity(self, session):
        """Test retrieving cache entries by entity."""
        repo = CacheRepository(session)
        
        repo.create(
            id="cache-1",
            key="customer:123:data",
            entity_type="customer",
            entity_id="123",
            data=json.dumps({"name": "Test"}),
            is_valid=True
        )
        repo.create(
            id="cache-2",
            key="customer:123:sites",
            entity_type="customer",
            entity_id="123",
            data=json.dumps([]),
            is_valid=True
        )
        session.commit()
        
        entries = repo.get_by_entity("customer", "123")
        assert len(entries) == 2

    def test_invalidate_cache_entry(self, session):
        """Test invalidating cache entries."""
        repo = CacheRepository(session)
        
        repo.create(
            id="cache-1",
            key="customer:123",
            entity_type="customer",
            entity_id="123",
            data=json.dumps({"name": "Test"}),
            is_valid=True
        )
        session.commit()
        
        count = repo.invalidate_by_entity("customer", "123")
        session.commit()
        
        assert count == 1
        retrieved = repo.get_by_key("customer:123")
        assert retrieved is None  # Should not return invalid entries

    def test_cache_expiration(self, session):
        """Test cache entry expiration."""
        repo = CacheRepository(session)
        
        # Create entry that expires in the past
        entry = repo.create(
            id="cache-1",
            key="customer:123",
            entity_type="customer",
            entity_id="123",
            data=json.dumps({"name": "Test"}),
            is_valid=True,
            expires_at=datetime.utcnow() - timedelta(seconds=1)
        )
        session.commit()
        
        expired = repo.get_expired_entries()
        assert len(expired) == 1
        assert expired[0].id == "cache-1"

    def test_clean_expired_entries(self, session):
        """Test cleaning expired cache entries."""
        repo = CacheRepository(session)
        
        # Create expired entry
        repo.create(
            id="cache-1",
            key="customer:123",
            entity_type="customer",
            entity_id="123",
            data=json.dumps({"name": "Test"}),
            is_valid=True,
            expires_at=datetime.utcnow() - timedelta(seconds=1)
        )
        session.commit()
        
        count = repo.clean_expired_entries()
        session.commit()
        
        assert count == 1
        all_entries = session.query(CacheEntry).all()
        assert len(all_entries) == 0


class TestCacheService:
    """Tests for CacheService."""

    def test_set_and_get_cache(self, cache_service, session):
        """Test setting and getting cache data."""
        data = {"name": "Test Customer", "id": "123"}
        
        cache_service.set("customer:123", "customer", "123", data)
        session.commit()
        
        retrieved = cache_service.get("customer:123")
        assert retrieved == data

    def test_cache_with_ttl(self, cache_service, session):
        """Test cache with TTL."""
        data = {"name": "Test"}
        
        # Set cache with 1 second TTL
        cache_service.set("customer:123", "customer", "123", data, ttl_seconds=1)
        session.commit()
        
        # Should be retrievable immediately
        retrieved = cache_service.get("customer:123")
        assert retrieved == data
        
        # Simulate expiration
        entry = cache_service.cache_repo.get_by_key("customer:123")
        entry.expires_at = datetime.utcnow() - timedelta(seconds=1)
        session.commit()
        
        # Should not be retrievable after expiration
        retrieved = cache_service.get("customer:123")
        assert retrieved is None

    def test_invalidate_entity_cache(self, cache_service, session):
        """Test invalidating entity cache."""
        cache_service.set("customer:123:data", "customer", "123", {"name": "Test"})
        cache_service.set("customer:123:sites", "customer", "123", [])
        session.commit()
        
        count = cache_service.invalidate_entity("customer", "123")
        session.commit()
        
        assert count == 2
        assert cache_service.get("customer:123:data") is None

    def test_cache_stats(self, cache_service, session):
        """Test cache statistics."""
        cache_service.set("customer:123", "customer", "123", {"name": "Test"})
        cache_service.set("device:456", "device", "456", {"status": "online"})
        session.commit()
        
        stats = cache_service.get_cache_stats()
        assert stats["valid_entries"] == 2
        assert stats["total_entries"] == 2


class TestSyncQueueRepository:
    """Tests for SyncQueueRepository."""

    def test_create_sync_queue_entry(self, session):
        """Test creating a sync queue entry."""
        repo = SyncQueueRepository(session)
        
        entry = repo.create(
            id="sync-1",
            action_type="update",
            entity_type="customer",
            entity_id="123",
            payload=json.dumps({"name": "Updated"}),
            status="pending"
        )
        session.commit()
        
        assert entry.id == "sync-1"
        assert entry.action_type == "update"
        assert entry.status == "pending"

    def test_get_pending_entries(self, session):
        """Test retrieving pending sync queue entries."""
        repo = SyncQueueRepository(session)
        
        repo.create(
            id="sync-1",
            action_type="update",
            entity_type="customer",
            entity_id="123",
            payload=json.dumps({"name": "Updated"}),
            status="pending",
            priority=1
        )
        repo.create(
            id="sync-2",
            action_type="create",
            entity_type="device",
            entity_id="456",
            payload=json.dumps({"name": "New Device"}),
            status="pending",
            priority=2
        )
        session.commit()
        
        pending = repo.get_pending_entries()
        assert len(pending) == 2
        # Should be ordered by priority (highest first)
        assert pending[0].priority == 2

    def test_mark_synced(self, session):
        """Test marking entry as synced."""
        repo = SyncQueueRepository(session)
        
        entry = repo.create(
            id="sync-1",
            action_type="update",
            entity_type="customer",
            entity_id="123",
            payload=json.dumps({"name": "Updated"}),
            status="pending"
        )
        session.commit()
        
        updated = repo.mark_synced("sync-1")
        session.commit()
        
        assert updated.status == "synced"

    def test_mark_failed(self, session):
        """Test marking entry as failed."""
        repo = SyncQueueRepository(session)
        
        entry = repo.create(
            id="sync-1",
            action_type="update",
            entity_type="customer",
            entity_id="123",
            payload=json.dumps({"name": "Updated"}),
            status="pending"
        )
        session.commit()
        
        updated = repo.mark_failed("sync-1", "Network error")
        session.commit()
        
        assert updated.status == "failed"
        assert updated.error_message == "Network error"


class TestSyncQueueService:
    """Tests for SyncQueueService."""

    def test_enqueue_action(self, sync_queue_service, session):
        """Test enqueueing an action."""
        payload = {"name": "Updated Customer"}
        
        entry = sync_queue_service.enqueue_action(
            "update", "customer", "123", payload, user_id="user-1"
        )
        session.commit()
        
        assert entry.action_type == "update"
        assert entry.entity_type == "customer"
        assert entry.status == "pending"

    def test_get_pending_actions(self, sync_queue_service, session):
        """Test retrieving pending actions."""
        sync_queue_service.enqueue_action("update", "customer", "123", {"name": "Updated"})
        sync_queue_service.enqueue_action("create", "device", "456", {"name": "New"})
        session.commit()
        
        pending = sync_queue_service.get_pending_actions()
        assert len(pending) == 2

    def test_queue_size(self, sync_queue_service, session):
        """Test getting queue size."""
        sync_queue_service.enqueue_action("update", "customer", "123", {"name": "Updated"})
        sync_queue_service.enqueue_action("create", "device", "456", {"name": "New"})
        session.commit()
        
        size = sync_queue_service.get_queue_size()
        assert size == 2

    def test_detect_conflict(self, sync_queue_service, session):
        """Test detecting a conflict."""
        entry = sync_queue_service.enqueue_action(
            "update", "customer", "123", {"name": "Local"}
        )
        session.commit()
        
        conflict = sync_queue_service.detect_conflict(
            entry.id, "customer", "123",
            {"name": "Local", "version": 1},
            {"name": "Remote", "version": 2},
            "update_conflict"
        )
        session.commit()
        
        assert conflict.conflict_type == "update_conflict"
        assert conflict.sync_queue_entry_id == entry.id

    def test_resolve_conflict(self, sync_queue_service, session):
        """Test resolving a conflict."""
        entry = sync_queue_service.enqueue_action(
            "update", "customer", "123", {"name": "Local"}
        )
        session.commit()
        
        conflict = sync_queue_service.detect_conflict(
            entry.id, "customer", "123",
            {"name": "Local"},
            {"name": "Remote"},
            "update_conflict"
        )
        session.commit()
        
        resolved = sync_queue_service.resolve_conflict(
            conflict.id, "remote_wins", {"name": "Remote"}, "user-1"
        )
        session.commit()
        
        assert resolved.resolution_strategy == "remote_wins"
        assert resolved.resolved_by == "user-1"

    def test_sync_status_lifecycle(self, sync_queue_service, session):
        """Test sync status lifecycle."""
        # Create initial status
        status = sync_queue_service.create_sync_status()
        session.commit()
        
        assert status.status == "idle"
        
        # Start sync
        sync_queue_service.enqueue_action("update", "customer", "123", {"name": "Updated"})
        session.commit()
        
        status = sync_queue_service.start_sync()
        session.commit()
        
        assert status.status == "syncing"
        assert status.total_entries == 1
        
        # Update progress
        sync_queue_service.update_sync_progress(synced=1)
        session.commit()
        
        status = sync_queue_service.get_sync_status()
        assert status.synced_entries == 1
        
        # Complete sync
        sync_queue_service.complete_sync()
        session.commit()
        
        status = sync_queue_service.get_sync_status()
        assert status.status == "idle"

    def test_sync_stats(self, sync_queue_service, session):
        """Test sync statistics."""
        sync_queue_service.enqueue_action("update", "customer", "123", {"name": "Updated"})
        sync_queue_service.enqueue_action("create", "device", "456", {"name": "New"})
        session.commit()
        
        stats = sync_queue_service.get_sync_stats()
        assert stats["pending_entries"] == 2
        assert stats["total_queue_size"] == 2


class TestOfflineFirstSync:
    """Integration tests for offline-first sync."""

    def test_offline_cache_and_queue(self, cache_service, sync_queue_service, session):
        """Test offline caching and queuing."""
        # Cache data for offline access
        customer_data = {"id": "123", "name": "Test Customer"}
        cache_service.set("customer:123", "customer", "123", customer_data)
        session.commit()
        
        # Queue action while offline
        sync_queue_service.enqueue_action(
            "update", "customer", "123", {"name": "Updated"}
        )
        session.commit()
        
        # Verify cache is available
        cached = cache_service.get("customer:123")
        assert cached == customer_data
        
        # Verify action is queued
        pending = sync_queue_service.get_pending_actions()
        assert len(pending) == 1

    def test_conflict_resolution_workflow(self, sync_queue_service, session):
        """Test complete conflict resolution workflow."""
        # Enqueue offline action
        entry = sync_queue_service.enqueue_action(
            "update", "customer", "123", {"name": "Local Update"}
        )
        session.commit()
        
        # Detect conflict during sync
        conflict = sync_queue_service.detect_conflict(
            entry.id, "customer", "123",
            {"name": "Local Update", "version": 1},
            {"name": "Remote Update", "version": 2},
            "update_conflict"
        )
        session.commit()
        
        # Resolve conflict
        resolved = sync_queue_service.resolve_conflict(
            conflict.id, "merge", 
            {"name": "Merged Update", "version": 3},
            "system"
        )
        session.commit()
        
        # Verify resolution
        assert resolved.resolution_strategy == "merge"
        unresolved = sync_queue_service.get_unresolved_conflicts()
        assert len(unresolved) == 0
