"""
Failure propagation — the part of impact analysis with no I/O in it.

These tests pin the semantics that the rest of the feature rests on: which way
a failure travels, how far it is allowed to go, and that a cycle in the graph
cannot make it run forever.
"""

import pytest

from app.core.propagation import Edge, Seed, build_adjacency, propagate
from app.core.twin_ontology import get_impact_directions

DIRECTIONS = get_impact_directions()


def _by_thing(results):
    return {item.thing: item for item in results}


def test_feeds_carries_failure_to_the_fed_thing():
    edges = [Edge(source="sensor", target="gateway", type="feeds")]

    results = _by_thing(propagate(edges, [Seed("sensor", 1.0)], DIRECTIONS))

    assert "gateway" in results
    assert results["gateway"].depth == 1
    assert results["gateway"].via_thing == "sensor"


def test_feeds_does_not_carry_failure_backwards():
    edges = [Edge(source="sensor", target="gateway", type="feeds")]

    # The gateway failing does not break the sensor that supplies it
    assert propagate(edges, [Seed("gateway", 1.0)], DIRECTIONS) == []


def test_monitors_carries_failure_from_the_observed_thing():
    # A monitor goes blind when what it watches is destroyed — the opposite of
    # how the relationship reads
    edges = [Edge(source="monitor", target="bridge", type="monitors")]

    results = _by_thing(propagate(edges, [Seed("bridge", 1.0)], DIRECTIONS))

    assert "monitor" in results
    assert propagate(edges, [Seed("monitor", 1.0)], DIRECTIONS) == []


def test_depends_on_carries_failure_to_the_dependant():
    edges = [Edge(source="hospital", target="power", type="dependsOn")]

    results = _by_thing(propagate(edges, [Seed("power", 1.0)], DIRECTIONS))

    assert "hospital" in results


def test_contains_carries_both_ways():
    edges = [Edge(source="district", target="building", type="contains")]

    assert "building" in _by_thing(propagate(edges, [Seed("district", 1.0)], DIRECTIONS))
    assert "district" in _by_thing(propagate(edges, [Seed("building", 1.0)], DIRECTIONS))


def test_inverse_types_are_understood():
    # The store holds the inverse the platform generated, not only the asserted
    # direction, so the algorithm must read both
    edges = [Edge(source="gateway", target="sensor", type="isFedBy")]

    results = _by_thing(propagate(edges, [Seed("sensor", 1.0)], DIRECTIONS))

    assert "gateway" in results


def test_duplicate_hops_from_inverse_pairs_collapse():
    edges = [
        Edge(source="sensor", target="gateway", type="feeds"),
        Edge(source="gateway", target="sensor", type="isFedBy"),
    ]

    adjacency = build_adjacency(edges, DIRECTIONS)

    assert [target for target, _edge in adjacency["sensor"]] == ["gateway"]


def test_severity_decays_with_each_hop():
    edges = [
        Edge(source="a", target="b", type="feeds"),
        Edge(source="b", target="c", type="feeds"),
    ]

    results = _by_thing(propagate(edges, [Seed("a", 1.0)], DIRECTIONS, decay=0.5))

    assert results["b"].severity == pytest.approx(0.5)
    assert results["c"].severity == pytest.approx(0.25)
    assert results["c"].depth == 2


def test_depth_limit_stops_the_chain():
    edges = [
        Edge(source="a", target="b", type="feeds"),
        Edge(source="b", target="c", type="feeds"),
        Edge(source="c", target="d", type="feeds"),
    ]

    results = _by_thing(propagate(edges, [Seed("a", 1.0)], DIRECTIONS, max_depth=2))

    assert set(results) == {"b", "c"}


def test_weak_effects_are_not_reported():
    edges = [
        Edge(source="a", target="b", type="feeds"),
        Edge(source="b", target="c", type="feeds"),
    ]

    results = _by_thing(
        propagate(edges, [Seed("a", 1.0)], DIRECTIONS, decay=0.2, min_severity=0.1)
    )

    # 0.2 survives, 0.04 does not
    assert set(results) == {"b"}


def test_a_cycle_terminates():
    edges = [
        Edge(source="a", target="b", type="feeds"),
        Edge(source="b", target="c", type="feeds"),
        Edge(source="c", target="a", type="feeds"),
    ]

    results = _by_thing(propagate(edges, [Seed("a", 1.0)], DIRECTIONS, max_depth=10))

    # The seed is never re-reported, and every other node is visited once
    assert set(results) == {"b", "c"}


def test_directly_damaged_things_are_not_repeated():
    edges = [Edge(source="a", target="b", type="feeds")]

    results = propagate(edges, [Seed("a", 1.0), Seed("b", 1.0)], DIRECTIONS)

    assert results == []


def test_inactive_relationships_carry_nothing():
    edges = [Edge(source="a", target="b", type="feeds", status="Inactive")]

    assert propagate(edges, [Seed("a", 1.0)], DIRECTIONS) == []


def test_unknown_relationship_type_still_carries_impact():
    # A vocabulary that has not caught up should not silently hide a failure
    edges = [Edge(source="a", target="b", type="somethingNew")]

    assert "b" in _by_thing(propagate(edges, [Seed("a", 1.0)], DIRECTIONS))


def test_strongest_path_wins():
    edges = [
        Edge(source="a", target="b", type="feeds"),
        Edge(source="a", target="c", type="feeds"),
        Edge(source="c", target="b", type="feeds"),
    ]

    results = _by_thing(propagate(edges, [Seed("a", 1.0)], DIRECTIONS, decay=0.5))

    # b is reachable in one hop (0.5) and two (0.25); the one-hop path stands
    assert results["b"].severity == pytest.approx(0.5)
    assert results["b"].depth == 1


def test_results_are_ordered_by_severity():
    edges = [
        Edge(source="a", target="b", type="feeds"),
        Edge(source="b", target="c", type="feeds"),
    ]

    results = propagate(edges, [Seed("a", 1.0)], DIRECTIONS, decay=0.5)

    assert [item.thing for item in results] == ["b", "c"]
