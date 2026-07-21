#!/usr/bin/env python3
"""Create or update n8n cron workflow: stack-observe alerts every 15 minutes."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path.home() / ".config" / "n8n-mcp" / "env")
load_dotenv(Path.home() / ".hermes" / ".env")

BASE = os.getenv("N8N_BASE_URL", "http://127.0.0.1:5678").rstrip("/")
KEY = os.getenv("N8N_API_KEY", "")
NAME = "Hermes Observe Alert (cron)"
CLAWD = Path(__file__).resolve().parent.parent
ALERT_SCRIPT = CLAWD / "scripts" / "stack-observe-alert.sh"

if not KEY:
    print("ERROR: N8N_API_KEY not set", file=sys.stderr)
    sys.exit(1)

headers = {"X-N8N-API-KEY": KEY, "Accept": "application/json", "Content-Type": "application/json"}


def nid() -> str:
    return str(uuid.uuid4())


def build_workflow() -> dict:
    cron_id, exec_id, if_id, respond_id = nid(), nid(), nid(), nid()
    cmd = f"bash {ALERT_SCRIPT}"
    js_if = """
const alerts = JSON.parse($json.stdout || '{}');
return alerts.alerts && alerts.alerts.length ? [{ json: alerts }] : [];
"""
    return {
        "name": NAME,
        "nodes": [
            {
                "parameters": {"rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}},
                "id": cron_id,
                "name": "Every 15 min",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 0],
            },
            {
                "parameters": {"command": cmd},
                "id": exec_id,
                "name": "Run stack-observe-alert",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [260, 0],
            },
            {
                "parameters": {"jsCode": js_if.strip()},
                "id": if_id,
                "name": "Has alerts",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [520, 0],
            },
            {
                "parameters": {
                    "respondWith": "json",
                    "responseBody": "={{ $json }}",
                },
                "id": respond_id,
                "name": "Log alerts",
                "type": "n8n-nodes-base.noOp",
                "typeVersion": 1,
                "position": [780, 0],
            },
        ],
        "connections": {
            "Every 15 min": {"main": [[{"node": "Run stack-observe-alert", "type": "main", "index": 0}]]},
            "Run stack-observe-alert": {"main": [[{"node": "Has alerts", "type": "main", "index": 0}]]},
            "Has alerts": {"main": [[{"node": "Log alerts", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


def find_existing(client: httpx.Client) -> str | None:
    r = client.get("/api/v1/workflows", params={"limit": 250})
    r.raise_for_status()
    for wf in r.json().get("data", []):
        if wf.get("name") == NAME:
            return wf["id"]
    return None


def main() -> None:
    if not ALERT_SCRIPT.is_file():
        print(f"ERROR: missing {ALERT_SCRIPT}", file=sys.stderr)
        sys.exit(1)
    body = build_workflow()
    with httpx.Client(base_url=BASE, headers=headers, timeout=30) as client:
        existing = find_existing(client)
        if existing:
            r = client.put(f"/api/v1/workflows/{existing}", json=body)
            action = "updated"
            wf_id = existing
        else:
            r = client.post("/api/v1/workflows", json=body)
            action = "created"
            wf_id = r.json().get("id") or (r.json().get("data") or {}).get("id")
        if r.status_code >= 400:
            print(f"ERROR {r.status_code}: {r.text[:800]}", file=sys.stderr)
            sys.exit(1)
        ar = client.post(f"/api/v1/workflows/{wf_id}/activate")
        print(json.dumps({"action": action, "workflow_id": wf_id, "activated": ar.status_code < 400}, indent=2))


if __name__ == "__main__":
    main()
