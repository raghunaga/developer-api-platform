"""Cache management service for offline-first caching."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, List
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.repositories import CacheRepository
from app.models.entities import CacheEntry

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing local cache storage with TTL and invalidation."""

    def __init__(self, session: Session):
        """Initialize cache service."""
        self.session = session
        self.cache_repo = CacheRepository(session)

    def set(self, key: str, entity_type: str, entity_id: str, data: Any, 
            ttl_seconds: Optional[int] = None) -> CacheEntry:
        """Store data in cache with optional TTL.
        
        Args:
            key: Unique cache key
            entity_type: Type of entity (e.g., 'customer', 'device')
            entity_id: ID of the entity
            data: Data to cache (will be JSON serialized)
            ttl_seconds: Time to live in seconds (None = no expiration)
        
        Returns:
            CacheEntry object
        """
        # Check if entry already exists
        existing = self.cache_repo.get_by_key(key)
        if existing:
            # Update existing entry
            existing.data = json.dumps(data)
            existing.updated_at = datetime.utcnow()
            existing.version += 1
            existing.is_valid = True
            
            if ttl_seconds:
                existing.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            else:
                existing.expires_at = None
            
            self.session.flush()
            logger.debug(f"Updated cache entry: {key}")
            return existing
        
        # Create new entry
        entry = CacheEntry(
            id=str(uuid4()),
            key=key,
            entity_type=entity_type,
            entity_id=entity_id,
            data=json.dumps(data),
            version=1,
            is_valid=True,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        )
        self.session.add(entry)
        self.session.flush()
        logger.debug(f"Created cache entry: {key}")
        return entry

    def get(self, key: str) -> Optional[Any]:
        """Retrieve data from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached data or None if not found or expired
        """
        entry = self.cache_repo.get_by_key(key)
        if not entry:
            logger.debug(f"Cache miss: {key}")
            return None
        
        # Check if expired
        if entry.expires_at and entry.expires_at <= datetime.utcnow():
            logger.debug(f"Cache entry expired: {key}")
            entry.is_valid = False
            self.session.flush()
            return None
        
        logger.debug(f"Cache hit: {key}")
        return json.loads(entry.data)

    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """Retrieve cache entry object.
        
        Args:
            key: Cache key
        
        Returns:
            CacheEntry object or None
        """
        return self.cache_repo.get_by_key(key)

    def delete(self, key: str) -> bool:
        """Delete cache entry.
        
        Args:
            key: Cache key
        
        Returns:
            True if deleted, False if not found
        """
        entry = self.cache_repo.get_by_key(key)
        if entry:
            self.session.delete(entry)
            self.session.flush()
            logger.debug(f"Deleted cache entry: {key}")
            return True
        return False

    def invalidate_entity(self, entity_type: str, entity_id: str) -> int:
        """Invalidate all cache entries for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of entity
        
        Returns:
            Number of invalidated entries
        """
        count = self.cache_repo.invalidate_by_entity(entity_type, entity_id)
        self.session.flush()
        logger.info(f"Invalidated {count} cache entries for {entity_type}:{entity_id}")
        return count

    def invalidate_type(self, entity_type: str) -> int:
        """Invalidate all cache entries of a type.
        
        Args:
            entity_type: Type of entity
        
        Returns:
            Number of invalidated entries
        """
        count = self.cache_repo.invalidate_by_type(entity_type)
        self.session.flush()
        logger.info(f"Invalidated {count} cache entries of type {entity_type}")
        return count

    def invalidate_all(self) -> int:
        """Invalidate all cache entries.
        
        Returns:
            Number of invalidated entries
        """
        entries = self.session.query(CacheEntry).filter(
            CacheEntry.is_valid == True
        ).all()
        
        count = 0
        for entry in entries:
            entry.is_valid = False
            count += 1
        
        self.session.flush()
        logger.info(f"Invalidated all {count} cache entries")
        return count

    def clean_expired(self) -> int:
        """Delete all expired cache entries.
        
        Returns:
            Number of deleted entries
        """
        count = self.cache_repo.clean_expired_entries()
        self.session.flush()
        logger.info(f"Cleaned {count} expired cache entries")
        return count

    def get_cache_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_entries = self.session.query(CacheEntry).count()
        valid_entries = self.cache_repo.get_cache_size()
        expired_entries = len(self.cache_repo.get_expired_entries())
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "invalid_entries": total_entries - valid_entries - expired_entries
        }

    def get_entity_cache(self, entity_type: str, entity_id: str) -> List[dict]:
        """Get all cache entries for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of entity
        
        Returns:
            List of cache entry data
        """
        entries = self.cache_repo.get_by_entity(entity_type, entity_id)
        return [
            {
                "key": entry.key,
                "data": json.loads(entry.data),
                "version": entry.version,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
                "expires_at": entry.expires_at.isoformat() if entry.expires_at else None
            }
            for entry in entries
        ]
