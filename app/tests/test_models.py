"""Tests for data models."""

import pytest
from datetime import datetime
from app.models import Tenant, Customer, Site, Gateway, Device, User, DataStream


def test_tenant_creation():
    """Test creating a Tenant instance."""
    tenant = Tenant(
        id="tenant-1",
        name="Test Tenant",
        identifier="test-tenant",
        status="active",
    )
    assert tenant.id == "tenant-1"
    assert tenant.name == "Test Tenant"
    assert tenant.identifier == "test-tenant"
    assert tenant.status == "active"
    assert isinstance(tenant.created_at, datetime)


def test_customer_creation():
    """Test creating a Customer instance."""
    customer = Customer(
        id="customer-1",
        tenant_id="tenant-1",
        name="Test Customer",
        identifier="test-customer",
        status="active",
    )
    assert customer.id == "customer-1"
    assert customer.tenant_id == "tenant-1"
    assert customer.name == "Test Customer"
    assert customer.identifier == "test-customer"


def test_site_creation():
    """Test creating a Site instance."""
    site = Site(
        id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test Site",
        identifier="test-site",
        location="New York",
    )
    assert site.id == "site-1"
    assert site.customer_id == "customer-1"
    assert site.tenant_id == "tenant-1"
    assert site.name == "Test Site"
    assert site.location == "New York"


def test_gateway_creation():
    """Test creating a Gateway instance."""
    gateway = Gateway(
        id="gateway-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test Gateway",
        identifier="test-gateway",
        gateway_type="edge-device",
        status="online",
    )
    assert gateway.id == "gateway-1"
    assert gateway.site_id == "site-1"
    assert gateway.name == "Test Gateway"
    assert gateway.status == "online"


def test_device_creation():
    """Test creating a Device instance."""
    device = Device(
        id="device-1",
        gateway_id="gateway-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test Device",
        identifier="test-device",
        device_type="sensor",
        status="online",
    )
    assert device.id == "device-1"
    assert device.gateway_id == "gateway-1"
    assert device.name == "Test Device"
    assert device.device_type == "sensor"


def test_user_creation():
    """Test creating a User instance."""
    user = User(
        id="user-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test User",
        identifier="test-user",
        role="operator",
    )
    assert user.id == "user-1"
    assert user.site_id == "site-1"
    assert user.name == "Test User"
    assert user.role == "operator"


def test_datastream_creation():
    """Test creating a DataStream instance."""
    datastream = DataStream(
        id="stream-1",
        device_id="device-1",
        gateway_id="gateway-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Temperature Stream",
        identifier="temp-stream",
        data_type="temperature",
        unit="celsius",
    )
    assert datastream.id == "stream-1"
    assert datastream.device_id == "device-1"
    assert datastream.name == "Temperature Stream"
    assert datastream.data_type == "temperature"
    assert datastream.unit == "celsius"
