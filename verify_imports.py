#!/usr/bin/env python3
"""Verify all imports work correctly."""

import sys

try:
    print("Verifying imports...")
    
    print("  - Importing models...")
    from app.models.entities import (
        Tenant, Customer, Site, Gateway, Device, User, DataStream,
        CacheEntry, SyncQueueEntry, DataConflict, SyncStatus,
        Permission, Role, RolePermission, AccessControl,
        ConflictResolution, AuditLogEntry,
        SLATargets, SLAMetric, PerformanceMetrics,
        DeviceCapabilities, InterfaceMode, InterfaceModePreferences
    )
    print("    ✓ All models imported successfully")
    
    print("  - Importing repositories...")
    from app.db.repositories import (
        PermissionRepository, RoleRepository, RolePermissionRepository,
        AccessControlRepository, ConflictResolutionRepository,
        AuditLogRepository, SLATargetsRepository, SLAMetricRepository,
        PerformanceMetricsRepository, DeviceCapabilitiesRepository,
        InterfaceModeRepository, InterfaceModePreferencesRepository,
        RepositoryFactory
    )
    print("    ✓ All repositories imported successfully")
    
    print("  - Importing services...")
    from app.services.mock_data_generator import MockDataGenerator
    from app.services.database_seeder import DatabaseSeeder
    print("    ✓ All services imported successfully")
    
    print("  - Importing CLI...")
    from app.cli import cli
    print("    ✓ CLI imported successfully")
    
    print("\n✓ All imports verified successfully!")
    sys.exit(0)
    
except Exception as e:
    print(f"\n✗ Import verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
