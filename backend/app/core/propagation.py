"""
Failure propagation across the twin relationship graph.

Pure functions, no I/O. This is the part of the impact analysis worth testing
on its own: given edges and a set of directly damaged twins, which other twins
lose their function, how far from the damage, and along which relationship.

The direction a failure travels is not the same thing as the direction a
relationship points. `ts:monitors` runs monitor → target, but a destroyed
target is what blinds the monitor, so impact travels the other way. That
mapping lives in the ontology as ts:impactDirection and is passed in here.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

SOURCE_TO_TARGET = "source-to-target"
TARGET_TO_SOURCE = "target-to-source"
BIDIRECTIONAL = "bidirectional"

# Relationships that were switched off carry no failure
INACTIVE_STATUS = "inactive"


@dataclass(frozen=True)
class Edge:
    """One relationship, as stored in the graph."""

    source: str
    target: str
    type: str
    uri: Optional[str] = None
    status: Optional[str] = None


@dataclass(frozen=True)
class Seed:
    """A twin the simulation damaged directly."""

    thing: str
    severity: float


@dataclass(frozen=True)
class Propagation:
    """A twin that was not hit itself but loses function because of one that was."""

    thing: str
    severity: float
    depth: int
    via_thing: str
    via_type: str
    via_relationship: Optional[str] = None


def build_adjacency(
    edges: Iterable[Edge], directions: Dict[str, str]
) -> Dict[str, List[Tuple[str, Edge]]]:
    """
    Who is affected when a given twin fails.

    An unknown relationship type falls back to source-to-target rather than
    being dropped: a relationship the vocabulary has not caught up with should
    still carry impact, and over-reporting is the safer failure here.
    """
    adjacency: Dict[str, List[Tuple[str, Edge]]] = defaultdict(list)
    seen: set = set()

    for edge in edges:
        if edge.status and edge.status.strip().lower() == INACTIVE_STATUS:
            continue

        direction = directions.get(edge.type, SOURCE_TO_TARGET)
        pairs = []
        if direction in (SOURCE_TO_TARGET, BIDIRECTIONAL):
            pairs.append((edge.source, edge.target))
        if direction in (TARGET_TO_SOURCE, BIDIRECTIONAL):
            pairs.append((edge.target, edge.source))

        for origin, affected in pairs:
            if origin == affected:
                continue
            # The store holds both a relationship and its inverse, so the same
            # hop arrives twice; keeping one is enough and keeps paths stable
            key = (origin, affected)
            if key in seen:
                continue
            seen.add(key)
            adjacency[origin].append((affected, edge))

    return adjacency


def propagate(
    edges: Iterable[Edge],
    seeds: Iterable[Seed],
    directions: Dict[str, str],
    *,
    max_depth: int = 3,
    decay: float = 0.6,
    min_severity: float = 0.05,
) -> List[Propagation]:
    """
    Twins that lose function because something they depend on was damaged.

    Args:
        edges: relationships in the tenant graph
        seeds: directly damaged twins with a 0..1 severity
        directions: relationship type → impact direction
        max_depth: how many hops from a damaged twin to follow
        decay: severity retained per hop; 0.6 means a neighbour of a wrecked
            twin is reported at 0.6 and its neighbour at 0.36
        min_severity: below this an effect is not worth reporting

    Returns:
        One entry per affected twin, strongest first. Directly damaged twins
        are not repeated here — they are the input.
    """
    adjacency = build_adjacency(edges, directions)

    seed_severity = {seed.thing: seed.severity for seed in seeds}
    best: Dict[str, Propagation] = {}
    # Severity already established for a twin; seeds start at their own level
    reached: Dict[str, float] = dict(seed_severity)

    queue = deque(
        (thing, severity, 0) for thing, severity in sorted(seed_severity.items())
    )

    while queue:
        thing, severity, depth = queue.popleft()
        if depth >= max_depth:
            continue

        for affected, edge in adjacency.get(thing, []):
            carried = severity * decay
            if carried < min_severity:
                continue
            # A twin damaged directly is already reported at full strength
            if affected in seed_severity:
                continue
            # Cycles end here: coming back around always carries less
            if reached.get(affected, 0.0) >= carried:
                continue

            reached[affected] = carried
            best[affected] = Propagation(
                thing=affected,
                severity=round(carried, 4),
                depth=depth + 1,
                via_thing=thing,
                via_type=edge.type,
                via_relationship=edge.uri,
            )
            queue.append((affected, carried, depth + 1))

    return sorted(best.values(), key=lambda item: (-item.severity, item.thing))


__all__ = [
    "Edge",
    "Seed",
    "Propagation",
    "propagate",
    "build_adjacency",
    "SOURCE_TO_TARGET",
    "TARGET_TO_SOURCE",
    "BIDIRECTIONAL",
]
