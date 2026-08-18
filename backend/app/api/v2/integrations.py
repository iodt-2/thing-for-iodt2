"""
External integration endpoints.

Provider-agnostic by design: the routes name a `{provider}` path segment and
resolve it through the registry, so a second or third partner organisation
needs no endpoint of its own.

Direction is inbound only. Publishing our own twins to a partner platform is a
later phase and deliberately not reachable from here — see
docs/ip2/2026-08-dis-sistem-entegrasyonu.md.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.services.integrations import (
    ExternalProviderError,
    get_provider,
    import_dataset,
    list_providers,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _provider_or_404(provider_key: str):
    try:
        return get_provider(provider_key)
    except KeyError:
        known = ", ".join(p.key for p in list_providers()) or "none registered"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider '{provider_key}'. Available: {known}",
        ) from None


@router.get(
    "/providers",
    summary="List external providers",
    description="Partner platforms this instance can import from, with their datasets.",
)
async def get_providers() -> Dict[str, Any]:
    providers = [provider.describe() for provider in list_providers()]
    return {"providers": providers, "count": len(providers)}


@router.get(
    "/{provider_key}/health",
    summary="Check a provider's health",
    description=(
        "Calls the partner's own health endpoint. Answers 502 when the partner "
        "is unreachable — that is their outage, not ours, and the reason is "
        "passed through unchanged."
    ),
)
async def provider_health(
    provider_key: str = Path(..., description="Provider key, e.g. 'netcad'"),
) -> Dict[str, Any]:
    provider = _provider_or_404(provider_key)
    try:
        upstream = await provider.health()
    except ExternalProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return {"provider": provider.key, "base_url": provider.base_url, "upstream": upstream}


@router.post(
    "/{provider_key}/import/{dataset}",
    summary="Import a provider dataset as twins",
    description=(
        "Fetches one dataset, maps it to TwinInterface/TwinInstance pairs and "
        "stores them. Imported twins carry their provenance (ts:externalSource, "
        "ts:externalId, ts:externalUrl, ts:fetchedAt) and a ts:contentHash, so "
        "re-running the import leaves unchanged records alone.\n\n"
        "Datasets that declare `requires` link to things another dataset "
        "imports; run those first or the links are dropped."
    ),
)
async def import_provider_dataset(
    provider_key: str = Path(..., description="Provider key, e.g. 'netcad'"),
    dataset: str = Path(..., description="Dataset key, e.g. 'towers'"),
    tenant: Optional[str] = Query(
        None,
        description=(
            "Target tenant. Defaults to the provider's own tenant so imported "
            "data does not land in 'default'."
        ),
    ),
    limit: Optional[int] = Query(None, ge=1, description="Maximum things to store"),
    bbox: Optional[str] = Query(
        None,
        description=(
            "Geographic filter, 'min_lat,min_lon,max_lat,max_lon'. Things "
            "without coordinates are kept."
        ),
    ),
    force: bool = Query(False, description="Store even when the content hash matches"),
    dry_run: bool = Query(False, description="Map and report without writing"),
) -> Dict[str, Any]:
    provider = _provider_or_404(provider_key)

    try:
        report = await import_dataset(
            provider,
            dataset,
            tenant_id=tenant,
            limit=limit,
            bbox=bbox,
            force=force,
            dry_run=dry_run,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ExternalProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return report.to_dict()
