"""Synchronization between SQLite and Neo4j graph database."""

import logging
from typing import Optional, List
from sqlalchemy.orm import Session

from app.db.graph import GraphDatabase, GraphQueryBuilder
from app.models.entities import (
    Tenant, Customer, Site, Gateway, Device, User, DataStream
)

logger = logging.getLogger(__name__)


class GraphSynchronizer:
    """Synchronizes data between SQLite and Neo4j."""

    def __init__(self, sql_session: Session, graph_db: Optional[GraphDatabase] = None):
        """Initialize graph synchronizer."""
        self.sql_session = sql_session
        self.graph_db = graph_db
        self.query_builder = GraphQueryBuilder(graph_db.session if graph_db else None)

    def sync_all_data(self) -> None:
        """Synchronize all data from SQLite to Neo4j."""
        if not self.graph_db or not self.graph_db.is_connected():
            logger.warning("Graph database not connected. Skipping sync.")
            return

        try:
            logger.info("Starting full data synchronization to Neo4j")

            # Clear existing graph
            self.graph_db.clear_graph()

            # Sync all entities
            self._sync_tenants()
            self._sync_customers()
            self._sync_sites()
            self._sync_gateways()
            self._sync_devices()
            self._sync_users()
            self._sync_data_streams()

            logger.info("Data synchronization completed successfully")
        except Exception as e:
            logger.error(f"Failed to synchronize data: {e}")

    def _sync_tenants(self) -> None:
        """Sync tenants from SQLite to Neo4j."""
        try:
            tenants = self.sql_session.query(Tenant).all()
            logger.info(f"Syncing {len(tenants)} tenants to Neo4j")

            for tenant in tenants:
                self.query_builder.create_node(
                    node_id=tenant.id,
                    node_type="Tenant",
                    properties={
                        "id": tenant.id,
                        "name": tenant.name,
                        "identifier": tenant.identifier,
                        "status": tenant.status,
                        "created_at": tenant.created_at.isoformat() if tenant.created_at else None
                    }
                )
        except Exception as e:
            logger.error(f"Failed to sync tenants: {e}")

    def _sync_customers(self) -> None:
        """Sync customers from SQLite to Neo4j."""
        try:
            customers = self.sql_session.query(Customer).all()
            logger.info(f"Syncing {len(customers)} customers to Neo4j")

            for customer in customers:
                self.query_builder.create_node(
                    node_id=customer.id,
                    node_type="Customer",
                    properties={
                        "id": customer.id,
                        "name": customer.name,
                        "identifier": customer.identifier,
                        "status": customer.status,
                        "created_at": customer.created_at.isoformat() if customer.created_at else None
                    }
                )

                # Create relationship to tenant
                if customer.tenant_id:
                    self.query_builder.create_relationship(
                        source_id=customer.tenant_id,
                        target_id=customer.id,
                        relationship_type="HAS_CUSTOMER"
                    )
        except Exception as e:
            logger.error(f"Failed to sync customers: {e}")

    def _sync_sites(self) -> None:
        """Sync sites from SQLite to Neo4j."""
        try:
            sites = self.sql_session.query(Site).all()
            logger.info(f"Syncing {len(sites)} sites to Neo4j")

            for site in sites:
                self.query_builder.create_node(
                    node_id=site.id,
                    node_type="Site",
                    properties={
                        "id": site.id,
                        "name": site.name,
                        "identifier": site.identifier,
                        "location": site.location,
                        "created_at": site.created_at.isoformat() if site.created_at else None
                    }
                )

                # Create relationship to customer
                if site.customer_id:
                    self.query_builder.create_relationship(
                        source_id=site.customer_id,
                        target_id=site.id,
                        relationship_type="HAS_SITE"
                    )
        except Exception as e:
            logger.error(f"Failed to sync sites: {e}")

    def _sync_gateways(self) -> None:
        """Sync gateways from SQLite to Neo4j."""
        try:
            gateways = self.sql_session.query(Gateway).all()
            logger.info(f"Syncing {len(gateways)} gateways to Neo4j")

            for gateway in gateways:
                self.query_builder.create_node(
                    node_id=gateway.id,
                    node_type="Gateway",
                    properties={
                        "id": gateway.id,
                        "name": gateway.name,
                        "identifier": gateway.identifier,
                        "gateway_type": gateway.gateway_type,
                        "status": gateway.status,
                        "created_at": gateway.created_at.isoformat() if gateway.created_at else None
                    }
                )

                # Create relationship to site
                if gateway.site_id:
                    self.query_builder.create_relationship(
                        source_id=gateway.site_id,
                        target_id=gateway.id,
                        relationship_type="HAS_GATEWAY"
                    )
        except Exception as e:
            logger.error(f"Failed to sync gateways: {e}")

    def _sync_devices(self) -> None:
        """Sync devices from SQLite to Neo4j."""
        try:
            devices = self.sql_session.query(Device).all()
            logger.info(f"Syncing {len(devices)} devices to Neo4j")

            for device in devices:
                self.query_builder.create_node(
                    node_id=device.id,
                    node_type="Device",
                    properties={
                        "id": device.id,
                        "name": device.name,
                        "identifier": device.identifier,
                        "device_type": device.device_type,
                        "status": device.status,
                        "created_at": device.created_at.isoformat() if device.created_at else None
                    }
                )

                # Create relationship to gateway
                if device.gateway_id:
                    self.query_builder.create_relationship(
                        source_id=device.gateway_id,
                        target_id=device.id,
                        relationship_type="HAS_DEVICE"
                    )
        except Exception as e:
            logger.error(f"Failed to sync devices: {e}")

    def _sync_users(self) -> None:
        """Sync users from SQLite to Neo4j."""
        try:
            users = self.sql_session.query(User).all()
            logger.info(f"Syncing {len(users)} users to Neo4j")

            for user in users:
                self.query_builder.create_node(
                    node_id=user.id,
                    node_type="User",
                    properties={
                        "id": user.id,
                        "name": user.name,
                        "identifier": user.identifier,
                        "role": user.role,
                        "created_at": user.created_at.isoformat() if user.created_at else None
                    }
                )

                # Create relationship to site
                if user.site_id:
                    self.query_builder.create_relationship(
                        source_id=user.site_id,
                        target_id=user.id,
                        relationship_type="HAS_USER"
                    )
        except Exception as e:
            logger.error(f"Failed to sync users: {e}")

    def _sync_data_streams(self) -> None:
        """Sync data streams from SQLite to Neo4j."""
        try:
            data_streams = self.sql_session.query(DataStream).all()
            logger.info(f"Syncing {len(data_streams)} data streams to Neo4j")

            for stream in data_streams:
                self.query_builder.create_node(
                    node_id=stream.id,
                    node_type="DataStream",
                    properties={
                        "id": stream.id,
                        "name": stream.name,
                        "identifier": stream.identifier,
                        "data_type": stream.data_type,
                        "unit": stream.unit,
                        "created_at": stream.created_at.isoformat() if stream.created_at else None
                    }
                )

                # Create relationship to device
                if stream.device_id:
                    self.query_builder.create_relationship(
                        source_id=stream.device_id,
                        target_id=stream.id,
                        relationship_type="HAS_DATA_STREAM"
                    )
        except Exception as e:
            logger.error(f"Failed to sync data streams: {e}")

    def sync_entity(self, entity_type: str, entity_id: str) -> None:
        """Sync a single entity to Neo4j."""
        if not self.graph_db or not self.graph_db.is_connected():
            logger.warning("Graph database not connected. Skipping sync.")
            return

        try:
            if entity_type == "Tenant":
                entity = self.sql_session.query(Tenant).filter(Tenant.id == entity_id).first()
                if entity:
                    self.query_builder.create_node(
                        node_id=entity.id,
                        node_type="Tenant",
                        properties={
                            "id": entity.id,
                            "name": entity.name,
                            "identifier": entity.identifier,
                            "status": entity.status,
                            "created_at": entity.created_at.isoformat() if entity.created_at else None
                        }
                    )
            elif entity_type == "Customer":
                entity = self.sql_session.query(Customer).filter(Customer.id == entity_id).first()
                if entity:
                    self.query_builder.create_node(
                        node_id=entity.id,
                        node_type="Customer",
                        properties={
                            "id": entity.id,
                            "name": entity.name,
                            "identifier": entity.identifier,
                            "status": entity.status,
                            "created_at": entity.created_at.isoformat() if entity.created_at else None
                        }
                    )
                    if entity.tenant_id:
                        self.query_builder.create_relationship(
                            source_id=entity.tenant_id,
                            target_id=entity.id,
                            relationship_type="HAS_CUSTOMER"
                        )
            # Add other entity types as needed
        except Exception as e:
            logger.error(f"Failed to sync entity {entity_type}({entity_id}): {e}")
