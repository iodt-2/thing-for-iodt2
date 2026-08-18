"""
External system integrations.

Partner adapters are registered here, once, at import time. Everything else
reaches them through the registry.
"""

from .base import (
    DatasetSpec,
    ExternalAttribute,
    ExternalLink,
    ExternalProvider,
    ExternalProviderError,
    ExternalThing,
)
from .importer import ImportReport, import_dataset
from .netcad import NetcadProvider
from .registry import get_provider, list_providers, register

register(NetcadProvider())

__all__ = [
    "DatasetSpec",
    "ExternalAttribute",
    "ExternalLink",
    "ExternalProvider",
    "ExternalProviderError",
    "ExternalThing",
    "ImportReport",
    "import_dataset",
    "NetcadProvider",
    "get_provider",
    "list_providers",
    "register",
]
