#!/usr/bin/env python3
"""Create or update the Stack Health Check n8n workflow via API."""
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
NAME = "Stack Health Check (Hermes)"

if not KEY:
    print("ERROR: N8N_API_KEY not set", file=sys.stderr)
    sys.exit(1)

headers = {"X-N8N-API-KEY": KEY, "Accept": "application/json", "Content-Type": "application/json"}


def nid() -> str:
    return str(uuid.uuid4())


def build_workflow() -> dict:
    wh_id, code_id, respond_id = nid(), nid(), nid()
    js = r"""
async function probe(url, opts = {}) {
  const req = {
    method: opts.method || 'GET',
    url,
    timeout: opts.timeout || 10000,
    json: opts.json !== false,
    ignoreHttpStatusErrors: true,
  };
  if (opts.headers) req.headers = opts.headers;
  try {
    const body = await this.helpers.httpRequest(req);
    return { ok: true, body };
  } catch (e) {
    try {
      const text = await this.helpers.httpRequest({ ...req, json: false });
      return { ok: true, body: text };
    } catch (e2) {
      return { ok: false, error: String(e2) };
    }
  }
}

const litellmAuth = { Authorization: 'Bearer admin' };
const litellmHealth = await probe.call(this, 'http://host.docker.internal:4000/health/liveliness');
const litellmModelsRaw = await probe.call(this, 'http://host.docker.internal:4000/v1/models', { headers: litellmAuth });
const ollamaRaw = await probe.call(this, 'http://host.docker.internal:11434/api/tags');
const routerRaw = await probe.call(this, 'http://host.docker.internal:3999/health');
const switchRaw = await probe.call(this, 'http://host.docker.internal:9120/api/status');
const n8n = await probe.call(this, 'http://127.0.0.1:5678/healthz');

const ollamaBody = ollamaRaw.body || {};
const ollamaModels = ollamaBody.models || [];
const litellmModelsBody = litellmModelsRaw.body || {};
const litellmModelIds = (litellmModelsBody.data || []).map(m => m.id || m.model).filter(Boolean);

const switchBody = switchRaw.body || {};
const switchServices = switchBody.services || [];
const gatewaySvc = switchServices.find(s => s.name === 'gateway');
const routerSvc = switchServices.find(s => s.name === 'router');
const gatewayRunning = Boolean(gatewaySvc && gatewaySvc.running);
const routerRunning = Boolean(routerSvc && routerSvc.running);

return [{ json: {
  ok: Boolean(
    litellmHealth.ok && litellmModelsRaw.ok && ollamaRaw.ok && n8n.ok &&
    routerRaw.ok && switchRaw.ok && gatewayRunning
  ),
  timestamp: new Date().toISOString(),
  litellm: {
    health: litellmHealth.body ?? litellmHealth,
    models: {
      ok: litellmModelsRaw.ok,
      count: litellmModelIds.length,
      models: litellmModelIds.slice(0, 12),
    },
  },
  ollama: { ok: ollamaRaw.ok, model_count: ollamaModels.length, models: ollamaModels.slice(0, 8).map(m => m.name || m.model) },
  router: {
    ok: routerRaw.ok,
    health: routerRaw.body ?? routerRaw,
    running: routerRunning,
    url: 'http://host.docker.internal:3999/health',
  },
  gateway: {
    ok: gatewayRunning,
    running: gatewayRunning,
    detail: gatewaySvc ? gatewaySvc.detail : 'unknown',
    probed_via: 'hermes_switch:/api/status',
  },
  hermes_switch: { ok: switchRaw.ok, services_count: switchServices.length },
  n8n: n8n.body ?? n8n,
}}];
"""
    return {
        "name": NAME,
        "nodes": [
            {
                "parameters": {"path": "stack-health", "httpMethod": "GET", "responseMode": "responseNode"},
                "id": wh_id,
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 0],
                "webhookId": str(uuid.uuid4()),
            },
            {
                "parameters": {"jsCode": js.strip()},
                "id": code_id,
                "name": "Probe Services",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [280, 0],
            },
            {
                "parameters": {"respondWith": "json", "responseBody": "={{ $json }}"},
                "id": respond_id,
                "name": "Respond",
                "type": "n8n-nodes-base.respondToWebhook",
                "typeVersion": 1.1,
                "position": [540, 0],
            },
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Probe Services", "type": "main", "index": 0}]]},
            "Probe Services": {"main": [[{"node": "Respond", "type": "main", "index": 0}]]},
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
            wf_id = r.json().get("data", r.json()).get("id") if r.status_code < 400 else None
            if not wf_id and isinstance(r.json(), dict):
                wf_id = r.json().get("id")
        if r.status_code >= 400:
            print(f"ERROR {r.status_code}: {r.text[:800]}", file=sys.stderr)
            sys.exit(1)
        ar = client.post(f"/api/v1/workflows/{wf_id}/activate")
        print(json.dumps({
            "action": action,
            "workflow_id": wf_id,
            "name": NAME,
            "activated": ar.status_code < 400,
            "webhook_test": f"curl -s {BASE}/webhook/stack-health",
        }, indent=2))


if __name__ == "__main__":
    main()
