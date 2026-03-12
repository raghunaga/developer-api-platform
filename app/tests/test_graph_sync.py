"""Tests for graph database synchronization."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from app.db.graph_sync import GraphSynchronizer
from app.models.entities import Tenant, Customer, Site, Gateway, Device, User, DataStream


class TestGraphSynchronizer:
    """Tests for GraphSynchronizer class."""

    def test_synchronizer_initialization(self):
        """Test synchronizer initialization."""
        sql_session = Mock()
        graph_db = Mock()
        sync = GraphSynchronizer(sql_session, graph_db)
        assert sync.sql_session == sql_session
        assert sync.graph_db == graph_db

    def test_sync_all_data_without_graph_db(self):
        """Test sync_all_data when graph_db is not connected."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = False

        sync = GraphSynchronizer(sql_session, graph_db)
        sync.sync_all_data()
        # Should not raise an error

    def test_sync_all_data_with_graph_db(self):
        """Test sync_all_data with connected graph_db."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Mock the query results
        sql_session.query.return_value.all.return_value = []

        sync = GraphSynchronizer(sql_session, graph_db)
        sync.sync_all_data()
        graph_db.clear_graph.assert_called_once()

    def test_sync_tenants(self):
        """Test syncing tenants."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Create mock tenant
        tenant = Mock(spec=Tenant)
        tenant.id = "tenant-1"
        tenant.name = "Test Tenant"
        tenant.identifier = "test-tenant"
        tenant.status = "active"
        tenant.created_at = datetime.utcnow()

        sql_session.query.return_value.all.return_value = [tenant]

        sync = GraphSynchronizer(sql_session, graph_db)
        sync._sync_tenants()
        # Should not raise an error

    def test_sync_customers(self):
        """Test syncing customers."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Create mock customer
        customer = Mock(spec=Customer)
        customer.id = "customer-1"
        customer.tenant_id = "tenant-1"
        customer.name = "Test Customer"
        customer.identifier = "test-customer"
        customer.status = "active"
        customer.created_at = datetime.utcnow()

        sql_session.query.return_value.all.return_value = [customer]

        sync = GraphSynchronizer(sql_session, graph_db)
        sync._sync_customers()
        # Should not raise an error

    def test_sync_sites(self):
        """Test syncing sites."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Create mock site
        site = Mock(spec=Site)
        site.id = "site-1"
        site.customer_id = "customer-1"
        site.name = "Test Site"
        site.identifier = "test-site"
        site.location = "New York"
        site.created_at = datetime.utcnow()

        sql_session.query.return_value.all.return_value = [site]

        sync = GraphSynchronizer(sql_session, graph_db)
        sync._sync_sites()
        # Should not raise an error

    def test_sync_gateways(self):
        """Test syncing gateways."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Create mock gateway
        gateway = Mock(spec=Gateway)
        gateway.id = "gateway-1"
        gateway.site_id = "site-1"
        gateway.name = "Test Gateway"
        gateway.identifier = "test-gateway"
        gateway.gateway_type = "edge"
        gateway.status = "online"
        gateway.created_at = datetime.utcnow()

        sql_session.query.return_value.all.return_value = [gateway]

        sync = GraphSynchronizer(sql_session, graph_db)
        sync._sync_gateways()
        # Should not raise an error

    def test_sync_devices(self):
        """Test syncing devices."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Create mock device
        device = Mock(spec=Device)
        device.id = "device-1"
        device.gateway_id = "gateway-1"
        device.name = "Test Device"
        device.identifier = "test-device"
        device.device_type = "sensor"
        device.status = "online"
        device.created_at = datetime.utcnow()

        sql_session.query.return_value.all.return_value = [device]

        sync = GraphSynchronizer(sql_session, graph_db)
        sync._sync_devices()
        # Should not raise an error

    def test_sync_users(self):
        """Test syncing users."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Create mock user
        user = Mock(spec=User)
        user.id = "user-1"
        user.site_id = "site-1"
        user.name = "Test User"
        user.identifier = "test-user"
        user.role = "operator"
        user.created_at = datetime.utcnow()

        sql_session.query.return_value.all.return_value = [user]

        sync = GraphSynchronizer(sql_session, graph_db)
        sync._sync_users()
        # Should not raise an error

    def test_sync_data_streams(self):
        """Test syncing data streams."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Create mock data stream
        stream = Mock(spec=DataStream)
        stream.id = "stream-1"
        stream.device_id = "device-1"
        stream.name = "Temperature"
        stream.identifier = "temp-stream"
        stream.data_type = "temperature"
        stream.unit = "celsius"
        stream.created_at = datetime.utcnow()

        sql_session.query.return_value.all.return_value = [stream]

        sync = GraphSynchronizer(sql_session, graph_db)
        sync._sync_data_streams()
        # Should not raise an error

    def test_sync_entity_customer(self):
        """Test syncing a single customer entity."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Create mock customer
        customer = Mock(spec=Customer)
        customer.id = "customer-1"
        customer.tenant_id = "tenant-1"
        customer.name = "Test Customer"
        customer.identifier = "test-customer"
        customer.status = "active"
        customer.created_at = datetime.utcnow()

        sql_session.query.return_value.filter.return_value.first.return_value = customer

        sync = GraphSynchronizer(sql_session, graph_db)
        sync.sync_entity("Customer", "customer-1")
        # Should not raise an error

    def test_sync_entity_not_found(self):
        """Test syncing an entity that doesn't exist."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        sql_session.query.return_value.filter.return_value.first.return_value = None

        sync = GraphSynchronizer(sql_session, graph_db)
        sync.sync_entity("Customer", "nonexistent-id")
        # Should not raise an error


class TestGraphSynchronizerIntegration:
    """Integration tests for graph synchronizer."""

    def test_sync_hierarchy_structure(self):
        """Test that sync creates correct hierarchy structure."""
        sql_session = Mock()
        graph_db = Mock()
        graph_db.is_connected.return_value = True
        graph_db.session = Mock()

        # Create mock entities
        tenant = Mock(spec=Tenant)
        tenant.id = "tenant-1"
        tenant.name = "Test Tenant"
        tenant.identifier = "test-tenant"
        tenant.status = "active"
        tenant.created_at = datetime.utcnow()

        customer = Mock(spec=Customer)
        customer.id = "customer-1"
        customer.tenant_id = "tenant-1"
        customer.name = "Test Customer"
        customer.identifier = "test-customer"
        customer.status = "active"
        customer.created_at = datetime.utcnow()

        site = Mock(spec=Site)
        site.id = "site-1"
        site.customer_id = "customer-1"
        site.name = "Test Site"
        site.identifier = "test-site"
        site.location = "New York"
        site.created_at = datetime.utcnow()

        # Mock query results
        def mock_query(model):
            mock_query_obj = Mock()
            if model == Tenant:
                mock_query_obj.all.return_value = [tenant]
            elif model == Customer:
                mock_query_obj.all.return_value = [customer]
            elif model == Site:
                mock_query_obj.all.return_value = [site]
            else:
                mock_query_obj.all.return_value = []
            return mock_query_obj

        sql_session.query.side_effect = mock_query

        sync = GraphSynchronizer(sql_session, graph_db)
        sync.sync_all_data()
        graph_db.clear_graph.assert_called_once()
