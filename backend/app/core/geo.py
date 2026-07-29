"""
Geographic helpers for proximity discovery.

Pure functions, no I/O — the distance maths is the part most worth testing on
its own, and it is shared by the SPARQL pre-filter and the exact ranking.
"""

import math
from typing import Dict, Optional, Tuple

# IUGG mean Earth radius
EARTH_RADIUS_KM = 6371.0088

# Length of one degree at the equator
KM_PER_DEGREE_LAT = 110.574
KM_PER_DEGREE_LON = 111.320


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bounding_box(lat: float, lon: float, radius_km: float) -> Dict[str, Optional[float]]:
    """
    Latitude/longitude bounds that enclose the search circle.

    Used only to narrow the SPARQL result set before the exact haversine pass,
    so it may be looser than the circle but must never be tighter.

    Longitude bounds come back as None whenever a simple min/max range cannot
    express the area — near the poles, or when the circle crosses the
    antimeridian. Dropping the bound there costs selectivity; getting it wrong
    would silently lose results.
    """
    lat_delta = radius_km / KM_PER_DEGREE_LAT

    min_lat = lat - lat_delta
    max_lat = lat + lat_delta

    # A circle reaching over a pole covers every longitude
    crosses_pole = min_lat <= -90.0 or max_lat >= 90.0
    min_lat = max(min_lat, -90.0)
    max_lat = min(max_lat, 90.0)

    bounds: Dict[str, Optional[float]] = {
        "min_lat": min_lat,
        "max_lat": max_lat,
        "min_lon": None,
        "max_lon": None,
    }
    if crosses_pole:
        return bounds

    # Longitude lines converge towards the poles, so use the widest latitude
    # the circle reaches — that is where a degree of longitude is shortest
    widest_lat = max(abs(min_lat), abs(max_lat))
    cos_lat = math.cos(math.radians(widest_lat))
    if cos_lat < 1e-9:
        return bounds

    lon_delta = radius_km / (KM_PER_DEGREE_LON * cos_lat)
    if lon_delta >= 180.0:
        return bounds

    min_lon = lon - lon_delta
    max_lon = lon + lon_delta
    if min_lon < -180.0 or max_lon > 180.0:
        # Crosses the antimeridian; a single range would exclude the far side
        return bounds

    bounds["min_lon"] = min_lon
    bounds["max_lon"] = max_lon
    return bounds


def parse_coordinate(value: object) -> Optional[float]:
    """Coordinate values arrive from SPARQL as strings; None when unusable."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_valid_point(lat: Optional[float], lon: Optional[float]) -> bool:
    return (
        lat is not None
        and lon is not None
        and -90.0 <= lat <= 90.0
        and -180.0 <= lon <= 180.0
    )
