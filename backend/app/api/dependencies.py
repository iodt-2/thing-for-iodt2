"""
TwinScale-Lite API Dependencies

Simplified dependency injection without authentication.
"""

from typing import Optional
from fastapi import Header, HTTPException, status
import re


def _validate_tenant_format(tenant_id: str) -> bool:
    """Validate tenant ID format"""
    pattern = r'^[a-zA-Z][a-zA-Z0-9\-\.]*$'
    return bool(re.match(pattern, tenant_id)) and len(tenant_id) <= 50


async def get_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> str:
    """
    Get tenant ID from header.

    For TwinScale-Lite, tenant is optional and defaults to "default".
    No authentication required.
    """
    from app.core.config import get_settings
    settings = get_settings()

    # Default tenant if no header
    if not x_tenant_id or not x_tenant_id.strip():
        return settings.DEFAULT_TENANT_ID

    # Validate format if provided
    if not _validate_tenant_format(x_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format. Must start with letter, contain only alphanumeric, dash, dot."
        )

    return x_tenant_id
