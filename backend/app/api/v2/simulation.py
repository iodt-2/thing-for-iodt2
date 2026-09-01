"""
Simulation endpoints — hazard from a partner, consequences from our graph.

The partner answers "how hard does this shake, and what breaks". The platform
answers "and what stops working as a result", which is the part only a
relationship graph can supply.

Runs are stored in their own named graphs. Twin graphs are left alone unless
the caller explicitly asks for `apply_status`, because a hypothetical must not
silently rewrite the live model.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

from app.services.integrations import ExternalProviderError, get_provider, list_providers
from app.services.integrations.base import HazardScenario
from app.services.simulation_service import (
    DEFAULT_FAILURE_THRESHOLD,
    run_hazard_simulation,
)
from app.services.twin_rdf_service import TwinRDFService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])


class EarthquakeRequest(BaseModel):
    """An epicentre and how the failure analysis should be run."""

    latitude: float = Field(..., ge=-90, le=90, description="Epicentre latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Epicentre longitude")
    magnitude: float = Field(..., gt=0, le=10, description="Moment magnitude")
    depth_km: float = Field(10.0, ge=0, description="Focal depth in km")

    tenant: Optional[str] = Field(
        None, description="Tenant whose twins take part; defaults to the provider's"
    )
    radius_km: float = Field(
        50.0, gt=0, le=1000, description="How far from the epicentre to include twins"
    )
    limit: Optional[int] = Field(
        None, ge=1, description="Cap on how many twins are sent to the partner"
    )

    max_depth: int = Field(3, ge=1, le=10, description="Hops to follow from a failure")
    decay: float = Field(0.6, gt=0, le=1, description="Severity retained per hop")
    min_severity: float = Field(
        0.05, ge=0, le=1, description="Below this a knock-on effect is not reported"
    )
    failure_threshold: float = Field(
        DEFAULT_FAILURE_THRESHOLD,
        ge=0,
        le=1,
        description="Damage at or above this counts as a failure and propagates",
    )

    apply_status: bool = Field(
        False,
        description=(
            "Also mark affected relationships ts:Degraded in the twin graphs. "
            "Off by default — this writes to the live model."
        ),
    )
    persist: bool = Field(True, description="Store the run in its own named graph")


def _provider_or_404(provider_key: str):
    try:
        return get_provider(provider_key)
    except KeyError:
        known = ", ".join(p.key for p in list_providers()) or "none registered"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider '{provider_key}'. Available: {known}",
        ) from None


@router.post(
    "/{provider_key}/earthquake",
    summary="Simulate an earthquake and trace its knock-on effects",
    description=(
        "Sends the tenant's located twins to the partner's ground-motion model, "
        "then follows the damage through the relationship graph: a twin that "
        "fails takes with it whatever depends on it. Direction of travel comes "
        "from ts:impactDirection in the ontology, not from a rule in the code."
    ),
)
async def simulate_earthquake(
    request: EarthquakeRequest,
    provider_key: str = Path(..., description="Provider key, e.g. 'netcad'"),
) -> Dict[str, Any]:
    provider = _provider_or_404(provider_key)

    scenario = HazardScenario(
        latitude=request.latitude,
        longitude=request.longitude,
        magnitude=request.magnitude,
        depth_km=request.depth_km,
    )

    try:
        return await run_hazard_simulation(
            provider,
            scenario,
            tenant_id=request.tenant or provider.default_tenant,
            radius_km=request.radius_km,
            limit=request.limit,
            max_depth=request.max_depth,
            decay=request.decay,
            min_severity=request.min_severity,
            failure_threshold=request.failure_threshold,
            apply_status=request.apply_status,
            persist=request.persist,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ExternalProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.get(
    "/runs",
    summary="List stored simulation runs",
)
async def list_runs(
    tenant: str = Query("default", description="Tenant scope"),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    service = TwinRDFService()
    runs = await service.list_simulation_runs(tenant_id=tenant, limit=limit)
    return {"tenant_id": tenant, "runs": runs, "count": len(runs)}


@router.get(
    "/runs/{run_id}",
    summary="One simulation run with its impacts",
)
async def get_run(
    run_id: str = Path(..., description="Run identifier"),
    tenant: str = Query("default", description="Tenant scope"),
) -> Dict[str, Any]:
    service = TwinRDFService()
    run = await service.get_simulation_run(run_id, tenant_id=tenant)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No simulation run '{run_id}' for tenant '{tenant}'",
        )
    return run
