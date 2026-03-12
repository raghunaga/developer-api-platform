"""Repository classes for data access with hierarchy traversal."""

import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.entities import (
    Tenant, Customer, Site, Gateway, Device, User, DataStream,
    CacheEntry, SyncQueueEntry, DataConflict, SyncStatus,
    Permission, Role, RolePermission, AccessControl,
    ConflictResolution, AuditLogEntry,
    SLATargets, SLAMetric, PerformanceMetrics,
    DeviceCapabilities, InterfaceMode, InterfaceModePreferences
)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class with common CRUD operations."""

    def __init__(self, session: Session, model_class):
        """Initialize repository with session and model class."""
        self.session = session
        self.model_class = model_class

    def create(self, **kwargs) -> object:
        """Create a new entity."""
        entity = self.model_class(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity

    def get_by_id(self, entity_id: str) -> Optional[object]:
        """Get entity by ID."""
        return self.session.query(self.model_class).filter(
            self.model_class.id == entity_id
        ).first()

    def get_all(self) -> List[object]:
        """Get all entities."""
        return self.session.query(self.model_class).all()

    def update(self, entity_id: str, **kwargs) -> Optional[object]:
        """Update entity by ID."""
        entity = self.get_by_id(entity_id)
        if entity:
            for key, value in kwargs.items():
                setattr(entity, key, value)
            self.session.flush()
        return entity

    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        entity = self.get_by_id(entity_id)
        if entity:
            self.session.delete(entity)
            self.session.flush()
            return True
        return False

    def commit(self) -> None:
        """Commit transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback transaction."""
        self.session.rollback()


class TenantRepository(BaseRepository):
    """Repository for Tenant entities."""

    def __init__(self, session: Session):
        """Initialize TenantRepository."""
        super().__init__(session, Tenant)

    def get_by_identifier(self, identifier: str) -> Optional[Tenant]:
        """Get tenant by identifier."""
        return self.session.query(Tenant).filter(
            Tenant.identifier == identifier
        ).first()

    def get_active_tenants(self) -> List[Tenant]:
        """Get all active tenants."""
        return self.session.query(Tenant).filter(
            Tenant.status == "active"
        ).all()


class CustomerRepository(BaseRepository):
    """Repository for Customer entities with hierarchy traversal."""

    def __init__(self, session: Session):
        """Initialize CustomerRepository."""
        super().__init__(session, Customer)

    def get_by_identifier(self, identifier: str) -> Optional[Customer]:
        """Get customer by identifier."""
        return self.session.query(Customer).filter(
            Customer.identifier == identifier
        ).first()

    def get_by_tenant(self, tenant_id: str) -> List[Customer]:
        """Get all customers for a tenant."""
        return self.session.query(Customer).filter(
            Customer.tenant_id == tenant_id
        ).all()

    def get_parent(self, customer_id: str) -> Optional[Tenant]:
        """Get parent tenant of a customer."""
        customer = self.get_by_id(customer_id)
        if customer:
            return customer.tenant
        return None

    def get_children(self, customer_id: str) -> List[Site]:
        """Get all sites (children) of a customer."""
        customer = self.get_by_id(customer_id)
        if customer:
            return customer.sites
        return []

    def get_path(self, customer_id: str) -> List[Tuple[str, str]]:
        """Get hierarchy path from tenant to customer.
        
        Returns list of tuples (entity_type, entity_id).
        """
        customer = self.get_by_id(customer_id)
        if not customer:
            return []
        
        path = [("tenant", customer.tenant_id), ("customer", customer_id)]
        return path

    def get_active_customers(self) -> List[Customer]:
        """Get all active customers."""
        return self.session.query(Customer).filter(
            Customer.status == "active"
        ).all()


class SiteRepository(BaseRepository):
    """Repository for Site entities with hierarchy traversal."""

    def __init__(self, session: Session):
        """Initialize SiteRepository."""
        super().__init__(session, Site)

    def get_by_identifier(self, identifier: str) -> Optional[Site]:
        """Get site by identifier."""
        return self.session.query(Site).filter(
            Site.identifier == identifier
        ).first()

    def get_by_customer(self, customer_id: str) -> List[Site]:
        """Get all sites for a customer."""
        return self.session.query(Site).filter(
            Site.customer_id == customer_id
        ).all()

    def get_parent(self, site_id: str) -> Optional[Customer]:
        """Get parent customer of a site."""
        site = self.get_by_id(site_id)
        if site:
            return site.customer
        return None

    def get_children(self, site_id: str) -> Tuple[List[Gateway], List[User]]:
        """Get all gateways and users (children) of a site.
        
        Returns tuple of (gateways, users).
        """
        site = self.get_by_id(site_id)
        if site:
            return (site.gateways, site.users)
        return ([], [])

    def get_path(self, site_id: str) -> List[Tuple[str, str]]:
        """Get hierarchy path from tenant to site.
        
        Returns list of tuples (entity_type, entity_id).
        """
        site = self.get_by_id(site_id)
        if not site:
            return []
        
        path = [
            ("tenant", site.tenant_id),
            ("customer", site.customer_id),
            ("site", site_id)
        ]
        return path


class GatewayRepository(BaseRepository):
    """Repository for Gateway entities with hierarchy traversal."""

    def __init__(self, session: Session):
        """Initialize GatewayRepository."""
        super().__init__(session, Gateway)

    def get_by_identifier(self, identifier: str) -> Optional[Gateway]:
        """Get gateway by identifier."""
        return self.session.query(Gateway).filter(
            Gateway.identifier == identifier
        ).first()

    def get_by_site(self, site_id: str) -> List[Gateway]:
        """Get all gateways for a site."""
        return self.session.query(Gateway).filter(
            Gateway.site_id == site_id
        ).all()

    def get_parent(self, gateway_id: str) -> Optional[Site]:
        """Get parent site of a gateway."""
        gateway = self.get_by_id(gateway_id)
        if gateway:
            return gateway.site
        return None

    def get_children(self, gateway_id: str) -> List[Device]:
        """Get all devices (children) of a gateway."""
        gateway = self.get_by_id(gateway_id)
        if gateway:
            return gateway.devices
        return []

    def get_path(self, gateway_id: str) -> List[Tuple[str, str]]:
        """Get hierarchy path from tenant to gateway.
        
        Returns list of tuples (entity_type, entity_id).
        """
        gateway = self.get_by_id(gateway_id)
        if not gateway:
            return []
        
        path = [
            ("tenant", gateway.tenant_id),
            ("customer", gateway.customer_id),
            ("site", gateway.site_id),
            ("gateway", gateway_id)
        ]
        return path

    def get_by_status(self, status: str) -> List[Gateway]:
        """Get all gateways with a specific status."""
        return self.session.query(Gateway).filter(
            Gateway.status == status
        ).all()


class DeviceRepository(BaseRepository):
    """Repository for Device entities with hierarchy traversal."""

    def __init__(self, session: Session):
        """Initialize DeviceRepository."""
        super().__init__(session, Device)

    def get_by_identifier(self, identifier: str) -> Optional[Device]:
        """Get device by identifier."""
        return self.session.query(Device).filter(
            Device.identifier == identifier
        ).first()

    def get_by_gateway(self, gateway_id: str) -> List[Device]:
        """Get all devices for a gateway."""
        return self.session.query(Device).filter(
            Device.gateway_id == gateway_id
        ).all()

    def get_by_site(self, site_id: str) -> List[Device]:
        """Get all devices for a site."""
        return self.session.query(Device).filter(
            Device.site_id == site_id
        ).all()

    def get_parent(self, device_id: str) -> Optional[Gateway]:
        """Get parent gateway of a device."""
        device = self.get_by_id(device_id)
        if device:
            return device.gateway
        return None

    def get_children(self, device_id: str) -> List[DataStream]:
        """Get all data streams (children) of a device."""
        device = self.get_by_id(device_id)
        if device:
            return device.data_streams
        return []

    def get_path(self, device_id: str) -> List[Tuple[str, str]]:
        """Get hierarchy path from tenant to device.
        
        Returns list of tuples (entity_type, entity_id).
        """
        device = self.get_by_id(device_id)
        if not device:
            return []
        
        path = [
            ("tenant", device.tenant_id),
            ("customer", device.customer_id),
            ("site", device.site_id),
            ("gateway", device.gateway_id),
            ("device", device_id)
        ]
        return path

    def get_by_status(self, status: str) -> List[Device]:
        """Get all devices with a specific status."""
        return self.session.query(Device).filter(
            Device.status == status
        ).all()

    def get_by_customer(self, customer_id: str) -> List[Device]:
        """Get all devices for a customer."""
        return self.session.query(Device).filter(
            Device.customer_id == customer_id
        ).all()


class UserRepository(BaseRepository):
    """Repository for User entities with hierarchy traversal."""

    def __init__(self, session: Session):
        """Initialize UserRepository."""
        super().__init__(session, User)

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        """Get user by identifier."""
        return self.session.query(User).filter(
            User.identifier == identifier
        ).first()

    def get_by_site(self, site_id: str) -> List[User]:
        """Get all users for a site."""
        return self.session.query(User).filter(
            User.site_id == site_id
        ).all()

    def get_parent(self, user_id: str) -> Optional[Site]:
        """Get parent site of a user."""
        user = self.get_by_id(user_id)
        if user:
            return user.site
        return None

    def get_path(self, user_id: str) -> List[Tuple[str, str]]:
        """Get hierarchy path from tenant to user.
        
        Returns list of tuples (entity_type, entity_id).
        """
        user = self.get_by_id(user_id)
        if not user:
            return []
        
        path = [
            ("tenant", user.tenant_id),
            ("customer", user.customer_id),
            ("site", user.site_id),
            ("user", user_id)
        ]
        return path

    def get_by_role(self, role: str) -> List[User]:
        """Get all users with a specific role."""
        return self.session.query(User).filter(
            User.role == role
        ).all()


class DataStreamRepository(BaseRepository):
    """Repository for DataStream entities with hierarchy traversal."""

    def __init__(self, session: Session):
        """Initialize DataStreamRepository."""
        super().__init__(session, DataStream)

    def get_by_identifier(self, identifier: str) -> Optional[DataStream]:
        """Get data stream by identifier."""
        return self.session.query(DataStream).filter(
            DataStream.identifier == identifier
        ).first()

    def get_by_device(self, device_id: str) -> List[DataStream]:
        """Get all data streams for a device."""
        return self.session.query(DataStream).filter(
            DataStream.device_id == device_id
        ).all()

    def get_parent(self, data_stream_id: str) -> Optional[Device]:
        """Get parent device of a data stream."""
        data_stream = self.get_by_id(data_stream_id)
        if data_stream:
            return data_stream.device
        return None

    def get_path(self, data_stream_id: str) -> List[Tuple[str, str]]:
        """Get hierarchy path from tenant to data stream.
        
        Returns list of tuples (entity_type, entity_id).
        """
        data_stream = self.get_by_id(data_stream_id)
        if not data_stream:
            return []
        
        path = [
            ("tenant", data_stream.tenant_id),
            ("customer", data_stream.customer_id),
            ("site", data_stream.site_id),
            ("gateway", data_stream.gateway_id),
            ("device", data_stream.device_id),
            ("data_stream", data_stream_id)
        ]
        return path

    def get_by_data_type(self, data_type: str) -> List[DataStream]:
        """Get all data streams with a specific data type."""
        return self.session.query(DataStream).filter(
            DataStream.data_type == data_type
        ).all()

class CacheRepository(BaseRepository):
    """Repository for CacheEntry entities with TTL and invalidation management."""

    def __init__(self, session: Session):
        """Initialize CacheRepository."""
        super().__init__(session, CacheEntry)

    def get_by_key(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        return self.session.query(CacheEntry).filter(
            CacheEntry.key == key,
            CacheEntry.is_valid == True
        ).first()

    def get_by_entity(self, entity_type: str, entity_id: str) -> List[CacheEntry]:
        """Get all cache entries for an entity."""
        return self.session.query(CacheEntry).filter(
            CacheEntry.entity_type == entity_type,
            CacheEntry.entity_id == entity_id,
            CacheEntry.is_valid == True
        ).all()

    def get_expired_entries(self) -> List[CacheEntry]:
        """Get all expired cache entries."""
        from datetime import datetime
        return self.session.query(CacheEntry).filter(
            CacheEntry.expires_at <= datetime.utcnow(),
            CacheEntry.is_valid == True
        ).all()

    def invalidate_by_entity(self, entity_type: str, entity_id: str) -> int:
        """Invalidate all cache entries for an entity.
        
        Returns number of invalidated entries.
        """
        entries = self.session.query(CacheEntry).filter(
            CacheEntry.entity_type == entity_type,
            CacheEntry.entity_id == entity_id
        ).all()
        
        count = 0
        for entry in entries:
            entry.is_valid = False
            count += 1
        
        self.session.flush()
        return count

    def invalidate_by_type(self, entity_type: str) -> int:
        """Invalidate all cache entries of a type.
        
        Returns number of invalidated entries.
        """
        entries = self.session.query(CacheEntry).filter(
            CacheEntry.entity_type == entity_type
        ).all()
        
        count = 0
        for entry in entries:
            entry.is_valid = False
            count += 1
        
        self.session.flush()
        return count

    def clean_expired_entries(self) -> int:
        """Delete all expired cache entries.
        
        Returns number of deleted entries.
        """
        expired = self.get_expired_entries()
        count = len(expired)
        
        for entry in expired:
            self.session.delete(entry)
        
        self.session.flush()
        return count

    def get_cache_size(self) -> int:
        """Get total number of valid cache entries."""
        return self.session.query(CacheEntry).filter(
            CacheEntry.is_valid == True
        ).count()


class SyncQueueRepository(BaseRepository):
    """Repository for SyncQueueEntry entities with conflict detection."""

    def __init__(self, session: Session):
        """Initialize SyncQueueRepository."""
        super().__init__(session, SyncQueueEntry)

    def get_pending_entries(self) -> List[SyncQueueEntry]:
        """Get all pending sync queue entries ordered by priority and creation time."""
        return self.session.query(SyncQueueEntry).filter(
            SyncQueueEntry.status == "pending"
        ).order_by(
            SyncQueueEntry.priority.desc(),
            SyncQueueEntry.created_at.asc()
        ).all()

    def get_by_status(self, status: str) -> List[SyncQueueEntry]:
        """Get all sync queue entries with a specific status."""
        return self.session.query(SyncQueueEntry).filter(
            SyncQueueEntry.status == status
        ).all()

    def get_by_entity(self, entity_type: str, entity_id: str) -> List[SyncQueueEntry]:
        """Get all sync queue entries for an entity."""
        return self.session.query(SyncQueueEntry).filter(
            SyncQueueEntry.entity_type == entity_type,
            SyncQueueEntry.entity_id == entity_id
        ).all()

    def get_failed_entries(self) -> List[SyncQueueEntry]:
        """Get all failed sync queue entries."""
        return self.session.query(SyncQueueEntry).filter(
            SyncQueueEntry.status == "failed"
        ).all()

    def get_conflict_entries(self) -> List[SyncQueueEntry]:
        """Get all sync queue entries with conflicts."""
        return self.session.query(SyncQueueEntry).filter(
            SyncQueueEntry.status == "conflict"
        ).all()

    def get_by_user(self, user_id: str) -> List[SyncQueueEntry]:
        """Get all sync queue entries created by a user."""
        return self.session.query(SyncQueueEntry).filter(
            SyncQueueEntry.user_id == user_id
        ).all()

    def get_by_device(self, device_id: str) -> List[SyncQueueEntry]:
        """Get all sync queue entries created by a device."""
        return self.session.query(SyncQueueEntry).filter(
            SyncQueueEntry.device_id == device_id
        ).all()

    def increment_retry_count(self, entry_id: str) -> Optional[SyncQueueEntry]:
        """Increment retry count for a sync queue entry."""
        from datetime import datetime
        entry = self.get_by_id(entry_id)
        if entry:
            entry.retry_count += 1
            entry.last_retry_at = datetime.utcnow()
            self.session.flush()
        return entry

    def mark_synced(self, entry_id: str) -> Optional[SyncQueueEntry]:
        """Mark a sync queue entry as synced."""
        entry = self.get_by_id(entry_id)
        if entry:
            entry.status = "synced"
            self.session.flush()
        return entry

    def mark_failed(self, entry_id: str, error_message: str) -> Optional[SyncQueueEntry]:
        """Mark a sync queue entry as failed."""
        entry = self.get_by_id(entry_id)
        if entry:
            entry.status = "failed"
            entry.error_message = error_message
            self.session.flush()
        return entry

    def mark_conflict(self, entry_id: str) -> Optional[SyncQueueEntry]:
        """Mark a sync queue entry as having a conflict."""
        entry = self.get_by_id(entry_id)
        if entry:
            entry.status = "conflict"
            self.session.flush()
        return entry

    def get_queue_size(self) -> int:
        """Get total number of pending sync queue entries."""
        return self.session.query(SyncQueueEntry).filter(
            SyncQueueEntry.status == "pending"
        ).count()


class DataConflictRepository(BaseRepository):
    """Repository for DataConflict entities."""

    def __init__(self, session: Session):
        """Initialize DataConflictRepository."""
        super().__init__(session, DataConflict)

    def get_by_sync_queue_entry(self, sync_queue_entry_id: str) -> Optional[DataConflict]:
        """Get conflict for a sync queue entry."""
        return self.session.query(DataConflict).filter(
            DataConflict.sync_queue_entry_id == sync_queue_entry_id
        ).first()

    def get_by_entity(self, entity_type: str, entity_id: str) -> List[DataConflict]:
        """Get all conflicts for an entity."""
        return self.session.query(DataConflict).filter(
            DataConflict.entity_type == entity_type,
            DataConflict.entity_id == entity_id
        ).all()

    def get_unresolved_conflicts(self) -> List[DataConflict]:
        """Get all unresolved conflicts."""
        return self.session.query(DataConflict).filter(
            DataConflict.resolved_at == None
        ).all()

    def get_by_conflict_type(self, conflict_type: str) -> List[DataConflict]:
        """Get all conflicts of a specific type."""
        return self.session.query(DataConflict).filter(
            DataConflict.conflict_type == conflict_type
        ).all()

    def mark_resolved(self, conflict_id: str, resolved_version: str, resolved_by: str) -> Optional[DataConflict]:
        """Mark a conflict as resolved."""
        from datetime import datetime
        conflict = self.get_by_id(conflict_id)
        if conflict:
            conflict.resolved_version = resolved_version
            conflict.resolved_by = resolved_by
            conflict.resolved_at = datetime.utcnow()
            self.session.flush()
        return conflict

    def get_conflict_count(self) -> int:
        """Get total number of unresolved conflicts."""
        return self.session.query(DataConflict).filter(
            DataConflict.resolved_at == None
        ).count()


class SyncStatusRepository(BaseRepository):
    """Repository for SyncStatus entities."""

    def __init__(self, session: Session):
        """Initialize SyncStatusRepository."""
        super().__init__(session, SyncStatus)

    def get_global_status(self) -> Optional[SyncStatus]:
        """Get global sync status (device_id is null)."""
        return self.session.query(SyncStatus).filter(
            SyncStatus.device_id == None
        ).first()

    def get_device_status(self, device_id: str) -> Optional[SyncStatus]:
        """Get sync status for a specific device."""
        return self.session.query(SyncStatus).filter(
            SyncStatus.device_id == device_id
        ).first()

    def get_all_device_statuses(self) -> List[SyncStatus]:
        """Get sync status for all devices."""
        return self.session.query(SyncStatus).filter(
            SyncStatus.device_id != None
        ).all()

    def get_syncing_statuses(self) -> List[SyncStatus]:
        """Get all currently syncing statuses."""
        return self.session.query(SyncStatus).filter(
            SyncStatus.status == "syncing"
        ).all()

    def update_progress(self, status_id: str, synced_entries: int, failed_entries: int, 
                       conflict_entries: int) -> Optional[SyncStatus]:
        """Update sync progress."""
        status = self.get_by_id(status_id)
        if status:
            status.synced_entries = synced_entries
            status.failed_entries = failed_entries
            status.conflict_entries = conflict_entries
            self.session.flush()
        return status

    def mark_syncing(self, status_id: str, total_entries: int) -> Optional[SyncStatus]:
        """Mark sync status as syncing."""
        from datetime import datetime
        status = self.get_by_id(status_id)
        if status:
            status.status = "syncing"
            status.total_entries = total_entries
            status.synced_entries = 0
            status.failed_entries = 0
            status.conflict_entries = 0
            status.last_sync_at = datetime.utcnow()
            self.session.flush()
        return status

    def mark_idle(self, status_id: str) -> Optional[SyncStatus]:
        """Mark sync status as idle."""
        status = self.get_by_id(status_id)
        if status:
            status.status = "idle"
            status.estimated_completion_time = None
            self.session.flush()
        return status

    def mark_error(self, status_id: str, error_message: str) -> Optional[SyncStatus]:
        """Mark sync status as error."""
        status = self.get_by_id(status_id)
        if status:
            status.status = "error"
            status.error_message = error_message
            self.session.flush()
        return status



class RepositoryFactory:
    """Factory for creating repository instances."""

    def __init__(self, session: Session):
        """Initialize factory with session."""
        self.session = session
        self._repositories = {}

    def get_tenant_repository(self) -> TenantRepository:
        """Get or create TenantRepository."""
        if "tenant" not in self._repositories:
            self._repositories["tenant"] = TenantRepository(self.session)
        return self._repositories["tenant"]

    def get_customer_repository(self) -> CustomerRepository:
        """Get or create CustomerRepository."""
        if "customer" not in self._repositories:
            self._repositories["customer"] = CustomerRepository(self.session)
        return self._repositories["customer"]

    def get_site_repository(self) -> SiteRepository:
        """Get or create SiteRepository."""
        if "site" not in self._repositories:
            self._repositories["site"] = SiteRepository(self.session)
        return self._repositories["site"]

    def get_gateway_repository(self) -> GatewayRepository:
        """Get or create GatewayRepository."""
        if "gateway" not in self._repositories:
            self._repositories["gateway"] = GatewayRepository(self.session)
        return self._repositories["gateway"]

    def get_device_repository(self) -> DeviceRepository:
        """Get or create DeviceRepository."""
        if "device" not in self._repositories:
            self._repositories["device"] = DeviceRepository(self.session)
        return self._repositories["device"]

    def get_user_repository(self) -> UserRepository:
        """Get or create UserRepository."""
        if "user" not in self._repositories:
            self._repositories["user"] = UserRepository(self.session)
        return self._repositories["user"]

    def get_data_stream_repository(self) -> DataStreamRepository:
        """Get or create DataStreamRepository."""
        if "data_stream" not in self._repositories:
            self._repositories["data_stream"] = DataStreamRepository(self.session)
        return self._repositories["data_stream"]

    def get_cache_repository(self) -> CacheRepository:
        """Get or create CacheRepository."""
        if "cache" not in self._repositories:
            self._repositories["cache"] = CacheRepository(self.session)
        return self._repositories["cache"]

    def get_sync_queue_repository(self) -> SyncQueueRepository:
        """Get or create SyncQueueRepository."""
        if "sync_queue" not in self._repositories:
            self._repositories["sync_queue"] = SyncQueueRepository(self.session)
        return self._repositories["sync_queue"]

    def get_data_conflict_repository(self) -> DataConflictRepository:
        """Get or create DataConflictRepository."""
        if "data_conflict" not in self._repositories:
            self._repositories["data_conflict"] = DataConflictRepository(self.session)
        return self._repositories["data_conflict"]

    def get_sync_status_repository(self) -> SyncStatusRepository:
        """Get or create SyncStatusRepository."""
        if "sync_status" not in self._repositories:
            self._repositories["sync_status"] = SyncStatusRepository(self.session)
        return self._repositories["sync_status"]

    def get_permission_repository(self) -> PermissionRepository:
        """Get or create PermissionRepository."""
        if "permission" not in self._repositories:
            self._repositories["permission"] = PermissionRepository(self.session)
        return self._repositories["permission"]

    def get_role_repository(self) -> RoleRepository:
        """Get or create RoleRepository."""
        if "role" not in self._repositories:
            self._repositories["role"] = RoleRepository(self.session)
        return self._repositories["role"]

    def get_role_permission_repository(self) -> RolePermissionRepository:
        """Get or create RolePermissionRepository."""
        if "role_permission" not in self._repositories:
            self._repositories["role_permission"] = RolePermissionRepository(self.session)
        return self._repositories["role_permission"]

    def get_access_control_repository(self) -> AccessControlRepository:
        """Get or create AccessControlRepository."""
        if "access_control" not in self._repositories:
            self._repositories["access_control"] = AccessControlRepository(self.session)
        return self._repositories["access_control"]

    def get_conflict_resolution_repository(self) -> ConflictResolutionRepository:
        """Get or create ConflictResolutionRepository."""
        if "conflict_resolution" not in self._repositories:
            self._repositories["conflict_resolution"] = ConflictResolutionRepository(self.session)
        return self._repositories["conflict_resolution"]

    def get_audit_log_repository(self) -> AuditLogRepository:
        """Get or create AuditLogRepository."""
        if "audit_log" not in self._repositories:
            self._repositories["audit_log"] = AuditLogRepository(self.session)
        return self._repositories["audit_log"]

    def get_sla_targets_repository(self) -> SLATargetsRepository:
        """Get or create SLATargetsRepository."""
        if "sla_targets" not in self._repositories:
            self._repositories["sla_targets"] = SLATargetsRepository(self.session)
        return self._repositories["sla_targets"]

    def get_sla_metric_repository(self) -> SLAMetricRepository:
        """Get or create SLAMetricRepository."""
        if "sla_metric" not in self._repositories:
            self._repositories["sla_metric"] = SLAMetricRepository(self.session)
        return self._repositories["sla_metric"]

    def get_performance_metrics_repository(self) -> PerformanceMetricsRepository:
        """Get or create PerformanceMetricsRepository."""
        if "performance_metrics" not in self._repositories:
            self._repositories["performance_metrics"] = PerformanceMetricsRepository(self.session)
        return self._repositories["performance_metrics"]

    def get_device_capabilities_repository(self) -> DeviceCapabilitiesRepository:
        """Get or create DeviceCapabilitiesRepository."""
        if "device_capabilities" not in self._repositories:
            self._repositories["device_capabilities"] = DeviceCapabilitiesRepository(self.session)
        return self._repositories["device_capabilities"]

    def get_interface_mode_repository(self) -> InterfaceModeRepository:
        """Get or create InterfaceModeRepository."""
        if "interface_mode" not in self._repositories:
            self._repositories["interface_mode"] = InterfaceModeRepository(self.session)
        return self._repositories["interface_mode"]

    def get_interface_mode_preferences_repository(self) -> InterfaceModePreferencesRepository:
        """Get or create InterfaceModePreferencesRepository."""
        if "interface_mode_preferences" not in self._repositories:
            self._repositories["interface_mode_preferences"] = InterfaceModePreferencesRepository(self.session)
        return self._repositories["interface_mode_preferences"]


class PermissionRepository(BaseRepository):
    """Repository for Permission entities."""

    def __init__(self, session: Session):
        super().__init__(session, Permission)

    def get_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name."""
        return self.session.query(Permission).filter(Permission.name == name).first()

    def get_by_resource_action(self, resource: str, action: str) -> List[Permission]:
        """Get permissions by resource and action."""
        return self.session.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action
        ).all()

    def get_by_resource(self, resource: str) -> List[Permission]:
        """Get all permissions for a resource."""
        return self.session.query(Permission).filter(Permission.resource == resource).all()


class RoleRepository(BaseRepository):
    """Repository for Role entities."""

    def __init__(self, session: Session):
        super().__init__(session, Role)

    def get_by_tenant(self, tenant_id: str) -> List[Role]:
        """Get all roles for a tenant."""
        return self.session.query(Role).filter(Role.tenant_id == tenant_id).all()

    def get_by_name(self, tenant_id: str, name: str) -> Optional[Role]:
        """Get role by tenant and name."""
        return self.session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.name == name
        ).first()

    def get_role_hierarchy(self, role_id: str) -> List[Role]:
        """Get role and all parent roles."""
        roles = []
        current_role = self.get_by_id(role_id)
        while current_role:
            roles.append(current_role)
            current_role = current_role.parent_role
        return roles


class RolePermissionRepository(BaseRepository):
    """Repository for RolePermission entities."""

    def __init__(self, session: Session):
        super().__init__(session, RolePermission)

    def get_by_role(self, role_id: str) -> List[RolePermission]:
        """Get all permissions for a role."""
        return self.session.query(RolePermission).filter(RolePermission.role_id == role_id).all()

    def get_by_permission(self, permission_id: str) -> List[RolePermission]:
        """Get all roles with a permission."""
        return self.session.query(RolePermission).filter(RolePermission.permission_id == permission_id).all()

    def add_permission_to_role(self, role_id: str, permission_id: str) -> RolePermission:
        """Add a permission to a role."""
        return self.create(role_id=role_id, permission_id=permission_id)

    def remove_permission_from_role(self, role_id: str, permission_id: str) -> bool:
        """Remove a permission from a role."""
        entry = self.session.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        ).first()
        if entry:
            self.session.delete(entry)
            self.commit()
            return True
        return False


class AccessControlRepository(BaseRepository):
    """Repository for AccessControl entities."""

    def __init__(self, session: Session):
        super().__init__(session, AccessControl)

    def get_by_user(self, user_id: str) -> List[AccessControl]:
        """Get all access controls for a user."""
        return self.session.query(AccessControl).filter(AccessControl.user_id == user_id).all()

    def get_by_role(self, role_id: str) -> List[AccessControl]:
        """Get all access controls with a role."""
        return self.session.query(AccessControl).filter(AccessControl.role_id == role_id).all()

    def get_by_resource(self, resource_type: str, resource_id: str) -> List[AccessControl]:
        """Get all access controls for a resource."""
        return self.session.query(AccessControl).filter(
            AccessControl.resource_type == resource_type,
            AccessControl.resource_id == resource_id
        ).all()

    def has_access(self, user_id: str, resource_type: str, resource_id: str) -> bool:
        """Check if user has access to a resource."""
        return self.session.query(AccessControl).filter(
            AccessControl.user_id == user_id,
            AccessControl.resource_type == resource_type,
            AccessControl.resource_id == resource_id
        ).first() is not None


class ConflictResolutionRepository(BaseRepository):
    """Repository for ConflictResolution entities."""

    def __init__(self, session: Session):
        super().__init__(session, ConflictResolution)

    def get_by_conflict(self, data_conflict_id: str) -> Optional[ConflictResolution]:
        """Get resolution for a conflict."""
        return self.session.query(ConflictResolution).filter(
            ConflictResolution.data_conflict_id == data_conflict_id
        ).first()

    def get_by_strategy(self, strategy: str) -> List[ConflictResolution]:
        """Get all resolutions using a strategy."""
        return self.session.query(ConflictResolution).filter(
            ConflictResolution.resolution_strategy == strategy
        ).all()


class AuditLogRepository(BaseRepository):
    """Repository for AuditLogEntry entities."""

    def __init__(self, session: Session):
        super().__init__(session, AuditLogEntry)

    def get_by_user(self, user_id: str, limit: int = 100) -> List[AuditLogEntry]:
        """Get audit logs for a user."""
        return self.session.query(AuditLogEntry).filter(
            AuditLogEntry.user_id == user_id
        ).order_by(AuditLogEntry.created_at.desc()).limit(limit).all()

    def get_by_entity(self, entity_type: str, entity_id: str, limit: int = 100) -> List[AuditLogEntry]:
        """Get audit logs for an entity."""
        return self.session.query(AuditLogEntry).filter(
            AuditLogEntry.entity_type == entity_type,
            AuditLogEntry.entity_id == entity_id
        ).order_by(AuditLogEntry.created_at.desc()).limit(limit).all()

    def get_by_action(self, action: str, limit: int = 100) -> List[AuditLogEntry]:
        """Get audit logs by action type."""
        return self.session.query(AuditLogEntry).filter(
            AuditLogEntry.action == action
        ).order_by(AuditLogEntry.created_at.desc()).limit(limit).all()

    def get_by_date_range(self, start_date, end_date, limit: int = 1000) -> List[AuditLogEntry]:
        """Get audit logs within a date range."""
        return self.session.query(AuditLogEntry).filter(
            AuditLogEntry.created_at >= start_date,
            AuditLogEntry.created_at <= end_date
        ).order_by(AuditLogEntry.created_at.desc()).limit(limit).all()

    def get_failed_actions(self, limit: int = 100) -> List[AuditLogEntry]:
        """Get failed audit log entries."""
        return self.session.query(AuditLogEntry).filter(
            AuditLogEntry.status != "success"
        ).order_by(AuditLogEntry.created_at.desc()).limit(limit).all()


class SLATargetsRepository(BaseRepository):
    """Repository for SLATargets entities."""

    def __init__(self, session: Session):
        super().__init__(session, SLATargets)

    def get_by_tenant(self, tenant_id: str) -> List[SLATargets]:
        """Get all SLA targets for a tenant."""
        return self.session.query(SLATargets).filter(SLATargets.tenant_id == tenant_id).all()

    def get_by_metric(self, metric_name: str) -> List[SLATargets]:
        """Get all SLA targets for a metric."""
        return self.session.query(SLATargets).filter(SLATargets.metric_name == metric_name).all()


class SLAMetricRepository(BaseRepository):
    """Repository for SLAMetric entities."""

    def __init__(self, session: Session):
        super().__init__(session, SLAMetric)

    def get_by_sla_target(self, sla_target_id: str) -> List[SLAMetric]:
        """Get all metrics for an SLA target."""
        return self.session.query(SLAMetric).filter(SLAMetric.sla_target_id == sla_target_id).all()

    def get_by_customer(self, customer_id: str) -> List[SLAMetric]:
        """Get all SLA metrics for a customer."""
        return self.session.query(SLAMetric).filter(SLAMetric.customer_id == customer_id).all()

    def get_by_site(self, site_id: str) -> List[SLAMetric]:
        """Get all SLA metrics for a site."""
        return self.session.query(SLAMetric).filter(SLAMetric.site_id == site_id).all()

    def get_non_compliant(self) -> List[SLAMetric]:
        """Get all non-compliant SLA metrics."""
        return self.session.query(SLAMetric).filter(
            SLAMetric.compliance_status != "compliant"
        ).all()


class PerformanceMetricsRepository(BaseRepository):
    """Repository for PerformanceMetrics entities."""

    def __init__(self, session: Session):
        super().__init__(session, PerformanceMetrics)

    def get_by_type(self, metric_type: str, limit: int = 100) -> List[PerformanceMetrics]:
        """Get metrics by type."""
        return self.session.query(PerformanceMetrics).filter(
            PerformanceMetrics.metric_type == metric_type
        ).order_by(PerformanceMetrics.created_at.desc()).limit(limit).all()

    def get_by_component(self, component: str, limit: int = 100) -> List[PerformanceMetrics]:
        """Get metrics by component."""
        return self.session.query(PerformanceMetrics).filter(
            PerformanceMetrics.component == component
        ).order_by(PerformanceMetrics.created_at.desc()).limit(limit).all()

    def get_by_device(self, device_id: str, limit: int = 100) -> List[PerformanceMetrics]:
        """Get metrics for a device."""
        return self.session.query(PerformanceMetrics).filter(
            PerformanceMetrics.device_id == device_id
        ).order_by(PerformanceMetrics.created_at.desc()).limit(limit).all()

    def get_by_customer(self, customer_id: str, limit: int = 100) -> List[PerformanceMetrics]:
        """Get metrics for a customer."""
        return self.session.query(PerformanceMetrics).filter(
            PerformanceMetrics.customer_id == customer_id
        ).order_by(PerformanceMetrics.created_at.desc()).limit(limit).all()


class DeviceCapabilitiesRepository(BaseRepository):
    """Repository for DeviceCapabilities entities."""

    def __init__(self, session: Session):
        super().__init__(session, DeviceCapabilities)

    def get_by_device(self, device_id: str) -> List[DeviceCapabilities]:
        """Get all capabilities for a device."""
        return self.session.query(DeviceCapabilities).filter(
            DeviceCapabilities.device_id == device_id
        ).all()

    def get_by_capability(self, capability_name: str) -> List[DeviceCapabilities]:
        """Get all devices with a capability."""
        return self.session.query(DeviceCapabilities).filter(
            DeviceCapabilities.capability_name == capability_name,
            DeviceCapabilities.is_available == True
        ).all()

    def has_capability(self, device_id: str, capability_name: str) -> bool:
        """Check if device has a capability."""
        return self.session.query(DeviceCapabilities).filter(
            DeviceCapabilities.device_id == device_id,
            DeviceCapabilities.capability_name == capability_name,
            DeviceCapabilities.is_available == True
        ).first() is not None


class InterfaceModeRepository(BaseRepository):
    """Repository for InterfaceMode entities."""

    def __init__(self, session: Session):
        super().__init__(session, InterfaceMode)

    def get_by_name(self, mode_name: str) -> Optional[InterfaceMode]:
        """Get interface mode by name."""
        return self.session.query(InterfaceMode).filter(
            InterfaceMode.mode_name == mode_name
        ).first()

    def get_all_ordered(self) -> List[InterfaceMode]:
        """Get all interface modes ordered by priority."""
        return self.session.query(InterfaceMode).order_by(InterfaceMode.priority.desc()).all()


class InterfaceModePreferencesRepository(BaseRepository):
    """Repository for InterfaceModePreferences entities."""

    def __init__(self, session: Session):
        super().__init__(session, InterfaceModePreferences)

    def get_by_user(self, user_id: str) -> Optional[InterfaceModePreferences]:
        """Get interface mode preferences for a user."""
        return self.session.query(InterfaceModePreferences).filter(
            InterfaceModePreferences.user_id == user_id
        ).first()

    def update_preferences(self, user_id: str, **kwargs) -> Optional[InterfaceModePreferences]:
        """Update user's interface mode preferences."""
        prefs = self.get_by_user(user_id)
        if prefs:
            return self.update(prefs.id, **kwargs)
        return None
