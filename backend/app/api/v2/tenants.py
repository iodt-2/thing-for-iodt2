"""
Tenant API Endpoints for TwinScale-Lite

Simplified tenant management without authentication.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    Tenant as TenantSchema,
    TenantStats,
    TenantValidationResponse
)
from app.services.tenant_manager import TenantManager

router = APIRouter()


def get_tenant_manager(db: Session = Depends(get_db)) -> TenantManager:
    """Get TenantManager instance"""
    return TenantManager(db)


@router.post("/", response_model=TenantSchema, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
):
    """
    Create a new tenant

    - **tenant_id**: Unique identifier for the tenant (alphanumeric + hyphens)
    - **name**: Human-readable name for the tenant
    - **description**: Optional description
    """
    tenant = tenant_manager.create_tenant(tenant_data)
    return tenant


@router.get("/validate/{tenant_id}", response_model=TenantValidationResponse)
async def validate_tenant_id(
    tenant_id: str,
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """
    Check if a tenant ID is available for registration
    
    Returns:
    - 200 OK: Always returns availability status
      - {"available": true, "message": "Tenant ID is available"} 
      - {"available": false, "message": "Tenant ID is already taken"}
    """
    existing_tenant = tenant_manager.get_tenant_by_id(tenant_id, active_only=False)
    if existing_tenant:
        return {"available": False, "message": "Tenant ID is already taken"}
    else:
        return {"available": True, "message": "Tenant ID is available"}


@router.get("/", response_model=List[TenantSchema])
def list_tenants(
    active_only: bool = Query(True, description="Filter only active tenants"),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """
    List all tenants

    - **active_only**: If true, only returns active tenants
    """
    return tenant_manager.list_tenants(active_only=active_only)


@router.get("/{tenant_id}", response_model=TenantSchema)
def get_tenant(
    tenant_id: str,
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """Get specific tenant by ID"""
    tenant = tenant_manager.get_tenant_by_id(tenant_id, active_only=False)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found"
        )
    return tenant


@router.put("/{tenant_id}", response_model=TenantSchema)
def update_tenant(
    tenant_id: str,
    tenant_update: TenantUpdate,
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """Update tenant information"""
    return tenant_manager.update_tenant(tenant_id, tenant_update)


@router.delete("/{tenant_id}")
def deactivate_tenant(
    tenant_id: str,
    hard_delete: bool = Query(False, description="Perform hard delete instead of deactivation"),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """
    Deactivate or delete a tenant
    
    - **hard_delete**: If true, permanently deletes the tenant. If false, just deactivates it.
    """
    if hard_delete:
        success = tenant_manager.delete_tenant(tenant_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found"
            )
        return {"message": f"Tenant '{tenant_id}' permanently deleted"}
    else:
        tenant = tenant_manager.deactivate_tenant(tenant_id)
        return {"message": f"Tenant '{tenant_id}' deactivated", "tenant": tenant}


@router.get("/{tenant_id}/stats", response_model=TenantStats)
async def get_tenant_stats(
    tenant_id: str,
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """Get tenant statistics"""
    return await tenant_manager.get_tenant_stats(tenant_id)
