"""Database connection and session management."""

import logging
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.models.base import Base
# Import models to register them with Base
from app.models import entities  # noqa: F401

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""

    def __init__(self, database_url: str = None):
        """Initialize database connection."""
        self.database_url = database_url or settings.database_url
        self.engine = None
        self.SessionLocal = None

    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        logger.info(f"Initializing database: {self.database_url}")

        # Create engine with connection pooling
        # For SQLite, use StaticPool for in-memory or NullPool for file-based
        # to avoid threading issues
        if "sqlite" in self.database_url:
            if ":memory:" in self.database_url:
                from sqlalchemy.pool import StaticPool
                pool_class = StaticPool
                pool_kwargs = {}
            else:
                from sqlalchemy.pool import NullPool
                pool_class = NullPool
                pool_kwargs = {}
        else:
            from sqlalchemy.pool import QueuePool
            pool_class = QueuePool
            pool_kwargs = {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }

        self.engine = create_engine(
            self.database_url,
            echo=settings.database_echo,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
            poolclass=pool_class,
            **pool_kwargs,
        )

        # Enable foreign keys for SQLite
        if "sqlite" in self.database_url:
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info("Database initialized successfully")

    def create_tables(self) -> None:
        """Create all tables in the database."""
        if self.engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.info("Creating database tables")
        logger.info(f"Base.metadata.tables: {list(Base.metadata.tables.keys())}")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
        try:
            self._create_indexes()
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}. Continuing without indexes.")

    def _create_indexes(self) -> None:
        """Create indexes for frequently accessed hierarchies."""
        if self.engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        # Skip index creation for in-memory databases
        if ":memory:" in self.database_url:
            logger.info("Skipping index creation for in-memory database")
            return

        logger.info("Creating database indexes")
        with self.engine.begin() as conn:
            # Customer hierarchy indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_customers_tenant_id ON customers(tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_customers_identifier ON customers(identifier)"))
            
            # Site hierarchy indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sites_customer_id ON sites(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sites_tenant_id ON sites(tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sites_identifier ON sites(identifier)"))
            
            # Gateway hierarchy indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_gateways_site_id ON gateways(site_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_gateways_customer_id ON gateways(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_gateways_tenant_id ON gateways(tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_gateways_identifier ON gateways(identifier)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_gateways_status ON gateways(status)"))
            
            # Device hierarchy indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_gateway_id ON devices(gateway_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_site_id ON devices(site_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_customer_id ON devices(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_tenant_id ON devices(tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_identifier ON devices(identifier)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)"))
            
            # User hierarchy indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_site_id ON users(site_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_customer_id ON users(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_identifier ON users(identifier)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)"))
            
            # DataStream hierarchy indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_streams_device_id ON data_streams(device_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_streams_gateway_id ON data_streams(gateway_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_streams_site_id ON data_streams(site_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_streams_customer_id ON data_streams(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_streams_tenant_id ON data_streams(tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_streams_identifier ON data_streams(identifier)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_streams_data_type ON data_streams(data_type)"))
            
            # Cache entry indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_entries_key ON cache_entries(key)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_entries_entity_type ON cache_entries(entity_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_entries_entity_id ON cache_entries(entity_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_entries_expires_at ON cache_entries(expires_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_entries_is_valid ON cache_entries(is_valid)"))
            
            # Sync queue entry indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sync_queue_entries_action_type ON sync_queue_entries(action_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sync_queue_entries_entity_type ON sync_queue_entries(entity_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sync_queue_entries_entity_id ON sync_queue_entries(entity_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sync_queue_entries_created_at ON sync_queue_entries(created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sync_queue_entries_status ON sync_queue_entries(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sync_queue_entries_priority ON sync_queue_entries(priority)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sync_queue_entries_status_priority ON sync_queue_entries(status, priority)"))
            
            # Data conflict indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_conflicts_sync_queue_entry_id ON data_conflicts(sync_queue_entry_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_conflicts_entity_type ON data_conflicts(entity_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_conflicts_entity_id ON data_conflicts(entity_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_conflicts_conflict_type ON data_conflicts(conflict_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_data_conflicts_resolution_strategy ON data_conflicts(resolution_strategy)"))
            
            # Sync status indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sync_status_device_id ON sync_status(device_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sync_status_status ON sync_status(status)"))
        
        logger.info("Database indexes created successfully")

    def drop_tables(self) -> None:
        """Drop all tables from the database."""
        if self.engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.warning("Dropping all database tables")
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")

    def get_session(self) -> Session:
        """Get a new database session."""
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.SessionLocal()

    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

    def transaction(self):
        """Context manager for transaction management."""
        return TransactionContext(self.SessionLocal)


# Global database instance
_db = Database()


def initialize_db(database_url: str = None) -> None:
    """Initialize the global database instance."""
    _db.database_url = database_url or settings.database_url
    _db.initialize()


def create_db_tables() -> None:
    """Create all database tables."""
    _db.create_tables()


def drop_db_tables() -> None:
    """Drop all database tables."""
    _db.drop_tables()


def get_db() -> Generator[Session, None, None]:
    """Get a database session for dependency injection."""
    db = _db.get_session()
    try:
        yield db
    finally:
        db.close()


class TransactionContext:
    """Context manager for transaction management."""

    def __init__(self, session_factory):
        """Initialize transaction context."""
        self.session_factory = session_factory
        self.session = None

    def __enter__(self) -> Session:
        """Enter transaction context."""
        self.session = self.session_factory()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context."""
        if exc_type is not None:
            self.session.rollback()
            logger.error(f"Transaction rolled back due to {exc_type.__name__}: {exc_val}")
        else:
            self.session.commit()
        self.session.close()
        return False
