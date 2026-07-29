"""
Thing Description Service

Renders stored TwinInterface data as W3C WoT Thing Descriptions, which is the
representation a Thing Description Directory is expected to serve.

Conformance note: the platform describes twins, it does not proxy them. There
are no protocol endpoints to read a property or invoke an action, so the
generated TDs carry no `forms`. A TD without forms is incomplete against
WoT TD 1.1; inventing endpoints that would 404 is worse than saying so, and
`ts:noProtocolBinding` marks it explicitly in the document.
"""

from typing import Any, Dict, List, Optional

from app.core.twin_ontology import GEO, TWIN

TD_CONTEXT = "https://www.w3.org/2022/wot/td/v1.1"

# Twin property types as stored, mapped to JSON Schema types used by TD
_TYPE_MAP = {
    "float": "number",
    "double": "number",
    "number": "number",
    "integer": "integer",
    "int": "integer",
    "string": "string",
    "boolean": "boolean",
    "bool": "boolean",
    "object": "object",
    "array": "array",
}


def _json_type(twin_type: Optional[str]) -> str:
    if not twin_type:
        return "string"
    return _TYPE_MAP.get(str(twin_type).lower(), "string")


def _as_number(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _as_bool(value: Any) -> Optional[bool]:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1")


def _property_affordance(prop: Dict[str, Any]) -> Dict[str, Any]:
    """One TD property affordance from a stored twin property."""
    affordance: Dict[str, Any] = {"type": _json_type(prop.get("type"))}

    if prop.get("description"):
        affordance["description"] = prop["description"]

    writable = _as_bool(prop.get("writable"))
    if writable is not None:
        # TD expresses this the other way round
        affordance["readOnly"] = not writable
        affordance["writeOnly"] = False

    if prop.get("unit"):
        affordance["unit"] = prop["unit"]

    minimum = _as_number(prop.get("minimum"))
    maximum = _as_number(prop.get("maximum"))
    if minimum is not None:
        affordance["minimum"] = minimum
    if maximum is not None:
        affordance["maximum"] = maximum

    return affordance


def _links(record: Dict[str, Any], api_base: str) -> List[Dict[str, Any]]:
    """
    Relationships become TD links.

    Inactive relationships are kept but flagged, because history matters here —
    the platform deactivates rather than deletes.
    """
    links = []
    for relationship in record.get("relationships", {}).values():
        target = relationship.get("target")
        if not target:
            continue

        link: Dict[str, Any] = {
            "rel": relationship.get("type") or "related",
            "href": f"{api_base}/things/{target}",
            "type": "application/td+json",
            "title": relationship.get("name"),
        }
        if relationship.get("status") and relationship["status"] != "Active":
            link["ts:relationshipStatus"] = relationship["status"]
        links.append(link)

    return links


def to_thing_description(record: Dict[str, Any], api_base: str) -> Dict[str, Any]:
    """
    Convert one grouped twin record into a Thing Description.

    Args:
        record: Output of TwinRDFService.fetch_thing_records
        api_base: Absolute API base, e.g. http://localhost:3015/api/v2
    """
    name = record.get("name") or ""

    description: Dict[str, Any] = {
        "@context": [
            TD_CONTEXT,
            {"ts": str(TWIN), "geo": str(GEO)},
        ],
        "@type": ["Thing", "ts:TwinInterface"],
        "id": record.get("uri") or f"urn:iodt2:{name}",
        "title": name,
        "securityDefinitions": {"nosec_sc": {"scheme": "nosec"}},
        "security": "nosec_sc",
        # See the module docstring: no protocol bindings exist to describe
        "ts:noProtocolBinding": True,
    }

    if record.get("description"):
        description["description"] = record["description"]

    for source_key, td_key in (
        ("thingType", "ts:thingType"),
        ("originalId", "ts:originalId"),
        ("manufacturer", "ts:manufacturer"),
        ("model", "ts:model"),
        ("serialNumber", "ts:serialNumber"),
        ("firmwareVersion", "ts:firmwareVersion"),
        ("dtdlInterface", "ts:dtdlInterface"),
        ("dtdlCategory", "ts:dtdlCategory"),
        ("address", "ts:address"),
    ):
        if record.get(source_key):
            description[td_key] = record[source_key]

    for source_key, td_key in (("latitude", "geo:lat"), ("longitude", "geo:long"), ("altitude", "geo:alt")):
        value = _as_number(record.get(source_key))
        if value is not None:
            description[td_key] = value

    properties = {
        prop_name: _property_affordance(prop)
        for prop_name, prop in record.get("properties", {}).items()
    }
    if properties:
        description["properties"] = properties

    actions = {}
    for cmd_name, command in record.get("commands", {}).items():
        action: Dict[str, Any] = {}
        if command.get("description"):
            action["description"] = command["description"]
        actions[cmd_name] = action
    if actions:
        description["actions"] = actions

    links = _links(record, api_base)
    if links:
        description["links"] = links

    return description


def to_thing_descriptions(records: List[Dict[str, Any]], api_base: str) -> List[Dict[str, Any]]:
    """Convert a page of records, preserving order."""
    return [to_thing_description(record, api_base) for record in records]
