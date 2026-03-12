"""Core data models for the hierarchical device dashboard."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base


class Tenant(Base):
    """Tenant entity - top-level organizational unit."""

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    identifier = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="active", nullable=False)

    # Relationships
    customers = relationship("Customer", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name})>"


class Customer(Base):
    """Customer entity - customer account within a tenant."""

    __tablename__ = "customers"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    identifier = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="active", nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="customers")
    sites = relationship("Site", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name={self.name})>"


class Site(Base):
    """Site entity - physical or logical location within a customer."""

    __tablename__ = "sites"

    id = Column(String(36), primary_key=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    identifier = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="sites")
    tenant = relationship("Tenant")
    gateways = relationship("Gateway", back_populates="site", cascade="all, delete-orphan")
    users = relationship("User", back_populates="site", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Site(id={self.id}, name={self.name})>"


class Gateway(Base):
    """Gateway entity - edge computing device that collects data from devices."""

    __tablename__ = "gateways"

    id = Column(String(36), primary_key=True)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    identifier = Column(String(255), nullable=False)
    gateway_type = Column(String(100), nullable=False)
    status = Column(String(50), default="online", nullable=False)
    last_update = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    site = relationship("Site", back_populates="gateways")
    customer = relationship("Customer")
    tenant = relationship("Tenant")
    devices = relationship("Device", back_populates="gateway", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Gateway(id={self.id}, name={self.name})>"


class Device(Base):
    """Device entity - edge device connected to a gateway."""

    __tablename__ = "devices"

    id = Column(String(36), primary_key=True)
    gateway_id = Column(String(36), ForeignKey("gateways.id"), nullable=False)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    identifier = Column(String(255), nullable=False)
    device_type = Column(String(100), nullable=False)
    status = Column(String(50), default="online", nullable=False)
    last_update = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    gateway = relationship("Gateway", back_populates="devices")
    site = relationship("Site")
    customer = relationship("Customer")
    tenant = relationship("Tenant")
    data_streams = relationship("DataStream", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, name={self.name})>"


class User(Base):
    """User entity - individual user account associated with a site."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    identifier = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    site = relationship("Site", back_populates="users")
    customer = relationship("Customer")
    tenant = relationship("Tenant")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name})>"


class DataStream(Base):
    """DataStream entity - continuous stream of metrics from a device."""

    __tablename__ = "data_streams"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False)
    gateway_id = Column(String(36), ForeignKey("gateways.id"), nullable=False)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    identifier = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)
    unit = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    device = relationship("Device", back_populates="data_streams")
    gateway = relationship("Gateway")
    site = relationship("Site")
    customer = relationship("Customer")
    tenant = relationship("Tenant")

    def __repr__(self) -> str:
        return f"<DataStream(id={self.id}, name={self.name})>"



class CacheEntry(Base):
    """CacheEntry entity - local cache storage for offline access."""

    __tablename__ = "cache_entries"

    id = Column(String(36), primary_key=True)
    key = Column(String(512), unique=True, nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)  # 'customer', 'site', 'device', etc.
    entity_id = Column(String(36), nullable=False, index=True)
    data = Column(String, nullable=False)  # JSON serialized data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)  # TTL expiration time
    version = Column(Integer, default=1, nullable=False)  # For conflict detection
    is_valid = Column(Boolean, default=True, nullable=False)  # For cache invalidation

    def __repr__(self) -> str:
        return f"<CacheEntry(id={self.id}, key={self.key}, entity_type={self.entity_type})>"


class SyncQueueEntry(Base):
    """SyncQueueEntry entity - queue for user actions during offline periods."""

    __tablename__ = "sync_queue_entries"

    id = Column(String(36), primary_key=True)
    action_type = Column(String(100), nullable=False, index=True)  # 'create', 'update', 'delete'
    entity_type = Column(String(100), nullable=False, index=True)  # 'customer', 'site', 'device', etc.
    entity_id = Column(String(36), nullable=False, index=True)
    payload = Column(String, nullable=False)  # JSON serialized action data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # 'pending', 'syncing', 'synced', 'failed', 'conflict'
    retry_count = Column(Integer, default=0, nullable=False)
    last_retry_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    conflict_resolution = Column(String, nullable=True)  # JSON serialized conflict resolution strategy
    user_id = Column(String(36), nullable=True)  # User who initiated the action
    device_id = Column(String(36), nullable=True)  # Device that initiated the action
    priority = Column(Integer, default=0, nullable=False, index=True)  # Higher priority syncs first

    def __repr__(self) -> str:
        return f"<SyncQueueEntry(id={self.id}, action_type={self.action_type}, status={self.status})>"


class DataConflict(Base):
    """DataConflict entity - tracks data conflicts during sync."""

    __tablename__ = "data_conflicts"

    id = Column(String(36), primary_key=True)
    sync_queue_entry_id = Column(String(36), ForeignKey("sync_queue_entries.id"), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(36), nullable=False, index=True)
    local_version = Column(String, nullable=False)  # JSON serialized local version
    remote_version = Column(String, nullable=False)  # JSON serialized remote version
    conflict_type = Column(String(100), nullable=False)  # 'update_conflict', 'delete_conflict', 'version_mismatch'
    resolution_strategy = Column(String(100), nullable=False, index=True)  # 'local_wins', 'remote_wins', 'merge', 'manual'
    resolved_version = Column(String, nullable=True)  # JSON serialized resolved version
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(36), nullable=True)  # User ID who resolved the conflict

    def __repr__(self) -> str:
        return f"<DataConflict(id={self.id}, entity_type={self.entity_type}, conflict_type={self.conflict_type})>"


class SyncStatus(Base):
    """SyncStatus entity - tracks overall sync status and progress."""

    __tablename__ = "sync_status"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), nullable=True, index=True)  # Device performing sync, null for global
    status = Column(String(50), default="idle", nullable=False, index=True)  # 'idle', 'syncing', 'paused', 'error'
    total_entries = Column(Integer, default=0, nullable=False)
    synced_entries = Column(Integer, default=0, nullable=False)
    failed_entries = Column(Integer, default=0, nullable=False)
    conflict_entries = Column(Integer, default=0, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)
    estimated_completion_time = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<SyncStatus(id={self.id}, status={self.status}, synced={self.synced_entries}/{self.total_entries})>"


class Permission(Base):
    """Permission entity - defines granular permissions for RBAC."""

    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    resource = Column(String(100), nullable=False, index=True)  # 'customer', 'site', 'device', etc.
    action = Column(String(100), nullable=False, index=True)  # 'read', 'write', 'delete', 'admin'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name})>"


class Role(Base):
    """Role entity - groups permissions for user roles."""

    __tablename__ = "roles"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    parent_role_id = Column(String(36), ForeignKey("roles.id"), nullable=True)  # For role hierarchy
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    parent_role = relationship("Role", remote_side=[id], backref="child_roles")

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class RolePermission(Base):
    """RolePermission entity - maps permissions to roles."""

    __tablename__ = "role_permissions"

    id = Column(String(36), primary_key=True)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = Column(String(36), ForeignKey("permissions.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    role = relationship("Role")
    permission = relationship("Permission")

    def __repr__(self) -> str:
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


class AccessControl(Base):
    """AccessControl entity - assigns roles to users for specific resources."""

    __tablename__ = "access_controls"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)  # 'customer', 'site', 'device'
    resource_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")
    role = relationship("Role")

    def __repr__(self) -> str:
        return f"<AccessControl(user_id={self.user_id}, role_id={self.role_id}, resource={self.resource_type}:{self.resource_id})>"


class ConflictResolution(Base):
    """ConflictResolution entity - tracks conflict resolution decisions."""

    __tablename__ = "conflict_resolutions"

    id = Column(String(36), primary_key=True)
    data_conflict_id = Column(String(36), ForeignKey("data_conflicts.id"), nullable=False, index=True)
    resolution_strategy = Column(String(100), nullable=False)  # 'local_wins', 'remote_wins', 'merge', 'manual'
    resolved_version = Column(String, nullable=False)  # JSON serialized resolved version
    reasoning = Column(String, nullable=True)  # Explanation of resolution decision
    resolved_by = Column(String(36), nullable=True)  # User ID who resolved
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    data_conflict = relationship("DataConflict")

    def __repr__(self) -> str:
        return f"<ConflictResolution(id={self.id}, strategy={self.resolution_strategy})>"


class AuditLogEntry(Base):
    """AuditLogEntry entity - comprehensive audit trail of all system changes."""

    __tablename__ = "audit_log_entries"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=True, index=True)  # User who performed action, null for system
    action = Column(String(100), nullable=False, index=True)  # 'create', 'update', 'delete', 'read', 'export'
    entity_type = Column(String(100), nullable=False, index=True)  # 'customer', 'site', 'device', etc.
    entity_id = Column(String(36), nullable=False, index=True)
    old_value = Column(String, nullable=True)  # JSON serialized old value
    new_value = Column(String, nullable=True)  # JSON serialized new value
    change_summary = Column(String, nullable=True)  # Human-readable summary
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String, nullable=True)
    status = Column(String(50), default="success", nullable=False)  # 'success', 'failure', 'partial'
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<AuditLogEntry(id={self.id}, action={self.action}, entity_type={self.entity_type})>"


class SLATargets(Base):
    """SLATargets entity - defines SLA targets for metrics."""

    __tablename__ = "sla_targets"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    metric_name = Column(String(255), nullable=False, index=True)  # 'availability', 'latency', 'error_rate'
    target_value = Column(Float, nullable=False)  # Target value (e.g., 99.9 for 99.9% availability)
    unit = Column(String(50), nullable=False)  # '%', 'ms', 'errors/min'
    warning_threshold = Column(Float, nullable=False)  # Alert when approaching target
    critical_threshold = Column(Float, nullable=False)  # Alert when violating target
    measurement_window = Column(Integer, nullable=False)  # Measurement window in seconds
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")

    def __repr__(self) -> str:
        return f"<SLATargets(id={self.id}, metric_name={self.metric_name}, target={self.target_value}{self.unit})>"


class SLAMetric(Base):
    """SLAMetric entity - tracks SLA compliance metrics."""

    __tablename__ = "sla_metrics"

    id = Column(String(36), primary_key=True)
    sla_target_id = Column(String(36), ForeignKey("sla_targets.id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True, index=True)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=True, index=True)
    current_value = Column(Float, nullable=False)
    compliance_status = Column(String(50), default="compliant", nullable=False, index=True)  # 'compliant', 'warning', 'critical'
    measurement_start = Column(DateTime, nullable=False)
    measurement_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    sla_target = relationship("SLATargets")
    customer = relationship("Customer")
    site = relationship("Site")

    def __repr__(self) -> str:
        return f"<SLAMetric(id={self.id}, current_value={self.current_value}, status={self.compliance_status})>"


class PerformanceMetrics(Base):
    """PerformanceMetrics entity - tracks system performance metrics."""

    __tablename__ = "performance_metrics"

    id = Column(String(36), primary_key=True)
    metric_type = Column(String(100), nullable=False, index=True)  # 'latency', 'throughput', 'error_rate', 'cache_hit_rate'
    metric_name = Column(String(255), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    component = Column(String(100), nullable=True, index=True)  # 'edge_inference', 'voice_command', 'gesture_recognition'
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=True, index=True)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    device = relationship("Device")
    site = relationship("Site")
    customer = relationship("Customer")

    def __repr__(self) -> str:
        return f"<PerformanceMetrics(id={self.id}, metric_type={self.metric_type}, value={self.value}{self.unit})>"


class DeviceCapabilities(Base):
    """DeviceCapabilities entity - tracks device capabilities and features."""

    __tablename__ = "device_capabilities"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    capability_name = Column(String(255), nullable=False, index=True)  # 'xr_support', 'ar_support', 'gpu', 'sensor_fusion'
    capability_value = Column(String, nullable=False)  # JSON serialized capability details
    is_available = Column(Boolean, default=True, nullable=False)
    last_detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    device = relationship("Device")

    def __repr__(self) -> str:
        return f"<DeviceCapabilities(id={self.id}, device_id={self.device_id}, capability={self.capability_name})>"


class InterfaceMode(Base):
    """InterfaceMode entity - defines available interface modes."""

    __tablename__ = "interface_modes"

    id = Column(String(36), primary_key=True)
    mode_name = Column(String(100), unique=True, nullable=False, index=True)  # 'xr', 'ar', 'desktop', 'mobile', 'cached'
    description = Column(String, nullable=True)
    priority = Column(Integer, default=0, nullable=False)  # Higher priority = preferred fallback
    requires_capabilities = Column(String, nullable=True)  # JSON array of required capabilities
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<InterfaceMode(id={self.id}, mode_name={self.mode_name})>"


class InterfaceModePreferences(Base):
    """InterfaceModePreferences entity - user preferences for interface modes."""

    __tablename__ = "interface_mode_preferences"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    preferred_mode = Column(String(100), nullable=False)  # 'xr', 'ar', 'desktop', 'mobile'
    fallback_chain = Column(String, nullable=False)  # JSON array of fallback modes in order
    quality_level = Column(String(50), default="high", nullable=False)  # 'ultra', 'high', 'medium', 'low'
    haptic_feedback_enabled = Column(Boolean, default=True, nullable=False)
    spatial_audio_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<InterfaceModePreferences(id={self.id}, user_id={self.user_id}, preferred_mode={self.preferred_mode})>"
