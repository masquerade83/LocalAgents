"""Build a knowledge graph of discoverable Wi-Fi/LAN devices.

Nodes:  Network, Device, Service, Vendor, Finding
Edges:  (Network)-[:HAS_DEVICE]->(Device)
        (Device)-[:CONNECTS_TO]->(Network gateway)
        (Device)-[:EXPOSES]->(Service)
        (Device)-[:MADE_BY]->(Vendor)
        (Device)-[:HAS_FINDING]->(Finding)

Exports both a portable JSON graph and Neo4j-ready Cypher.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"


def _node(node_id: str, label: str, props: dict[str, Any]) -> dict[str, Any]:
    return {"id": node_id, "label": label, "props": props}


def build_graph(scan: dict[str, Any]) -> dict[str, Any]:
    """Turn an (optionally fingerprinted) scan payload into a graph."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_vendors: set[str] = set()

    subnet = scan.get("subnet", "unknown")
    gateway = scan.get("gateway", "")
    net_id = f"net:{subnet}"
    nodes.append(
        _node(
            net_id,
            "Network",
            {"subnet": subnet, "gateway": gateway, "scanned_at": scan.get("scanned_at")},
        )
    )

    for dev in scan.get("devices", []):
        ip = dev["ip"]
        dev_id = f"dev:{ip}"
        nodes.append(
            _node(
                dev_id,
                "Device",
                {
                    "ip": ip,
                    "mac": dev.get("mac", ""),
                    "hostname": dev.get("hostname", ""),
                    "nickname": dev.get("nickname", ""),
                    "room": dev.get("room", ""),
                    "device_type": dev.get("device_type", "unknown"),
                    "online": dev.get("online", False),
                    "is_gateway": dev.get("is_gateway", False),
                    "open_ports": dev.get("open_ports", []),
                    "login_surface": dev.get("login_surface", []),
                    "tags": dev.get("tags", []),
                },
            )
        )
        edges.append({"from": net_id, "to": dev_id, "type": "HAS_DEVICE"})
        if gateway and ip != gateway:
            edges.append({"from": dev_id, "to": f"dev:{gateway}", "type": "CONNECTS_TO"})

        vendor = (dev.get("vendor") or "").strip()
        if vendor:
            vid = f"vendor:{vendor.lower()}"
            if vendor.lower() not in seen_vendors:
                nodes.append(_node(vid, "Vendor", {"name": vendor}))
                seen_vendors.add(vendor.lower())
            edges.append({"from": dev_id, "to": vid, "type": "MADE_BY"})

        for port, svc in (dev.get("services") or {}).items():
            svc_id = f"svc:{ip}:{port}"
            nodes.append(
                _node(
                    svc_id,
                    "Service",
                    {
                        "port": int(port),
                        "service": svc.get("service", ""),
                        "title": svc.get("title", ""),
                        "server": svc.get("server", ""),
                        "auth_scheme": svc.get("auth_scheme", ""),
                        "banner": svc.get("banner", ""),
                    },
                )
            )
            edges.append({"from": dev_id, "to": svc_id, "type": "EXPOSES"})

        for finding in dev.get("findings", []):
            fid = f"finding:{ip}:{finding.get('id','x')}"
            nodes.append(_node(fid, "Finding", dict(finding)))
            edges.append({"from": dev_id, "to": fid, "type": "HAS_FINDING"})

    return {
        "generated_from": scan.get("scanned_at"),
        "subnet": subnet,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def _cy_props(props: dict[str, Any]) -> str:
    parts = []
    for k, v in props.items():
        if v is None or v == "":
            continue
        parts.append(f"{k}: {json.dumps(v)}")
    return "{" + ", ".join(parts) + "}"


def to_cypher(graph: dict[str, Any]) -> str:
    """Neo4j import script (idempotent via MERGE)."""
    lines = ["// Auto-generated LAN knowledge graph", "// Run in Neo4j Browser or cypher-shell", ""]
    for n in graph["nodes"]:
        props = dict(n["props"])
        props["id"] = n["id"]
        lines.append(f"MERGE (n:{n['label']} {{id: {json.dumps(n['id'])}}}) SET n += {_cy_props(props)};")
    lines.append("")
    for e in graph["edges"]:
        lines.append(
            f"MATCH (a {{id: {json.dumps(e['from'])}}}), (b {{id: {json.dumps(e['to'])}}}) "
            f"MERGE (a)-[:{e['type']}]->(b);"
        )
    return "\n".join(lines) + "\n"


def save_graph(graph: dict[str, Any]) -> dict[str, str]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "graph.json"
    cypher_path = DATA_DIR / "graph.cypher"
    json_path.write_text(json.dumps(graph, indent=2) + "\n")
    cypher_path.write_text(to_cypher(graph))
    return {"json": str(json_path), "cypher": str(cypher_path)}
