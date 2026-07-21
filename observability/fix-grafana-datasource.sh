#!/usr/bin/env bash
# Fix Grafana Prometheus datasource UID mismatch (panels use uid=prometheus).
set -euo pipefail

GRAFANA="${GRAFANA_URL:-http://127.0.0.1:3000}"
AUTH="admin:admin"

echo "Fixing Grafana datasource UID → prometheus ..."

# Delete auto-generated datasource if wrong UID
export GRAFANA AUTH
export DS_JSON="$(curl -sf -u "$AUTH" "$GRAFANA/api/datasources")"
python3 <<'PY'
import json, os, sys, urllib.request
auth = os.environ.get("AUTH", "admin:admin").encode()
base = os.environ.get("GRAFANA", "http://127.0.0.1:3000")
for ds in json.loads(os.environ["DS_JSON"]):
    if ds.get("type") != "prometheus":
        continue
    if ds.get("uid") == "prometheus":
        print("Hermes datasource uid=prometheus is present")
        extras = [
            d for d in json.loads(os.environ["DS_JSON"])
            if d.get("type") == "prometheus" and d.get("uid") != "prometheus"
        ]
        if extras:
            print(
                f"Note: {len(extras)} legacy Prometheus datasource(s) remain read-only "
                "(safe to ignore; dashboards use uid=prometheus)"
            )
        sys.exit(0)
    if ds.get("readOnly"):
        print(f"Skip read-only datasource id={ds['id']} uid={ds.get('uid')}")
        continue
    req = urllib.request.Request(
        f"{base}/api/datasources/{ds['id']}",
        method="DELETE",
        headers={"Authorization": "Basic " + __import__("base64").b64encode(auth).decode()},
    )
    urllib.request.urlopen(req)
    print(f"Deleted old datasource id={ds['id']} uid={ds.get('uid')}")
PY

# Recreate via provisioning — restart Grafana
ROOT="$(cd "$(dirname "$0")" && pwd)"
docker compose -f "$ROOT/docker-compose.yml" restart grafana
sleep 4

uid=$(curl -sf -u "$AUTH" "$GRAFANA/api/datasources" | python3 -c "import sys,json; ds=json.load(sys.stdin); print(next((d['uid'] for d in ds if d.get('uid')=='prometheus'), 'NONE'))")
echo "Hermes datasource uid: $uid"
echo "Open: $GRAFANA/d/hermes-stack-overview/hermes-stack-overview"
