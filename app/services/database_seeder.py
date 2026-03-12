"""Database seeding and bulk insert operations."""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import insert

from app.models.entities import (
    Tenant, Customer, Site, Gateway, Device, User, DataStream,
    Permission, Role, RolePermission, AccessControl,
    AuditLogEntry, SLATargets, SLAMetric, PerformanceMetrics,
    DeviceCapabilities, InterfaceMode, InterfaceModePreferences
)
from app.services.mock_data_generator import MockDataGenerator

logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """Seed database with mock data."""

    def __init__(self, session: Session):
        self.session = session
        self.generator = MockDataGenerator()

    def seed_all(self) -> Dict[str, int]:
        """Seed database with complete mock dataset."""
        logger.info("Starting database seeding...")
        
        data = self.generator.generate_complete_dataset()
        counts = {}
        
        try:
            # Seed each entity type
            counts["tenants"] = self._bulk_insert(Tenant, data["tenants"])
            counts["customers"] = self._bulk_insert(Customer, data["customers"])
            counts["sites"] = self._bulk_insert(Site, data["sites"])
            counts["gateways"] = self._bulk_insert(Gateway, data["gateways"])
            counts["devices"] = self._bulk_insert(Device, data["devices"])
            counts["users"] = self._bulk_insert(User, data["users"])
            counts["data_streams"] = self._bulk_insert(DataStream, data["data_streams"])
            counts["permissions"] = self._bulk_insert(Permission, data["permissions"])
            counts["roles"] = self._bulk_insert(Role, data["roles"])
            counts["audit_logs"] = self._bulk_insert(AuditLogEntry, data["audit_logs"])
            counts["sla_targets"] = self._bulk_insert(SLATargets, data["sla_targets"])
            counts["performance_metrics"] = self._bulk_insert(PerformanceMetrics, data["performance_metrics"])
            counts["device_capabilities"] = self._bulk_insert(DeviceCapabilities, data["device_capabilities"])
            counts["interface_modes"] = self._bulk_insert(InterfaceMode, data["interface_modes"])
            
            self.session.commit()
            logger.info(f"Database seeding completed successfully. Counts: {counts}")
            return counts
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error during database seeding: {e}")
            raise

    def seed_customer(self, customer_key: str) -> Dict[str, int]:
        """Seed database with data for a specific customer (verizon or att)."""
        logger.info(f"Starting database seeding for customer: {customer_key}")
        
        data = self.generator.generate_complete_dataset()
        counts = {}
        
        try:
            # Get customer data
            customers = [c for c in data["customers"] if customer_key in c.identifier.lower()]
            if not customers:
                raise ValueError(f"Customer {customer_key} not found")
            
            customer = customers[0]
            
            # Seed customer and related data
            counts["customers"] = self._bulk_insert(Customer, [customer])
            
            # Filter and seed related entities
            customer_sites = [s for s in data["sites"] if s.customer_id == customer.id]
            counts["sites"] = self._bulk_insert(Site, customer_sites)
            
            site_ids = [s.id for s in customer_sites]
            customer_gateways = [g for g in data["gateways"] if g.site_id in site_ids]
            counts["gateways"] = self._bulk_insert(Gateway, customer_gateways)
            
            gateway_ids = [g.id for g in customer_gateways]
            customer_devices = [d for d in data["devices"] if d.gateway_id in gateway_ids]
            counts["devices"] = self._bulk_insert(Device, customer_devices)
            
            device_ids = [d.id for d in customer_devices]
            customer_streams = [s for s in data["data_streams"] if s.device_id in device_ids]
            counts["data_streams"] = self._bulk_insert(DataStream, customer_streams)
            
            customer_users = [u for u in data["users"] if u.site_id in site_ids]
            counts["users"] = self._bulk_insert(User, customer_users)
            
            # Seed global data (permissions, roles, etc.)
            counts["permissions"] = self._bulk_insert(Permission, data["permissions"])
            counts["roles"] = self._bulk_insert(Role, data["roles"])
            counts["sla_targets"] = self._bulk_insert(SLATargets, data["sla_targets"])
            counts["interface_modes"] = self._bulk_insert(InterfaceMode, data["interface_modes"])
            
            self.session.commit()
            logger.info(f"Customer {customer_key} seeding completed. Counts: {counts}")
            return counts
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error during customer seeding: {e}")
            raise

    def _bulk_insert(self, model_class, entities: List[Any]) -> int:
        """Bulk insert entities into database."""
        if not entities:
            return 0
        
        try:
            # Convert ORM objects to dictionaries for bulk insert
            values = []
            for entity in entities:
                if hasattr(entity, '__dict__'):
                    # Remove SQLAlchemy internal attributes
                    entity_dict = {k: v for k, v in entity.__dict__.items() if not k.startswith('_')}
                    values.append(entity_dict)
                else:
                    values.append(entity)
            
            if values:
                stmt = insert(model_class).values(values)
                result = self.session.execute(stmt)
                logger.debug(f"Inserted {result.rowcount} {model_class.__name__} entities")
                return result.rowcount
            return 0
        except Exception as e:
            logger.error(f"Error bulk inserting {model_class.__name__}: {e}")
            raise

    def reset_database(self) -> None:
        """Reset database by deleting all data."""
        logger.info("Resetting database...")
        
        try:
            # Delete in reverse order of dependencies
            self.session.query(InterfaceModePreferences).delete()
            self.session.query(InterfaceMode).delete()
            self.session.query(DeviceCapabilities).delete()
            self.session.query(PerformanceMetrics).delete()
            self.session.query(SLAMetric).delete()
            self.session.query(SLATargets).delete()
            self.session.query(AuditLogEntry).delete()
            self.session.query(AccessControl).delete()
            self.session.query(RolePermission).delete()
            self.session.query(Role).delete()
            self.session.query(Permission).delete()
            self.session.query(DataStream).delete()
            self.session.query(Device).delete()
            self.session.query(Gateway).delete()
            self.session.query(User).delete()
            self.session.query(Site).delete()
            self.session.query(Customer).delete()
            self.session.query(Tenant).delete()
            
            self.session.commit()
            logger.info("Database reset completed")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error during database reset: {e}")
            raise

    def verify_seeding(self) -> Dict[str, int]:
        """Verify seeding by counting entities."""
        counts = {
            "tenants": self.session.query(Tenant).count(),
            "customers": self.session.query(Customer).count(),
            "sites": self.session.query(Site).count(),
            "gateways": self.session.query(Gateway).count(),
            "devices": self.session.query(Device).count(),
            "users": self.session.query(User).count(),
            "data_streams": self.session.query(DataStream).count(),
            "permissions": self.session.query(Permission).count(),
            "roles": self.session.query(Role).count(),
            "audit_logs": self.session.query(AuditLogEntry).count(),
            "sla_targets": self.session.query(SLATargets).count(),
            "performance_metrics": self.session.query(PerformanceMetrics).count(),
            "device_capabilities": self.session.query(DeviceCapabilities).count(),
            "interface_modes": self.session.query(InterfaceMode).count(),
        }
        
        logger.info(f"Database verification: {counts}")
        
        # Verify expected counts
        expected = {
            "tenants": 1,
            "customers": 2,
            "sites": 10,
            "gateways": 30,
            "devices": 300,
            "users": 50,
            "data_streams": 900,
        }
        
        for entity_type, expected_count in expected.items():
            actual_count = counts.get(entity_type, 0)
            if actual_count != expected_count:
                logger.warning(f"Expected {expected_count} {entity_type}, got {actual_count}")
        
        return counts
