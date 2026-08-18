"""
Provider registry.

One place that knows which partner adapters exist. The REST layer and the
importer look providers up here, so neither imports a partner module directly
and adding an organisation stays a one-line change.
"""

import logging
from typing import Dict, List

from .base import ExternalProvider

logger = logging.getLogger(__name__)

_PROVIDERS: Dict[str, ExternalProvider] = {}


def register(provider: ExternalProvider) -> ExternalProvider:
    """Register an adapter under its key, replacing any previous one."""
    if not provider.key:
        raise ValueError("Provider must declare a key")
    _PROVIDERS[provider.key] = provider
    logger.debug(f"[integrations] registered provider '{provider.key}'")
    return provider


def get_provider(key: str) -> ExternalProvider:
    """
    The adapter registered under `key`.

    Raises:
        KeyError: when no such provider is registered
    """
    try:
        return _PROVIDERS[key]
    except KeyError:
        raise KeyError(f"Unknown provider '{key}'") from None


def list_providers() -> List[ExternalProvider]:
    return list(_PROVIDERS.values())


__all__ = ["register", "get_provider", "list_providers"]
