"""Integration tests for Phase 1 implementation."""

import pytest
from app.db.database import Database
from app.services.mock_data_generator import MockDataGenerator
from app.services.database_seeder import DatabaseSeeder


class TestPhase1Integration:
    """Integration tests for Phase 1 tasks."""

    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        db = Database(db_url="sqlite:///:memory:")
        db.create_tables()
        session = db.get_session()
        yield session
        session.close()

    def test_mock_data_generation(self):
        """Test mock data generation for both customers."""
        generator = MockDataGenerator()
        data = generator.generate_complete_dataset()
        
        # Verify structure
        assert "tenants" in data
        assert "customers" in data
        assert "sites" in data
        assert "gateways" in data
        assert "devices" in data
        assert "users" in data
        assert "data_streams" in data
        
        # Verify counts
        assert len(data["tenants"]) == 1
        assert len(data["customers"]) == 2
        assert len(data["sites"]) == 10
        assert len(data["gateways"]) == 30
        assert len(data["devices"]) == 300
        assert len(data["users"]) == 50
        assert len(data["data_streams"]) == 900

    def test_database_seeding(self, db_session):
        """Test database seeding with mock data."""
        seeder = DatabaseSeeder(db_session)
        counts = seeder.seed_all()
        
        # Verify seeding counts
        assert counts["tenants"] == 1
        assert counts["customers"] == 2
        assert counts["sites"] == 10
        assert counts["gateways"] == 30
        assert counts["devices"] == 300
        assert counts["users"] == 50
        assert counts["data_streams"] == 900

    def test_database_verification(self, db_session):
        """Test database verification after seeding."""
        seeder = DatabaseSeeder(db_session)
        seeder.seed_all()
        
        verification = seeder.verify_seeding()
        
        # Verify expected counts
        assert verification["tenants"] == 1
        assert verification["customers"] == 2
        assert verification["sites"] == 10
        assert verification["gateways"] == 30
        assert verification["devices"] == 300
        assert verification["users"] == 50
        assert verification["data_streams"] == 900

    def test_customer_specific_seeding(self, db_session):
        """Test seeding specific customer data."""
        seeder = DatabaseSeeder(db_session)
        counts = seeder.seed_customer("verizon")
        
        # Verify Verizon customer seeding
        assert counts["customers"] >= 1
        assert counts["sites"] >= 5
        assert counts["gateways"] >= 15
        assert counts["devices"] >= 150
        assert counts["users"] >= 5

    def test_database_reset(self, db_session):
        """Test database reset functionality."""
        seeder = DatabaseSeeder(db_session)
        
        # Seed data
        seeder.seed_all()
        verification_before = seeder.verify_seeding()
        assert verification_before["devices"] == 300
        
        # Reset database
        seeder.reset_database()
        verification_after = seeder.verify_seeding()
        assert verification_after["devices"] == 0

    def test_rbac_models(self, db_session):
        """Test RBAC models and repositories."""
        from app.models.entities import Permission, Role, AccessControl, Tenant, Customer, Site, User
        from app.db.repositories import PermissionRepository, RoleRepository, AccessControlRepository
        
        # Create test data
        tenant = Tenant(id="t1", name="Test", identifier="test", status="active")
        db_session.add(tenant)
        db_session.flush()
        
        customer = Customer(id="c1", tenant_id="t1", name="Test", identifier="test", status="active")
        db_session.add(customer)
        db_session.flush()
        
        site = Site(id="s1", customer_id="c1", tenant_id="t1", name="Test", identifier="test")
        db_session.add(site)
        db_session.flush()
        
        user = User(id="u1", site_id="s1", customer_id="c1", tenant_id="t1", name="Test", identifier="test", role="operator")
        db_session.add(user)
        db_session.flush()
        
        # Test Permission repository
        perm_repo = PermissionRepository(db_session)
        perm = perm_repo.create(id="p1", name="customer:read", resource="customer", action="read")
        assert perm.name == "customer:read"
        
        # Test Role repository
        role_repo = RoleRepository(db_session)
        role = role_repo.create(id="r1", tenant_id="t1", name="admin", description="Admin")
        assert role.name == "admin"
        
        # Test AccessControl repository
        ac_repo = AccessControlRepository(db_session)
        ac = ac_repo.create(id="ac1", user_id="u1", role_id="r1", resource_type="site", resource_id="s1")
        assert ac.resource_type == "site"

    def test_audit_logging(self, db_session):
        """Test audit logging models and repositories."""
        from app.models.entities import AuditLogEntry, Tenant, Customer
        from app.db.repositories import AuditLogRepository
        
        # Create test data
        tenant = Tenant(id="t1", name="Test", identifier="test", status="active")
        db_session.add(tenant)
        db_session.flush()
        
        customer = Customer(id="c1", tenant_id="t1", name="Test", identifier="test", status="active")
        db_session.add(customer)
        db_session.flush()
        
        # Test AuditLog repository
        audit_repo = AuditLogRepository(db_session)
        log = audit_repo.create(
            id="l1",
            action="create",
            entity_type="customer",
            entity_id="c1",
            status="success"
        )
        assert log.action == "create"
        
        # Test query methods
        logs = audit_repo.get_by_action("create")
        assert len(logs) > 0

    def test_sla_monitoring(self, db_session):
        """Test SLA monitoring models and repositories."""
        from app.models.entities import SLATargets, SLAMetric, Tenant, Customer
        from app.db.repositories import SLATargetsRepository, SLAMetricRepository
        
        # Create test data
        tenant = Tenant(id="t1", name="Test", identifier="test", status="active")
        db_session.add(tenant)
        db_session.flush()
        
        customer = Customer(id="c1", tenant_id="t1", name="Test", identifier="test", status="active")
        db_session.add(customer)
        db_session.flush()
        
        # Test SLATargets repository
        sla_repo = SLATargetsRepository(db_session)
        target = sla_repo.create(
            id="sla1",
            tenant_id="t1",
            metric_name="availability",
            target_value=99.9,
            unit="%",
            warning_threshold=99.5,
            critical_threshold=99.0,
            measurement_window=3600
        )
        assert target.metric_name == "availability"
        
        # Test SLAMetric repository
        metric_repo = SLAMetricRepository(db_session)
        metric = metric_repo.create(
            id="m1",
            sla_target_id="sla1",
            customer_id="c1",
            current_value=99.95,
            compliance_status="compliant",
            measurement_start=db_session.query(SLATargets).first().created_at,
            measurement_end=db_session.query(SLATargets).first().created_at
        )
        assert metric.compliance_status == "compliant"

    def test_device_capabilities(self, db_session):
        """Test device capabilities models and repositories."""
        from app.models.entities import (
            DeviceCapabilities, InterfaceMode, InterfaceModePreferences,
            Tenant, Customer, Site, Gateway, Device, User
        )
        from app.db.repositories import (
            DeviceCapabilitiesRepository, InterfaceModeRepository,
            InterfaceModePreferencesRepository
        )
        
        # Create test data
        tenant = Tenant(id="t1", name="Test", identifier="test", status="active")
        db_session.add(tenant)
        db_session.flush()
        
        customer = Customer(id="c1", tenant_id="t1", name="Test", identifier="test", status="active")
        db_session.add(customer)
        db_session.flush()
        
        site = Site(id="s1", customer_id="c1", tenant_id="t1", name="Test", identifier="test")
        db_session.add(site)
        db_session.flush()
        
        gateway = Gateway(id="g1", site_id="s1", customer_id="c1", tenant_id="t1", name="Test", identifier="test", gateway_type="EdgeGateway")
        db_session.add(gateway)
        db_session.flush()
        
        device = Device(id="d1", gateway_id="g1", site_id="s1", customer_id="c1", tenant_id="t1", name="Test", identifier="test", device_type="Sensor")
        db_session.add(device)
        db_session.flush()
        
        user = User(id="u1", site_id="s1", customer_id="c1", tenant_id="t1", name="Test", identifier="test", role="operator")
        db_session.add(user)
        db_session.flush()
        
        # Test DeviceCapabilities repository
        cap_repo = DeviceCapabilitiesRepository(db_session)
        capability = cap_repo.create(
            id="cap1",
            device_id="d1",
            capability_name="xr_support",
            capability_value='{"enabled": true}',
            is_available=True
        )
        assert capability.capability_name == "xr_support"
        
        # Test InterfaceMode repository
        mode_repo = InterfaceModeRepository(db_session)
        mode = mode_repo.create(id="m1", mode_name="xr", description="XR Mode", priority=5)
        assert mode.mode_name == "xr"
        
        # Test InterfaceModePreferences repository
        pref_repo = InterfaceModePreferencesRepository(db_session)
        prefs = pref_repo.create(
            id="p1",
            user_id="u1",
            preferred_mode="xr",
            fallback_chain='["ar", "desktop", "mobile"]',
            quality_level="high"
        )
        assert prefs.preferred_mode == "xr"

    def test_performance_metrics(self, db_session):
        """Test performance metrics models and repositories."""
        from app.models.entities import PerformanceMetrics, Tenant, Customer
        from app.db.repositories import PerformanceMetricsRepository
        
        # Create test data
        tenant = Tenant(id="t1", name="Test", identifier="test", status="active")
        db_session.add(tenant)
        db_session.flush()
        
        customer = Customer(id="c1", tenant_id="t1", name="Test", identifier="test", status="active")
        db_session.add(customer)
        db_session.flush()
        
        # Test PerformanceMetrics repository
        metrics_repo = PerformanceMetricsRepository(db_session)
        metric = metrics_repo.create(
            id="pm1",
            metric_type="latency",
            metric_name="edge_inference_latency",
            value=45.5,
            unit="ms",
            component="edge_inference",
            customer_id="c1"
        )
        assert metric.metric_type == "latency"
        
        # Test query methods
        latency_metrics = metrics_repo.get_by_type("latency")
        assert len(latency_metrics) > 0

    def test_complete_workflow(self, db_session):
        """Test complete workflow from seeding to verification."""
        seeder = DatabaseSeeder(db_session)
        
        # Step 1: Seed all data
        seed_counts = seeder.seed_all()
        assert seed_counts["devices"] == 300
        
        # Step 2: Verify seeding
        verification = seeder.verify_seeding()
        assert verification["devices"] == 300
        
        # Step 3: Query specific customer
        from app.db.repositories import CustomerRepository
        customer_repo = CustomerRepository(db_session)
        customers = customer_repo.get_all()
        assert len(customers) == 2
        
        # Step 4: Verify customer data
        verizon = [c for c in customers if "verizon" in c.identifier.lower()][0]
        assert verizon.name == "Verizon"
        
        # Step 5: Verify sites for customer
        sites = customer_repo.get_children(verizon.id)
        assert len(sites) == 5
