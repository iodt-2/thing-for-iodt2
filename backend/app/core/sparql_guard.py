"""
SPARQL Guard

Validates and normalises user-supplied SPARQL before it reaches Fuseki.

The previous check looked at the first line that was not a PREFIX declaration
and asked whether it started with SELECT. A comment line ahead of the query was
enough to slip past it, and nothing capped the result size. This module replaces
that with a comment-aware scan and a default-deny rule on the query form.
"""

import logging
import re
from typing import Optional, Set

logger = logging.getLogger(__name__)


class SparqlGuardError(ValueError):
    """Raised when a query is not allowed through."""


# Read-only query forms. Anything else — INSERT, DELETE, DROP, CLEAR, LOAD,
# CREATE, COPY, MOVE, ADD, WITH — is rejected by not being on this list, so a
# new update keyword in a future SPARQL revision is denied by default.
READ_FORMS: Set[str] = {"SELECT", "ASK", "CONSTRUCT", "DESCRIBE"}

# Forms that accept a LIMIT clause (ASK returns a single boolean)
LIMITABLE_FORMS: Set[str] = {"SELECT", "CONSTRUCT", "DESCRIBE"}

# SPARQL IRIREF production — deliberately strict so a '<' comparison operator
# is not mistaken for the start of an IRI
_IRIREF_RE = re.compile(r'<[^<>"{}|^`\\\s]*>')
_PROLOGUE_RE = re.compile(r"^\s*(?:PREFIX\s+[^\s:]*:\s*<[^>]*>|BASE\s*<[^>]*>)\s*", re.IGNORECASE)
_FIRST_WORD_RE = re.compile(r"^\s*([A-Za-z]+)")
_LIMIT_RE = re.compile(r"\bLIMIT\s+(\d+)", re.IGNORECASE)


def strip_comments(query: str) -> str:
    """
    Remove SPARQL comments (# to end of line).

    A naive strip would corrupt queries: '#' appears inside IRIs
    (<http://twin.dtd/ontology#name>) and inside string literals. This scanner
    skips over both, so only real comments are removed.
    """
    out = []
    i = 0
    length = len(query)
    quote: Optional[str] = None  # active string delimiter, if any

    while i < length:
        if quote:
            if query[i] == "\\" and i + 1 < length:
                # Escaped character inside a literal — copy the pair verbatim
                out.append(query[i:i + 2])
                i += 2
                continue
            if query.startswith(quote, i):
                out.append(quote)
                i += len(quote)
                quote = None
                continue
            out.append(query[i])
            i += 1
            continue

        # Triple-quoted literals must be tested before single-quoted ones
        opening = next(
            (d for d in ('"""', "'''", '"', "'") if query.startswith(d, i)),
            None,
        )
        if opening:
            quote = opening
            out.append(opening)
            i += len(opening)
            continue

        # Only a full IRIREF counts as an IRI; this leaves '<' as a comparison
        # operator alone, e.g. FILTER(?lat < 90)
        iri = _IRIREF_RE.match(query, i)
        if iri:
            out.append(iri.group(0))
            i = iri.end()
            continue

        if query[i] == "#":
            newline = query.find("\n", i)
            i = length if newline == -1 else newline
            continue

        out.append(query[i])
        i += 1

    return "".join(out)


def strip_prologue(query: str) -> str:
    """Remove leading PREFIX and BASE declarations."""
    remaining = query
    while True:
        match = _PROLOGUE_RE.match(remaining)
        if not match:
            return remaining.lstrip()
        remaining = remaining[match.end():]


def detect_query_form(query: str) -> Optional[str]:
    """
    Return the query form (SELECT, ASK, CONSTRUCT, DESCRIBE, INSERT, ...).

    Expects a comment-stripped query. Returns None when nothing recognisable
    is left.
    """
    match = _FIRST_WORD_RE.match(strip_prologue(query))
    return match.group(1).upper() if match else None


def enforce_limit(query: str, max_limit: int) -> str:
    """
    Make sure a limitable query carries a LIMIT no larger than max_limit.

    Looks only after the last closing brace, where the solution modifiers live,
    so a LIMIT inside a subquery is left alone.
    """
    form = detect_query_form(query)
    if form not in LIMITABLE_FORMS:
        return query

    body_end = query.rfind("}") + 1  # 0 when there is no brace, e.g. DESCRIBE <uri>
    head, tail = query[:body_end], query[body_end:]

    match = _LIMIT_RE.search(tail)
    if not match:
        return f"{query.rstrip()}\nLIMIT {max_limit}"

    if int(match.group(1)) <= max_limit:
        return query

    logger.info(f"Capping SPARQL LIMIT {match.group(1)} to {max_limit}")
    return head + tail[:match.start()] + f"LIMIT {max_limit}" + tail[match.end():]


def guard_query(query: str, max_limit: int = 1000) -> str:
    """
    Validate a user-supplied read query and return the version to execute.

    Args:
        query: Raw query text as received from the client
        max_limit: Ceiling for the result size

    Returns:
        Comment-stripped query with an enforced LIMIT

    Raises:
        SparqlGuardError: empty query, or a form that is not read-only
    """
    if not query or not query.strip():
        raise SparqlGuardError("Query is empty")

    cleaned = strip_comments(query).strip()
    if not cleaned:
        raise SparqlGuardError("Query contains nothing but comments")

    form = detect_query_form(cleaned)
    if form is None:
        raise SparqlGuardError("Could not determine the query form")

    if form not in READ_FORMS:
        raise SparqlGuardError(
            f"'{form}' is not allowed. This endpoint is read-only; "
            f"use one of: {', '.join(sorted(READ_FORMS))}"
        )

    return enforce_limit(cleaned, max_limit)
