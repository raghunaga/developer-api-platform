"""Mock data generator for Verizon and AT&T customers with realistic data."""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from faker import Faker

from app.models.entities import (
    Tenant, Customer, Site, Gateway, Device, User, DataStream,
    Permission, Role, AccessControl,
    AuditLogEntry, SLATargets, SLAMetric, PerformanceMetrics,
    DeviceCapabilities, InterfaceMode, InterfaceModePreferences
)

fake = Faker()


class MockDataGenerator:
    """Generate realistic mock data for testing and development."""

    def __init__(self):
        self.tenant_id = str(uuid.uuid4())
        self.customers = {}
        self.sites = {}
        self.gateways = {}
        self.devices = {}
        self.users = {}
        self.data_streams = {}

    def generate_tenant(self) -> Tenant:
        """Generate a tenant."""
        return Tenant(
            id=self.tenant_id,
            name="Belden Horizon",
            identifier="belden-horizon",
            status="active"
        )

    def generate_customers(self) -> List[Customer]:
        """Generate Verizon and AT&T customers."""
        customers = []
        
        # Verizon
        verizon = Customer(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            name="Verizon",
            identifier="verizon-001",
            status="active"
        )
        self.customers["verizon"] = verizon
        customers.append(verizon)
        
        # AT&T
        att = Customer(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            name="AT&T",
            identifier="att-001",
            status="active"
        )
        self.customers["att"] = att
        customers.append(att)
        
        return customers

    def generate_sites(self, customer_key: str, customer_id: str) -> List[Site]:
        """Generate 5 sites for a customer."""
        site_names = {
            "verizon": ["New York", "Los Angeles", "Chicago", "Dallas", "Seattle"],
            "att": ["Boston", "San Francisco", "Houston", "Miami", "Denver"]
        }
        
        sites = []
        for site_name in site_names.get(customer_key, []):
            site = Site(
                id=str(uuid.uuid4()),
                customer_id=customer_id,
                tenant_id=self.tenant_id,
                name=site_name,
                identifier=f"{customer_key}-site-{site_name.lower().replace(' ', '-')}",
                location=site_name
            )
            sites.append(site)
            self.sites[f"{customer_key}-{site_name}"] = site
        
        return sites

    def generate_gateways(self, site_id: str, customer_id: str, site_name: str, customer_key: str) -> List[Gateway]:
        """Generate 3 gateways for a site."""
        gateways = []
        for i in range(3):
            gateway = Gateway(
                id=str(uuid.uuid4()),
                site_id=site_id,
                customer_id=customer_id,
                tenant_id=self.tenant_id,
                name=f"{site_name} Gateway {i+1}",
                identifier=f"{customer_key}-gw-{site_name.lower().replace(' ', '-')}-{i+1}",
                gateway_type="EdgeGateway",
                status=fake.random_element(["online", "online", "online", "offline"]),
                last_update=datetime.utcnow() - timedelta(minutes=fake.random_int(0, 60))
            )
            gateways.append(gateway)
            self.gateways[gateway.id] = gateway
        
        return gateways

    def generate_devices(self, gateway_id: str, site_id: str, customer_id: str, gateway_num: int) -> List[Device]:
        """Generate 10 devices for a gateway."""
        devices = []
        for i in range(10):
            device = Device(
                id=str(uuid.uuid4()),
                gateway_id=gateway_id,
                site_id=site_id,
                customer_id=customer_id,
                tenant_id=self.tenant_id,
                name=f"Device-{gateway_num}-{i+1}",
                identifier=f"device-{gateway_num}-{i+1}",
                device_type=fake.random_element(["Sensor", "PLC", "Controller", "Monitor"]),
                status=fake.random_element(["online", "online", "online", "offline", "error"]),
                last_update=datetime.utcnow() - timedelta(minutes=fake.random_int(0, 120))
            )
            devices.append(device)
            self.devices[device.id] = device
        
        return devices

    def generate_users(self, site_id: str, customer_id: str, site_name: str) -> List[User]:
        """Generate 5 users for a site."""
        users = []
        roles = ["operator", "engineer", "manager", "admin", "viewer"]
        
        for i, role in enumerate(roles):
            user = User(
                id=str(uuid.uuid4()),
                site_id=site_id,
                customer_id=customer_id,
                tenant_id=self.tenant_id,
                name=fake.name(),
                identifier=f"{site_name.lower().replace(' ', '-')}-{role}-{i+1}",
                role=role
            )
            users.append(user)
            self.users[user.id] = user
        
        return users

    def generate_data_streams(self, device_id: str, gateway_id: str, site_id: str, customer_id: str) -> List[DataStream]:
        """Generate 3 data streams for a device."""
        stream_types = [
            ("temperature", "celsius"),
            ("pressure", "psi"),
            ("vibration", "mm/s")
        ]
        
        streams = []
        for stream_type, unit in stream_types:
            stream = DataStream(
                id=str(uuid.uuid4()),
                device_id=device_id,
                gateway_id=gateway_id,
                site_id=site_id,
                customer_id=customer_id,
                tenant_id=self.tenant_id,
                name=f"{stream_type.capitalize()} Stream",
                identifier=f"{device_id}-{stream_type}",
                data_type=stream_type,
                unit=unit
            )
            streams.append(stream)
            self.data_streams[stream.id] = stream
        
        return streams

    def generate_permissions(self) -> List[Permission]:
        """Generate standard permissions."""
        permissions = []
        resources = ["customer", "site", "device", "user", "data_stream"]
        actions = ["read", "write", "delete", "admin"]
        
        for resource in resources:
            for action in actions:
                permission = Permission(
                    id=str(uuid.uuid4()),
                    name=f"{resource}:{action}",
                    description=f"Permission to {action} {resource}s",
                    resource=resource,
                    action=action
                )
                permissions.append(permission)
        
        return permissions

    def generate_roles(self) -> List[Role]:
        """Generate standard roles."""
        roles = []
        role_names = ["admin", "manager", "engineer", "operator", "viewer"]
        
        for role_name in role_names:
            role = Role(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                name=role_name,
                description=f"{role_name.capitalize()} role"
            )
            roles.append(role)
        
        return roles

    def generate_audit_logs(self, user_id: str, entity_type: str, entity_id: str, count: int = 10) -> List[AuditLogEntry]:
        """Generate audit log entries."""
        logs = []
        actions = ["create", "update", "delete", "read", "export"]
        
        for i in range(count):
            log = AuditLogEntry(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action=fake.random_element(actions),
                entity_type=entity_type,
                entity_id=entity_id,
                change_summary=f"Change {i+1}",
                ip_address=fake.ipv4(),
                status=fake.random_element(["success", "success", "success", "failure"]),
                created_at=datetime.utcnow() - timedelta(hours=fake.random_int(0, 720))
            )
            logs.append(log)
        
        return logs

    def generate_sla_targets(self) -> List[SLATargets]:
        """Generate SLA targets."""
        targets = []
        metrics = [
            ("availability", 99.9, "%"),
            ("latency", 100, "ms"),
            ("error_rate", 0.1, "%")
        ]
        
        for metric_name, target_value, unit in metrics:
            target = SLATargets(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                metric_name=metric_name,
                target_value=target_value,
                unit=unit,
                warning_threshold=target_value * 0.95,
                critical_threshold=target_value * 0.90,
                measurement_window=3600
            )
            targets.append(target)
        
        return targets

    def generate_performance_metrics(self, device_id: str, site_id: str, customer_id: str, count: int = 20) -> List[PerformanceMetrics]:
        """Generate performance metrics."""
        metrics = []
        metric_types = [
            ("latency", "edge_inference", "ms"),
            ("latency", "voice_command", "ms"),
            ("latency", "gesture_recognition", "ms"),
            ("throughput", "data_stream", "events/sec"),
            ("error_rate", "inference", "%"),
            ("cache_hit_rate", "cache", "%")
        ]
        
        for _ in range(count):
            metric_type, component, unit = fake.random_element(metric_types)
            metric = PerformanceMetrics(
                id=str(uuid.uuid4()),
                metric_type=metric_type,
                metric_name=f"{component}_{metric_type}",
                value=fake.random_int(10, 500),
                unit=unit,
                component=component,
                device_id=device_id,
                site_id=site_id,
                customer_id=customer_id,
                created_at=datetime.utcnow() - timedelta(minutes=fake.random_int(0, 1440))
            )
            metrics.append(metric)
        
        return metrics

    def generate_device_capabilities(self, device_id: str) -> List[DeviceCapabilities]:
        """Generate device capabilities."""
        capabilities = []
        capability_names = ["xr_support", "ar_support", "gpu", "sensor_fusion", "edge_inference"]
        
        for capability_name in capability_names:
            capability = DeviceCapabilities(
                id=str(uuid.uuid4()),
                device_id=device_id,
                capability_name=capability_name,
                capability_value=json.dumps({"enabled": True, "version": "1.0"}),
                is_available=fake.boolean()
            )
            capabilities.append(capability)
        
        return capabilities

    def generate_interface_modes(self) -> List[InterfaceMode]:
        """Generate interface modes."""
        modes = []
        mode_configs = [
            ("xr", "Holographic XR interface", 5),
            ("ar", "Augmented Reality overlay", 4),
            ("desktop", "Desktop 2D interface", 3),
            ("mobile", "Mobile simplified interface", 2),
            ("cached", "Cached offline mode", 1)
        ]
        
        for mode_name, description, priority in mode_configs:
            mode = InterfaceMode(
                id=str(uuid.uuid4()),
                mode_name=mode_name,
                description=description,
                priority=priority
            )
            modes.append(mode)
        
        return modes

    def generate_complete_dataset(self) -> Dict[str, List[Any]]:
        """Generate complete dataset for both customers."""
        data = {
            "tenants": [],
            "customers": [],
            "sites": [],
            "gateways": [],
            "devices": [],
            "users": [],
            "data_streams": [],
            "permissions": [],
            "roles": [],
            "audit_logs": [],
            "sla_targets": [],
            "performance_metrics": [],
            "device_capabilities": [],
            "interface_modes": []
        }
        
        # Generate tenant
        tenant = self.generate_tenant()
        data["tenants"].append(tenant)
        
        # Generate customers
        customers = self.generate_customers()
        data["customers"].extend(customers)
        
        # Generate sites, gateways, devices, users, data streams for each customer
        for customer_key, customer in [("verizon", customers[0]), ("att", customers[1])]:
            sites = self.generate_sites(customer_key, customer.id)
            data["sites"].extend(sites)
            
            for site_idx, site in enumerate(sites):
                # Generate users for site
                users = self.generate_users(site.id, customer.id, site.name)
                data["users"].extend(users)
                
                # Generate gateways for site
                gateways = self.generate_gateways(site.id, customer.id, site.name, customer_key)
                data["gateways"].extend(gateways)
                
                for gw_idx, gateway in enumerate(gateways):
                    # Generate devices for gateway
                    devices = self.generate_devices(gateway.id, site.id, customer.id, site_idx * 3 + gw_idx + 1)
                    data["devices"].extend(devices)
                    
                    for device in devices:
                        # Generate data streams for device
                        streams = self.generate_data_streams(device.id, gateway.id, site.id, customer.id)
                        data["data_streams"].extend(streams)
                        
                        # Generate device capabilities
                        capabilities = self.generate_device_capabilities(device.id)
                        data["device_capabilities"].extend(capabilities)
                        
                        # Generate performance metrics
                        metrics = self.generate_performance_metrics(device.id, site.id, customer.id)
                        data["performance_metrics"].extend(metrics)
                    
                    # Generate audit logs for gateway
                    if users:
                        logs = self.generate_audit_logs(users[0].id, "gateway", gateway.id, count=5)
                        data["audit_logs"].extend(logs)
        
        # Generate permissions, roles, SLA targets, interface modes (global)
        data["permissions"].extend(self.generate_permissions())
        data["roles"].extend(self.generate_roles())
        data["sla_targets"].extend(self.generate_sla_targets())
        data["interface_modes"].extend(self.generate_interface_modes())
        
        return data
