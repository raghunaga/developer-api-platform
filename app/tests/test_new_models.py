"""Tests for new data models and repositories."""

import pytest
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.database import Database
from app.models.entities import (
    Permission, Role, RolePermission, AccessControl,
    ConflictResolution, AuditLogEntry,
    SLATargets, SLAMetric, PerformanceMetrics,
    DeviceCapabilities, InterfaceMode, InterfaceModePreferences,
    Tenant, Customer, Site, User
)
from app.db.repositories import (
    PermissionRepository, RoleRepository, RolePermissionRepository,
    AccessControlRepository, ConflictResolutionRepository,
    AuditLogRepository, SLATargetsRepository, SLAMetricRepository,
    PerformanceMetricsRepository, DeviceCapabilitiesRepository,
    InterfaceModeRepository, InterfaceModePreferencesRepository
)


@pytest.fixture
def db_session():
    """Create a test database session."""
    db = Database(db_url="sqlite:///:memory:")
    db.create_tables()
    session = db.get_session()
    yield session
    session.close()


@pytest.fixture
def tenant_and_customer(db_session):
    """Create test tenant and customer."""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Test Tenant",
        identifier="test-tenant",
        status="active"
    )
    db_session.add(tenant)
    db_session.flush()
    
    customer = Customer(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        name="Test Customer",
        identifier="test-customer",
        status="active"
    )
    db_session.add(customer)
    db_session.commit()
    
    return tenant, customer


class TestPermissionModel:
    """Test Permission model."""

    def test_create_permission(self, db_session):
        """Test creating a permission."""
        permission = Permission(
            id=str(uuid.uuid4()),
            name="customer:read",
            description="Read customer data",
            resource="customer",
            action="read"
        )
        db_session.add(permission)
        db_session.commit()
        
        retrieved = db_session.query(Permission).filter_by(name="customer:read").first()
        assert retrieved is not None
        assert retrieved.resource == "customer"
        assert retrieved.action == "read"


class TestRoleModel:
    """Test Role model."""

    def test_create_role(self, db_session, tenant_and_customer):
        """Test creating a role."""
        tenant, _ = tenant_and_customer
        
        role = Role(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            name="admin",
            description="Administrator role"
        )
        db_session.add(role)
        db_session.commit()
        
        retrieved = db_session.query(Role).filter_by(name="admin").first()
        assert retrieved is not None
        assert retrieved.tenant_id == tenant.id


class TestAccessControlModel:
    """Test AccessControl model."""

    def test_create_access_control(self, db_session, tenant_and_customer):
        """Test creating access control."""
        tenant, customer = tenant_and_customer
        
        site = Site(
            id=str(uuid.uuid4()),
            customer_id=customer.id,
            tenant_id=tenant.id,
            name="Test Site",
            identifier="test-site"
        )
        db_session.add(site)
        db_session.flush()
        
        user = User(
            id=str(uuid.uuid4()),
            site_id=site.id,
            customer_id=customer.id,
            tenant_id=tenant.id,
            name="Test User",
            identifier="test-user",
            role="operator"
        )
        db_session.add(user)
        db_session.flush()
        
        role = Role(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            name="operator",
            description="Operator role"
        )
        db_session.add(role)
        db_session.flush()
        
        access_control = AccessControl(
            id=str(uuid.uuid4()),
            user_id=user.id,
            role_id=role.id,
            resource_type="site",
            resource_id=site.id
        )
        db_session.add(access_control)
        db_session.commit()
        
        retrieved = db_session.query(AccessControl).filter_by(user_id=user.id).first()
        assert retrieved is not None
        assert retrieved.resource_type == "site"


class TestAuditLogModel:
    """Test AuditLogEntry model."""

    def test_create_audit_log(self, db_session, tenant_and_customer):
        """Test creating audit log entry."""
        tenant, customer = tenant_and_customer
        
        log = AuditLogEntry(
            id=str(uuid.uuid4()),
            user_id=None,
            action="create",
            entity_type="customer",
            entity_id=customer.id,
            change_summary="Created new customer",
            status="success"
        )
        db_session.add(log)
        db_session.commit()
        
        retrieved = db_session.query(AuditLogEntry).filter_by(entity_id=customer.id).first()
        assert retrieved is not None
        assert retrieved.action == "create"
        assert retrieved.status == "success"


class TestSLATargetsModel:
    """Test SLATargets model."""

    def test_create_sla_target(self, db_session, tenant_and_customer):
        """Test creating SLA target."""
        tenant, _ = tenant_and_customer
        
        target = SLATargets(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            metric_name="availability",
            target_value=99.9,
            unit="%",
            warning_threshold=99.5,
            critical_threshold=99.0,
            measurement_window=3600
        )
        db_session.add(target)
        db_session.commit()
        
        retrieved = db_session.query(SLATargets).filter_by(metric_name="availability").first()
        assert retrieved is not None
        assert retrieved.target_value == 99.9


class TestPerformanceMetricsModel:
    """Test PerformanceMetrics model."""

    def test_create_performance_metric(self, db_session, tenant_and_customer):
        """Test creating performance metric."""
        tenant, customer = tenant_and_customer
        
        metric = PerformanceMetrics(
            id=str(uuid.uuid4()),
            metric_type="latency",
            metric_name="edge_inference_latency",
            value=45.5,
            unit="ms",
            component="edge_inference",
            customer_id=customer.id
        )
        db_session.add(metric)
        db_session.commit()
        
        retrieved = db_session.query(PerformanceMetrics).filter_by(metric_type="latency").first()
        assert retrieved is not None
        assert retrieved.value == 45.5


class TestDeviceCapabilitiesModel:
    """Test DeviceCapabilities model."""

    def test_create_device_capability(self, db_session, tenant_and_customer):
        """Test creating device capability."""
        from app.models.entities import Gateway, Device
        
        tenant, customer = tenant_and_customer
        
        site = Site(
            id=str(uuid.uuid4()),
            customer_id=customer.id,
            tenant_id=tenant.id,
            name="Test Site",
            identifier="test-site"
        )
        db_session.add(site)
        db_session.flush()
        
        gateway = Gateway(
            id=str(uuid.uuid4()),
            site_id=site.id,
            customer_id=customer.id,
            tenant_id=tenant.id,
            name="Test Gateway",
            identifier="test-gateway",
            gateway_type="EdgeGateway"
        )
        db_session.add(gateway)
        db_session.flush()
        
        device = Device(
            id=str(uuid.uuid4()),
            gateway_id=gateway.id,
            site_id=site.id,
            customer_id=customer.id,
            tenant_id=tenant.id,
            name="Test Device",
            identifier="test-device",
            device_type="Sensor"
        )
        db_session.add(device)
        db_session.flush()
        
        capability = DeviceCapabilities(
            id=str(uuid.uuid4()),
            device_id=device.id,
            capability_name="xr_support",
            capability_value='{"enabled": true}',
            is_available=True
        )
        db_session.add(capability)
        db_session.commit()
        
        retrieved = db_session.query(DeviceCapabilities).filter_by(device_id=device.id).first()
        assert retrieved is not None
        assert retrieved.capability_name == "xr_support"


class TestInterfaceModeModel:
    """Test InterfaceMode model."""

    def test_create_interface_mode(self, db_session):
        """Test creating interface mode."""
        mode = InterfaceMode(
            id=str(uuid.uuid4()),
            mode_name="xr",
            description="Holographic XR interface",
            priority=5
        )
        db_session.add(mode)
        db_session.commit()
        
        retrieved = db_session.query(InterfaceMode).filter_by(mode_name="xr").first()
        assert retrieved is not None
        assert retrieved.priority == 5


class TestPermissionRepository:
    """Test PermissionRepository."""

    def test_get_by_resource_action(self, db_session):
        """Test getting permissions by resource and action."""
        repo = PermissionRepository(db_session)
        
        permission = repo.create(
            id=str(uuid.uuid4()),
            name="customer:read",
            resource="customer",
            action="read"
        )
        
        results = repo.get_by_resource_action("customer", "read")
        assert len(results) > 0
        assert results[0].name == "customer:read"


class TestRoleRepository:
    """Test RoleRepository."""

    def test_get_by_tenant(self, db_session, tenant_and_customer):
        """Test getting roles by tenant."""
        tenant, _ = tenant_and_customer
        repo = RoleRepository(db_session)
        
        repo.create(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            name="admin",
            description="Admin role"
        )
        
        results = repo.get_by_tenant(tenant.id)
        assert len(results) > 0
        assert results[0].name == "admin"


class TestAuditLogRepository:
    """Test AuditLogRepository."""

    def test_get_by_action(self, db_session, tenant_and_customer):
        """Test getting audit logs by action."""
        tenant, customer = tenant_and_customer
        repo = AuditLogRepository(db_session)
        
        repo.create(
            id=str(uuid.uuid4()),
            action="create",
            entity_type="customer",
            entity_id=customer.id,
            status="success"
        )
        
        results = repo.get_by_action("create")
        assert len(results) > 0
        assert results[0].action == "create"


class TestInterfaceModeRepository:
    """Test InterfaceModeRepository."""

    def test_get_all_ordered(self, db_session):
        """Test getting all interface modes ordered by priority."""
        repo = InterfaceModeRepository(db_session)
        
        repo.create(id=str(uuid.uuid4()), mode_name="xr", priority=5)
        repo.create(id=str(uuid.uuid4()), mode_name="ar", priority=4)
        repo.create(id=str(uuid.uuid4()), mode_name="desktop", priority=3)
        
        results = repo.get_all_ordered()
        assert len(results) >= 3
        assert results[0].priority >= results[1].priority
