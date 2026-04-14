"""
Debug Dump Service

Thing create akışında üretilen tüm formatları (JSON, JSON-LD, YAML, RDF/Turtle)
backend/data/debug/ altında zaman damgalı klasörlere kaydeder.

Kullanım:
    from app.services.debug_dump_service import DebugDumpService
    DebugDumpService.dump(thing_id, form_data, interface_yaml, instance_yaml, metadata)
"""

import json
import logging
import os
import re
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from rdflib import Graph, Literal, URIRef, BNode, Namespace
from rdflib.namespace import RDF, RDFS, XSD

logger = logging.getLogger(__name__)

# Debug çıktılarının kök klasörü
_DEBUG_ROOT = Path(__file__).resolve().parents[3] / "data" / "debug"


def _safe_slug(text: str) -> str:
    """Dosya adına uygun kısa slug üretir."""
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", text)
    return slug[:60]


def _build_jsonld(
    thing_id: str,
    interface_yaml_str: str,
    instance_yaml_str: str,
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    YAML içeriğinden JSON-LD belgesi oluşturur.

    Ontoloji: http://twin.dtd/ontology#
    Veri namespace: http://iodt2.com/
    """
    iface = yaml.safe_load(interface_yaml_str)
    inst = yaml.safe_load(instance_yaml_str)

    iface_name = iface["metadata"]["name"]
    inst_name = inst["metadata"]["name"]

    ts = "http://twin.dtd/ontology#"
    tsd = "http://iodt2.com/"

    iface_uri = f"{tsd}{iface_name}"
    inst_uri = f"{tsd}instance/{inst_name}"

    # --- Interface node ---
    iface_node: Dict[str, Any] = {
        "@id": iface_uri,
        "@type": f"{ts}TwinInterface",
        f"{ts}name": [{"@value": iface_name}],
    }

    labels = iface["metadata"].get("labels", {})
    annotations = iface["metadata"].get("annotations", {})

    if labels.get("generated-by"):
        iface_node[f"{ts}generatedBy"] = [{"@value": labels["generated-by"]}]
    if labels.get("generated-at"):
        iface_node[f"{ts}generatedAt"] = [
            {"@value": labels["generated-at"], "@type": "http://www.w3.org/2001/XMLSchema#dateTime"}
        ]
    if labels.get("thing-type"):
        iface_node[f"{ts}thingType"] = [{"@value": labels["thing-type"]}]

    for ann_key, ts_key in [
        ("manufacturer", "manufacturer"),
        ("model", "model"),
        ("serialNumber", "serialNumber"),
        ("firmwareVersion", "firmwareVersion"),
        ("dtdl-interface", "dtdlInterface"),
        ("dtdl-interface-name", "dtdlInterfaceName"),
        ("dtdl-category", "dtdlCategory"),
        ("original-id", "originalId"),
        ("source", "sourceFormat"),
        ("latitude", "latitude"),
        ("longitude", "longitude"),
        ("address", "address"),
        ("altitude", "altitude"),
    ]:
        val = annotations.get(ann_key)
        if val:
            iface_node[f"{ts}{ts_key}"] = [{"@value": val}]

    spec = iface.get("spec", {})

    # Properties
    prop_nodes = []
    for prop in spec.get("properties", []):
        pnode: Dict[str, Any] = {
            "@id": f"{tsd}{iface_name}/property/{prop['name']}",
            "@type": f"{ts}Property",
            f"{ts}propertyName": [{"@value": prop["name"]}],
            f"{ts}propertyType": [{"@value": prop["type"]}],
        }
        if prop.get("description"):
            pnode[f"{ts}description"] = [{"@value": prop["description"]}]
        if prop.get("x-writable") is not None:
            pnode[f"{ts}writable"] = [
                {"@value": prop["x-writable"], "@type": "http://www.w3.org/2001/XMLSchema#boolean"}
            ]
        if prop.get("x-minimum") is not None:
            pnode[f"{ts}minimum"] = [{"@value": prop["x-minimum"]}]
        if prop.get("x-maximum") is not None:
            pnode[f"{ts}maximum"] = [{"@value": prop["x-maximum"]}]
        if prop.get("x-unit"):
            pnode[f"{ts}unit"] = [{"@value": prop["x-unit"]}]
        prop_nodes.append(pnode)

    if prop_nodes:
        iface_node[f"{ts}hasProperty"] = [{"@id": p["@id"]} for p in prop_nodes]

    # Relationships
    rel_nodes = []
    for rel in spec.get("relationships", []):
        rnode: Dict[str, Any] = {
            "@id": f"{tsd}{iface_name}/relationship/{rel['name']}",
            "@type": f"{ts}Relationship",
            f"{ts}relationshipName": [{"@value": rel["name"]}],
            f"{ts}targetInterface": [{"@value": rel.get("interface", "")}],
        }
        if rel.get("description"):
            rnode[f"{ts}description"] = [{"@value": rel["description"]}]
        rel_nodes.append(rnode)

    if rel_nodes:
        iface_node[f"{ts}hasRelationship"] = [{"@id": r["@id"]} for r in rel_nodes]

    # Commands
    cmd_nodes = []
    for cmd in spec.get("commands", []):
        cnode: Dict[str, Any] = {
            "@id": f"{tsd}{iface_name}/command/{cmd['name']}",
            "@type": f"{ts}Command",
            f"{ts}commandName": [{"@value": cmd["name"]}],
        }
        if cmd.get("description"):
            cnode[f"{ts}description"] = [{"@value": cmd["description"]}]
        if cmd.get("schema"):
            cnode[f"{ts}schema"] = [{"@value": json.dumps(cmd["schema"])}]
        cmd_nodes.append(cnode)

    if cmd_nodes:
        iface_node[f"{ts}hasCommand"] = [{"@id": c["@id"]} for c in cmd_nodes]

    # --- Instance node ---
    inst_node: Dict[str, Any] = {
        "@id": inst_uri,
        "@type": f"{ts}TwinInstance",
        f"{ts}name": [{"@value": inst_name}],
        f"{ts}instanceOf": [{"@id": iface_uri}],
    }

    ilabels = inst["metadata"].get("labels", {})
    if ilabels.get("generated-by"):
        inst_node[f"{ts}generatedBy"] = [{"@value": ilabels["generated-by"]}]
    if ilabels.get("generated-at"):
        inst_node[f"{ts}generatedAt"] = [
            {"@value": ilabels["generated-at"], "@type": "http://www.w3.org/2001/XMLSchema#dateTime"}
        ]

    irel_nodes = []
    for rel in inst.get("spec", {}).get("twinInstanceRelationships", []):
        target_uri = f"{tsd}instance/{rel.get('instance', '')}"
        bnode_id = f"_:irel_{inst_name}_{rel['name']}"
        irnode: Dict[str, Any] = {
            "@id": bnode_id,
            "@type": f"{ts}InstanceRelationship",
            f"{ts}relationshipName": [{"@value": rel["name"]}],
            f"{ts}targetInstance": [{"@id": target_uri}],
        }
        irel_nodes.append(irnode)

    if irel_nodes:
        inst_node[f"{ts}hasInstanceRelationship"] = [{"@id": r["@id"]} for r in irel_nodes]

    # Assemble graph
    graph_nodes = [iface_node] + prop_nodes + rel_nodes + cmd_nodes + [inst_node] + irel_nodes

    return {
        "@context": {
            "ts": ts,
            "tsd": tsd,
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        },
        "@graph": graph_nodes,
    }


def _build_rdf_turtle(
    interface_yaml_str: str,
    instance_yaml_str: str,
    metadata: Optional[Dict[str, Any]],
) -> str:
    """
    YAML içeriğinden RDF Turtle dizgesi oluşturur.
    TwinRDFService ile aynı mantığı kullanır; Fuseki bağlantısı gerektirmez.
    """
    from ..core.twin_ontology import (
        TWIN, TWIN_DATA,
        create_interface_uri, create_instance_uri,
        create_property_uri, create_relationship_uri, create_command_uri,
    )

    TS = TWIN
    TSD = TWIN_DATA

    iface_data = yaml.safe_load(interface_yaml_str)
    inst_data = yaml.safe_load(instance_yaml_str)

    g = Graph()
    g.bind("ts", TS)
    g.bind("tsd", TSD)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    iface_name = iface_data["metadata"]["name"]
    interface_uri = create_interface_uri(iface_name)

    g.add((interface_uri, RDF.type, TS.TwinInterface))
    g.add((interface_uri, TS.name, Literal(iface_name)))

    labels = iface_data["metadata"].get("labels", {})
    annotations = iface_data["metadata"].get("annotations", {})

    if labels.get("generated-by"):
        g.add((interface_uri, TS.generatedBy, Literal(labels["generated-by"])))
    if labels.get("generated-at"):
        g.add((interface_uri, TS.generatedAt,
               Literal(labels["generated-at"], datatype=XSD.dateTime)))
    if labels.get("thing-type"):
        g.add((interface_uri, TS.thingType, Literal(labels["thing-type"])))

    for ann_key, ts_prop in [
        ("source", TS.sourceFormat),
        ("original-id", TS.originalId),
        ("manufacturer", TS.manufacturer),
        ("model", TS.model),
        ("serialNumber", TS.serialNumber),
        ("firmwareVersion", TS.firmwareVersion),
        ("dtdl-interface", TS.dtdlInterface),
        ("dtdl-interface-name", TS.dtdlInterfaceName),
        ("dtdl-category", TS.dtdlCategory),
    ]:
        val = annotations.get(ann_key)
        if val:
            g.add((interface_uri, ts_prop, Literal(val)))

    spec = iface_data.get("spec", {})

    for prop in spec.get("properties", []):
        prop_uri = create_property_uri(iface_name, prop["name"])
        g.add((prop_uri, RDF.type, TS.Property))
        g.add((prop_uri, TS.propertyName, Literal(prop["name"])))
        g.add((prop_uri, TS.propertyType, Literal(prop["type"])))
        if prop.get("description"):
            g.add((prop_uri, TS.description, Literal(prop["description"])))
        if prop.get("x-writable") is not None:
            g.add((prop_uri, TS.writable,
                   Literal(prop["x-writable"], datatype=XSD.boolean)))
        if prop.get("x-minimum") is not None:
            g.add((prop_uri, TS.minimum, Literal(prop["x-minimum"])))
        if prop.get("x-maximum") is not None:
            g.add((prop_uri, TS.maximum, Literal(prop["x-maximum"])))
        if prop.get("x-unit"):
            g.add((prop_uri, TS.unit, Literal(prop["x-unit"])))
        g.add((interface_uri, TS.hasProperty, prop_uri))

    for rel in spec.get("relationships", []):
        rel_uri = create_relationship_uri(iface_name, rel["name"])
        g.add((rel_uri, RDF.type, TS.Relationship))
        g.add((rel_uri, TS.relationshipName, Literal(rel["name"])))
        g.add((rel_uri, TS.targetInterface, Literal(rel.get("interface", ""))))
        if rel.get("description"):
            g.add((rel_uri, TS.description, Literal(rel["description"])))
        g.add((interface_uri, TS.hasRelationship, rel_uri))

    for cmd in spec.get("commands", []):
        cmd_uri = create_command_uri(iface_name, cmd["name"])
        g.add((cmd_uri, RDF.type, TS.Command))
        g.add((cmd_uri, TS.commandName, Literal(cmd["name"])))
        if cmd.get("description"):
            g.add((cmd_uri, TS.description, Literal(cmd["description"])))
        if cmd.get("schema"):
            g.add((cmd_uri, TS.schema, Literal(json.dumps(cmd["schema"]))))
        g.add((interface_uri, TS.hasCommand, cmd_uri))

    # Instance
    inst_name = inst_data["metadata"]["name"]
    instance_uri = create_instance_uri(inst_name)

    g.add((instance_uri, RDF.type, TS.TwinInstance))
    g.add((instance_uri, TS.name, Literal(inst_name)))
    g.add((instance_uri, TS.instanceOf, interface_uri))

    ilabels = inst_data["metadata"].get("labels", {})
    if ilabels.get("generated-by"):
        g.add((instance_uri, TS.generatedBy, Literal(ilabels["generated-by"])))
    if ilabels.get("generated-at"):
        g.add((instance_uri, TS.generatedAt,
               Literal(ilabels["generated-at"], datatype=XSD.dateTime)))

    for rel in inst_data.get("spec", {}).get("twinInstanceRelationships", []):
        rel_node = BNode()
        g.add((rel_node, RDF.type, TS.InstanceRelationship))
        g.add((rel_node, TS.relationshipName, Literal(rel["name"])))
        target_uri = create_instance_uri(rel.get("instance", ""))
        g.add((rel_node, TS.targetInstance, target_uri))
        g.add((instance_uri, TS.hasInstanceRelationship, rel_node))

    return g.serialize(format="turtle")


class DebugDumpService:
    """
    Thing create akışının ürettiği formatları diske yazar.

    Her çağrı için yeni bir klasör oluşturulur:
        data/debug/<timestamp>_<thing-slug>/
            ├── 01_form_input.json          — ham form verisi (TwinCreateRequest)
            ├── 02_interface.yaml           — TwinInterface YAML
            ├── 03_instance.yaml            — TwinInstance YAML
            ├── 04_output.json              — üretilen YAML'lerin JSON temsili
            ├── 05_output.jsonld            — JSON-LD formatı
            └── 06_output.ttl               — RDF Turtle formatı
    """

    @staticmethod
    def dump(
        thing_id: str,
        form_data: Dict[str, Any],
        interface_yaml: str,
        instance_yaml: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Tüm formatları debug klasörüne yazar ve klasör yolunu döner.

        Args:
            thing_id:        Formdan gelen ham thing id (ör. "my-sensor")
            form_data:       TwinCreateRequest.model_dump() çıktısı
            interface_yaml:  Üretilen TwinInterface YAML dizgesi
            instance_yaml:   Üretilen TwinInstance YAML dizgesi
            metadata:        RDF servisine gönderilen metadata dict'i (opsiyonel)

        Returns:
            Path: Oluşturulan debug klasörünün yolu
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:-3]
        slug = _safe_slug(thing_id)
        dump_dir = _DEBUG_ROOT / f"{ts}_{slug}"
        dump_dir.mkdir(parents=True, exist_ok=True)

        errors: list[str] = []

        # 1. Ham form verisi
        try:
            form_path = dump_dir / "01_form_input.json"
            form_path.write_text(
                json.dumps(form_data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception as exc:
            errors.append(f"form_input: {exc}")

        # 2. TwinInterface YAML
        try:
            (dump_dir / "02_interface.yaml").write_text(interface_yaml, encoding="utf-8")
        except Exception as exc:
            errors.append(f"interface_yaml: {exc}")

        # 3. TwinInstance YAML
        try:
            (dump_dir / "03_instance.yaml").write_text(instance_yaml, encoding="utf-8")
        except Exception as exc:
            errors.append(f"instance_yaml: {exc}")

        # 4. JSON (YAML → parsed dict)
        try:
            iface_dict = yaml.safe_load(interface_yaml)
            inst_dict = yaml.safe_load(instance_yaml)
            combined = {
                "interface": iface_dict,
                "instance": inst_dict,
                "metadata": metadata,
            }
            (dump_dir / "04_output.json").write_text(
                json.dumps(combined, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception as exc:
            errors.append(f"output_json: {exc}")

        # 5. JSON-LD
        try:
            jsonld_doc = _build_jsonld(thing_id, interface_yaml, instance_yaml, metadata)
            (dump_dir / "05_output.jsonld").write_text(
                json.dumps(jsonld_doc, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            errors.append(f"output_jsonld: {exc}")

        # 6. RDF Turtle
        try:
            turtle = _build_rdf_turtle(interface_yaml, instance_yaml, metadata)
            (dump_dir / "06_output.ttl").write_text(turtle, encoding="utf-8")
        except Exception as exc:
            errors.append(f"output_ttl: {exc}")

        # Özet log
        if errors:
            logger.warning(
                f"[DebugDump] {dump_dir.name}: bazı formatlar yazılamadı: {errors}"
            )
        else:
            logger.info(f"[DebugDump] Debug dosyaları yazıldı: {dump_dir}")

        return dump_dir
