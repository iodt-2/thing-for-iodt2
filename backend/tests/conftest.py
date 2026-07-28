"""
Shared pytest setup.

Puts the backend package on sys.path so tests can `from app...` regardless of
where pytest is invoked from.
"""

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session")
def ontology():
    """A private ontology graph — safe for tests that add triples to it."""
    from app.core.twin_ontology import get_twin_ontology

    return get_twin_ontology()
