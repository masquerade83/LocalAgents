"""Persistent nicknames / rooms / tags for discovered devices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "registry.json"

# Seed with gear already known in this home (TOOLS.md / prior scans)
DEFAULT_REGISTRY: dict[str, dict[str, Any]] = {
    "192.168.29.1": {
        "nickname": "JioFiber Gateway",
        "room": "Network",
        "tags": ["router", "gateway"],
        "capabilities": [],
    },
    "192.168.29.221": {
        "nickname": "Camera 1",
        "room": "Home",
        "tags": ["camera", "rtsp"],
        "capabilities": ["camera.stream"],
        "links": {"rtsp_viewer": "../rtsp-viewer/"},
    },
}


def _ensure_file() -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text(json.dumps(DEFAULT_REGISTRY, indent=2) + "\n")


def load_registry() -> dict[str, dict[str, Any]]:
    _ensure_file()
    try:
        data = json.loads(REGISTRY_PATH.read_text())
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return dict(DEFAULT_REGISTRY)


def save_registry(data: dict[str, dict[str, Any]]) -> None:
    _ensure_file()
    REGISTRY_PATH.write_text(json.dumps(data, indent=2) + "\n")


def merge_registry(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reg = load_registry()
    merged: list[dict[str, Any]] = []
    for d in devices:
        meta = reg.get(d["ip"]) or reg.get(d.get("mac") or "")
        row = dict(d)
        if meta:
            row["nickname"] = meta.get("nickname") or ""
            row["room"] = meta.get("room") or ""
            row["tags"] = meta.get("tags") or []
            row["capabilities"] = meta.get("capabilities") or []
            row["links"] = meta.get("links") or {}
        else:
            row.setdefault("nickname", "")
            row.setdefault("room", "")
            row.setdefault("tags", [])
            row.setdefault("capabilities", [])
            row.setdefault("links", {})
        merged.append(row)
    return merged


def upsert_device(key: str, patch: dict[str, Any]) -> dict[str, Any]:
    reg = load_registry()
    current = dict(reg.get(key) or {})
    current.update({k: v for k, v in patch.items() if v is not None})
    reg[key] = current
    save_registry(reg)
    return current
