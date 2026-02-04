"""
Initialize Tenants for TwinScale-Lite

This script creates default tenants for the system.
Run this after database initialization.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal, init_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate
from app.services.tenant_manager import TenantManager


def create_default_tenants():
    """Create default tenants"""

    # Initialize database tables first
    print("Initializing database tables...")
    init_db()
    print("✓ Database tables created")

    # Create database session
    db = SessionLocal()
    tenant_manager = TenantManager(db)

    try:
        # Default tenants to create
        default_tenants = [
            {
                "tenant_id": "default",
                "name": "Default Tenant",
                "description": "Default tenant for TwinScale-Lite",
                "is_active": True,
                "max_things": 10000
            },
            {
                "tenant_id": "iodt2",
                "name": "IoT Department 2",
                "description": "IoT Department 2 tenant",
                "is_active": True,
                "max_things": 5000
            },
            {
                "tenant_id": "kozalak",
                "name": "Kozalak Project",
                "description": "Kozalak IoT sensors project",
                "is_active": True,
                "max_things": 1000
            }
        ]

        print("\nCreating default tenants...")

        for tenant_data in default_tenants:
            # Check if tenant already exists
            existing = tenant_manager.get_tenant_by_id(tenant_data["tenant_id"])

            if existing:
                print(f"  ⚠ Tenant '{tenant_data['tenant_id']}' already exists - skipping")
            else:
                tenant_create = TenantCreate(**tenant_data)
                created_tenant = tenant_manager.create_tenant(tenant_create)
                print(f"  ✓ Created tenant: {created_tenant.tenant_id} ({created_tenant.name})")

        print("\n✅ Tenant initialization completed successfully!")

        # List all tenants
        print("\nCurrent tenants:")
        all_tenants = tenant_manager.list_tenants(active_only=False)
        for tenant in all_tenants:
            status = "Active" if tenant.is_active else "Inactive"
            print(f"  - {tenant.tenant_id}: {tenant.name} [{status}]")

    except Exception as e:
        print(f"\n❌ Error during tenant initialization: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("TwinScale-Lite Tenant Initialization")
    print("=" * 60)
    create_default_tenants()
