"""
T3 — geographic proximity discovery.

Depends on the June work: without location triples in RDF there is nothing to
search, so a failure here may mean H1 regressed rather than T3.
"""

import pytest

from app.core.geo import bounding_box, haversine_km, is_valid_point, parse_coordinate

# Kadıköy, matching the demo scenario
CENTRE = (40.9885, 29.0270)


# ---------------------------------------------------------------------------
# Distance maths
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "label,a,b,expected_km,tolerance",
    [
        ("Istanbul-Ankara", (41.0082, 28.9784), (39.9334, 32.8597), 351, 15),
        ("London-Paris", (51.5074, -0.1278), (48.8566, 2.3522), 344, 10),
        ("same point", (40.0, 29.0), (40.0, 29.0), 0, 0.001),
        ("one degree of latitude", (40.0, 29.0), (41.0, 29.0), 111.2, 0.5),
        ("across the antimeridian", (0.0, 179.95), (0.0, -179.95), 11.1, 1.0),
    ],
)
def test_haversine_against_known_distances(label, a, b, expected_km, tolerance):
    assert haversine_km(*a, *b) == pytest.approx(expected_km, abs=tolerance)


def test_haversine_is_symmetric():
    forward = haversine_km(40.9, 29.0, 41.2, 29.5)
    backward = haversine_km(41.2, 29.5, 40.9, 29.0)

    assert forward == pytest.approx(backward)


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------

def test_box_is_used_where_it_can_be():
    box = bounding_box(*CENTRE, radius_km=1.0)

    assert box["min_lon"] is not None and box["max_lon"] is not None
    assert box["min_lat"] < CENTRE[0] < box["max_lat"]


@pytest.mark.parametrize(
    "lat,lon,radius_km,reason",
    [
        (89.9, 0.0, 100.0, "circle reaches over the pole"),
        (0.0, 179.9, 100.0, "circle crosses the antimeridian"),
        (0.0, 0.0, 30000.0, "circle wraps the globe"),
    ],
)
def test_longitude_bound_is_dropped_when_it_cannot_be_expressed(lat, lon, radius_km, reason):
    """
    The box only narrows the candidate set. Where a single min/max range would
    exclude part of the circle, the bound is dropped rather than guessed —
    haversine still applies the exact limit, so results are never lost.
    """
    box = bounding_box(lat, lon, radius_km)

    assert box["min_lon"] is None, reason
    assert box["max_lon"] is None, reason


def test_latitude_bounds_stay_on_the_globe():
    box = bounding_box(89.9, 0.0, 500.0)

    assert -90.0 <= box["min_lat"] <= 90.0
    assert -90.0 <= box["max_lat"] <= 90.0


def test_box_never_excludes_a_point_inside_the_circle():
    """The pre-filter must be loose, never tight."""
    import math

    lat, lon, radius = 40.9885, 29.0270, 5.0
    box = bounding_box(lat, lon, radius)

    for bearing in range(0, 360, 15):
        # A point just inside the circle edge, in every direction
        d = (radius - 0.01) / 6371.0088
        phi1, lambda1 = math.radians(lat), math.radians(lon)
        theta = math.radians(bearing)
        phi2 = math.asin(math.sin(phi1) * math.cos(d) + math.cos(phi1) * math.sin(d) * math.cos(theta))
        lambda2 = lambda1 + math.atan2(
            math.sin(theta) * math.sin(d) * math.cos(phi1),
            math.cos(d) - math.sin(phi1) * math.sin(phi2),
        )
        plat, plon = math.degrees(phi2), math.degrees(lambda2)

        assert box["min_lat"] <= plat <= box["max_lat"], f"latitude excluded at {bearing}°"
        if box["min_lon"] is not None:
            assert box["min_lon"] <= plon <= box["max_lon"], f"longitude excluded at {bearing}°"


# ---------------------------------------------------------------------------
# Coordinate parsing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value,expected",
    [("40.9885", 40.9885), (29, 29.0), ("", None), (None, None), ("abc", None), ("1e2", 100.0)],
)
def test_parse_coordinate(value, expected):
    assert parse_coordinate(value) == expected


@pytest.mark.parametrize(
    "lat,lon,valid",
    [(40.0, 29.0, True), (90.0, 180.0, True), (-90.0, -180.0, True),
     (91.0, 0.0, False), (0.0, 181.0, False), (None, 0.0, False), (0.0, None, False)],
)
def test_is_valid_point(lat, lon, valid):
    assert is_valid_point(lat, lon) is valid


# ---------------------------------------------------------------------------
# End to end against the local store
# ---------------------------------------------------------------------------

NEARBY_FIXTURE = [
    ("centre-sensor", 40.9885, 29.0270),      # 0 km
    ("close-sensor", 40.9920, 29.0300),       # ~0.5 km
    ("mid-sensor", 41.0100, 29.0500),         # ~3 km
    ("far-sensor", 41.2000, 29.5000),         # ~46 km
    ("located-nowhere", None, None),          # no coordinates at all
]


@pytest.fixture
def located_things(twin_store):
    for name, lat, lon in NEARBY_FIXTURE:
        thing = {"@id": name}
        if lat is not None:
            thing["latitude"], thing["longitude"] = lat, lon
        twin_store.add_thing(thing)
    return twin_store


def short_names(matches):
    return [uri.split("/")[-1].replace("default-", "") for uri, _distance in matches]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "radius_km,expected",
    [
        (0.1, ["centre-sensor"]),
        (1.0, ["centre-sensor", "close-sensor"]),
        (5.0, ["centre-sensor", "close-sensor", "mid-sensor"]),
        (100.0, ["centre-sensor", "close-sensor", "mid-sensor", "far-sensor"]),
    ],
)
async def test_radius_filters(located_things, radius_km, expected):
    matches = await located_things.service.find_nearby(
        *CENTRE, radius_km=radius_km, tenant_id="default", limit=50
    )

    assert short_names(matches) == expected


@pytest.mark.asyncio
async def test_results_are_ordered_by_distance(located_things):
    matches = await located_things.service.find_nearby(
        *CENTRE, radius_km=100.0, tenant_id="default", limit=50
    )
    distances = [distance for _uri, distance in matches]

    assert distances == sorted(distances)


@pytest.mark.asyncio
async def test_things_without_coordinates_cannot_match(located_things):
    matches = await located_things.service.find_nearby(
        *CENTRE, radius_km=20000.0, tenant_id="default", limit=50
    )

    assert "located-nowhere" not in short_names(matches)


@pytest.mark.asyncio
async def test_limit_keeps_the_closest(located_things):
    everything = await located_things.service.find_nearby(
        *CENTRE, radius_km=100.0, tenant_id="default", limit=50
    )
    limited = await located_things.service.find_nearby(
        *CENTRE, radius_km=100.0, tenant_id="default", limit=2
    )

    assert limited == everything[:2]


@pytest.mark.asyncio
async def test_other_tenants_are_invisible(twin_store):
    twin_store.add_thing({"@id": "ours", "latitude": 40.9885, "longitude": 29.0270})
    twin_store.add_thing(
        {"@id": "theirs", "latitude": 40.9886, "longitude": 29.0271}, tenant="acme"
    )

    matches = await twin_store.service.find_nearby(
        *CENTRE, radius_km=5.0, tenant_id="default", limit=50
    )

    assert short_names(matches) == ["ours"]


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

def test_nearby_endpoint_reports_distance(discovery_client, located_things):
    response = discovery_client.get(
        "/api/v2/discovery/nearby",
        params={"lat": CENTRE[0], "lon": CENTRE[1], "radius_km": 5},
    )
    body = response.json()

    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] == "application/ld+json"
    assert len(body) == 3
    distances = [td["ts:distanceKm"] for td in body]
    assert distances == sorted(distances)


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 91, "lon": 29, "radius_km": 1},
        {"lat": 40, "lon": 181, "radius_km": 1},
        {"lat": 40, "lon": 29, "radius_km": 0},
        {"lat": 40, "lon": 29, "radius_km": 10000},
        {"lon": 29, "radius_km": 1},
    ],
)
def test_invalid_parameters_are_rejected(discovery_client, params):
    assert discovery_client.get("/api/v2/discovery/nearby", params=params).status_code == 422


def test_no_match_returns_an_empty_list(discovery_client, located_things):
    # Sydney
    response = discovery_client.get(
        "/api/v2/discovery/nearby", params={"lat": -33.9, "lon": 151.2, "radius_km": 1}
    )

    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["X-Total-Count"] == "0"
