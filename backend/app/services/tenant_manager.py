"""
Tenant Manager Service for TwinScale-Lite

Simplified tenant management without user authentication or Ditto integration.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantStats


class TenantManager:
    """Service for managing tenants"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_tenant(self, tenant_data: TenantCreate) -> Tenant:
        """Create a new tenant"""
        
        # Check if tenant ID already exists
        existing_tenant = self.db.query(Tenant).filter(
            Tenant.tenant_id == tenant_data.tenant_id
        ).first()
        
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant with ID '{tenant_data.tenant_id}' already exists"
            )
        
        # Create tenant record
        db_tenant = Tenant(
            tenant_id=tenant_data.tenant_id,
            name=tenant_data.name,
            description=tenant_data.description,
            is_active=tenant_data.is_active,
            max_things=tenant_data.max_things
        )
        
        self.db.add(db_tenant)
        self.db.commit()
        self.db.refresh(db_tenant)
        
        return db_tenant
    
    def get_tenant_by_id(self, tenant_id: str, active_only: bool = False) -> Optional[Tenant]:
        """Get tenant by tenant_id"""
        query = self.db.query(Tenant).filter(Tenant.tenant_id == tenant_id)
        if active_only:
            query = query.filter(Tenant.is_active == True)
        return query.first()
    
    def get_tenant_by_db_id(self, id: int) -> Optional[Tenant]:
        """Get tenant by database ID"""
        return self.db.query(Tenant).filter(Tenant.id == id).first()
    
    def list_tenants(self, active_only: bool = True) -> List[Tenant]:
        """List all tenants"""
        query = self.db.query(Tenant)
        if active_only:
            query = query.filter(Tenant.is_active == True)
        return query.all()
    
    def update_tenant(self, tenant_id: str, tenant_update: TenantUpdate) -> Tenant:
        """Update tenant information"""
        tenant = self.get_tenant_by_id(tenant_id, active_only=False)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found"
            )
        
        # Update fields
        update_data = tenant_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        
        self.db.commit()
        self.db.refresh(tenant)
        return tenant
    
    def deactivate_tenant(self, tenant_id: str) -> Tenant:
        """Deactivate tenant (soft delete)"""
        tenant = self.get_tenant_by_id(tenant_id, active_only=False)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found"
            )
        
        tenant.is_active = False
        self.db.commit()
        self.db.refresh(tenant)
        return tenant
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """Hard delete tenant"""
        tenant = self.get_tenant_by_id(tenant_id, active_only=False)
        if not tenant:
            return False
        
        self.db.delete(tenant)
        self.db.commit()
        return True
    
    async def get_tenant_stats(self, tenant_id: str) -> TenantStats:
        """Get tenant statistics"""
        tenant = self.get_tenant_by_id(tenant_id, active_only=False)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found"
            )
        
        # TODO: Get actual thing count from Fuseki
        # For now, return 0
        stats = TenantStats(
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            is_active=tenant.is_active,
            things_count=0,
            limits={
                "max_things": tenant.max_things
            }
        )
        
        return stats
