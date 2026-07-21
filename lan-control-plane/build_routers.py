#!/usr/bin/env python3
"""Classify LAN devices by vendor/ISP (Jio vs Airtel vs client) and attach the
gateway default-login self-audit. Writes data/routers.json for the browser view.
"""

from __future__ import annotations

import json
from pathlib import Path

from discovery import scan_network, DEFAULT_GATEWAY
from registry import merge_registry
from fingerprint import fingerprint_all
from vendor_oui import classify_all
from router_audit import audit_gateway

DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> int:
    scan = scan_network(ping_sweep=True)
    scan["devices"] = merge_registry(scan["devices"])
    scan["devices"] = fingerprint_all(scan["devices"])
    scan["devices"] = classify_all(scan["devices"])

    routers = [d for d in scan["devices"] if d.get("kind") == "isp-cpe" or d.get("is_gateway")]

    audit = audit_gateway(
        DEFAULT_GATEWAY,
        next((r.get("isp") for r in routers if r.get("is_gateway")), "generic") or "generic",
        authorized=True,
        ownership_ack="i own these devices",
    )
    for r in routers:
        if r.get("is_gateway"):
            r["audit"] = audit

    by_isp: dict[str, int] = {}
    for d in scan["devices"]:
        isp = d.get("isp") or "—"
        by_isp[isp] = by_isp.get(isp, 0) + 1

    result = {
        "scanned_at": scan["scanned_at"],
        "subnet": scan["subnet"],
        "total_devices": scan["count"],
        "isp_breakdown": by_isp,
        "routers": [
            {
                "ip": r["ip"],
                "mac": r.get("mac", ""),
                "hostname": r.get("hostname", ""),
                "nickname": r.get("nickname", ""),
                "vendor": r.get("vendor", ""),
                "isp": r.get("isp", ""),
                "kind": r.get("kind", ""),
                "open_ports": r.get("open_ports", []),
                "audit": r.get("audit"),
            }
            for r in routers
        ],
        "note": "Only the gateway you administer is login-tested. Nearby Wi-Fi APs "
                "cannot be labelled Jio/Airtel or login-tested: macOS redacts their "
                "SSID/BSSID and they are not on your network.",
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "routers.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
