"""
H6 — the SPARQL guard.

The previous check read the first non-PREFIX line and asked whether it started
with SELECT, so a leading comment walked straight past it. Nothing capped the
result size either.
"""

import pytest

from app.core.sparql_guard import (
    SparqlGuardError, detect_query_form, guard_query, strip_comments,
)

MAX = 100


# ---------------------------------------------------------------------------
# Rejection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query",
    [
        "# harmless looking comment\nDROP ALL",
        "# comment\nDELETE WHERE { ?s ?p ?o }",
        "\n\n   # comment\n  INSERT DATA { <a:b> <a:c> <a:d> }",
    ],
    ids=["drop", "delete", "insert"],
)
def test_comment_prefixed_updates_are_rejected(query):
    """These are exactly the bodies that slipped past the old check."""
    with pytest.raises(SparqlGuardError):
        guard_query(query, max_limit=MAX)


@pytest.mark.parametrize(
    "query",
    [
        "DROP ALL",
        "CLEAR GRAPH <http://x>",
        "LOAD <http://elsewhere/data.ttl>",
        "CREATE GRAPH <http://x>",
        "COPY DEFAULT TO <http://x>",
        "WITH <http://g> DELETE { ?s ?p ?o } WHERE { ?s ?p ?o }",
        "PREFIX ts: <http://twin.dtd/ontology#>\nINSERT DATA { ts:a ts:b ts:c }",
    ],
)
def test_update_forms_are_rejected(query):
    with pytest.raises(SparqlGuardError):
        guard_query(query, max_limit=MAX)


@pytest.mark.parametrize("query", ["", "   \n  ", "# nothing but a comment"])
def test_empty_input_is_rejected(query):
    with pytest.raises(SparqlGuardError):
        guard_query(query, max_limit=MAX)


def test_rejection_message_names_the_form():
    with pytest.raises(SparqlGuardError, match="DROP"):
        guard_query("DROP ALL", max_limit=MAX)


# ---------------------------------------------------------------------------
# Acceptance
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query,form",
    [
        ("SELECT * WHERE { ?s ?p ?o }", "SELECT"),
        ("ASK { ?s ?p ?o }", "ASK"),
        ("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", "CONSTRUCT"),
        ("DESCRIBE <http://iodt2.com/x>", "DESCRIBE"),
        ("# leading comment\nSELECT * WHERE { ?s ?p ?o }", "SELECT"),
        ("PREFIX ts: <http://twin.dtd/ontology#>\nSELECT * WHERE { ?s ?p ?o }", "SELECT"),
    ],
)
def test_read_forms_are_accepted(query, form):
    guarded = guard_query(query, max_limit=MAX)

    assert detect_query_form(guarded) == form


# ---------------------------------------------------------------------------
# LIMIT enforcement
# ---------------------------------------------------------------------------

def test_missing_limit_is_added():
    assert f"LIMIT {MAX}" in guard_query("SELECT * WHERE { ?s ?p ?o }", max_limit=MAX)


def test_limit_below_the_ceiling_is_left_alone():
    guarded = guard_query("SELECT * WHERE { ?s ?p ?o } LIMIT 5", max_limit=MAX)

    assert "LIMIT 5" in guarded
    assert f"LIMIT {MAX}" not in guarded


def test_limit_above_the_ceiling_is_capped():
    guarded = guard_query("SELECT * WHERE { ?s ?p ?o } LIMIT 999999", max_limit=MAX)

    assert f"LIMIT {MAX}" in guarded
    assert "999999" not in guarded


def test_subquery_limit_survives():
    """Only the solution modifiers after the last brace may be rewritten."""
    guarded = guard_query(
        "SELECT * WHERE { { SELECT ?s WHERE { ?s ?p ?o } LIMIT 3 } ?s ?p ?o }",
        max_limit=MAX,
    )

    assert "LIMIT 3" in guarded
    assert f"LIMIT {MAX}" in guarded


def test_ask_gets_no_limit():
    """ASK returns a single boolean; a LIMIT there is a syntax error."""
    assert "LIMIT" not in guard_query("ASK { ?s ?p ?o }", max_limit=MAX).upper()


# ---------------------------------------------------------------------------
# Comment stripping — '#' is not always a comment
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query,must_survive",
    [
        ("SELECT * WHERE { ?s <http://twin.dtd/ontology#name> ?o }", "ontology#name"),
        ('SELECT * WHERE { ?s ?p "colour #ff0000" }', "#ff0000"),
        ("SELECT * WHERE { ?s ?p 'single #quoted' }", "#quoted"),
        ('SELECT * WHERE { ?s ?p """multi\nline # hash""" }', "line # hash"),
        # '<' as a comparison operator must not be read as the start of an IRI,
        # or the comment after it would be kept
        ("SELECT * WHERE { ?s ?p ?o FILTER(?o < 90) }", "< 90"),
    ],
    ids=["iri", "literal", "single-quoted", "triple-quoted", "less-than"],
)
def test_hash_inside_iris_and_literals_survives(query, must_survive):
    assert must_survive in strip_comments(query)


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * WHERE { ?s ?p ?o } # trailing comment",
        "# leading comment\nSELECT * WHERE { ?s ?p ?o }",
        "SELECT * WHERE { ?s ?p ?o FILTER(?o < 90) } # after a comparison",
    ],
)
def test_real_comments_are_removed(query):
    assert "comment" not in strip_comments(query)


def test_realistic_query_survives_intact():
    """A saved search from the UI must come through unharmed."""
    query = """PREFIX ts: <http://twin.dtd/ontology#>
# Relationships by type
SELECT ?iface ?rel WHERE {
  GRAPH ?g {
    ?iface ts:hasRelationship ?rel .
    ?rel ts:relationshipType ts:feeds .
  }
}"""

    guarded = guard_query(query, max_limit=MAX)

    assert "ts:feeds" in guarded
    assert "ts:hasRelationship" in guarded
    assert "Relationships by type" not in guarded
    assert f"LIMIT {MAX}" in guarded
