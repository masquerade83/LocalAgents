#!/usr/bin/env python3
"""Build the Wi-Fi/LAN device knowledge graph.

Pipeline:  discover -> fingerprint -> graph -> (optional) credential self-audit -> export

Examples:
  python build_kg.py                      # discover + fingerprint + graph
  python build_kg.py --no-fingerprint     # discovery only (fastest, most passive)
  python build_kg.py --audit-defaults --own   # also check factory-default logins (own devices)
"""

from __future__ import annotations

import argparse
import json
import sys

from discovery import scan_network
from registry import merge_registry
from fingerprint import fingerprint_all
from knowledge_graph import build_graph, save_graph
from credential_audit import check_default_credentials


def main() -> int:
    ap = argparse.ArgumentParser(description="Build LAN device knowledge graph")
    ap.add_argument("--no-ping", action="store_true", help="skip ping sweep (ARP only)")
    ap.add_argument("--no-fingerprint", action="store_true", help="skip port/service scan")
    ap.add_argument("--audit-defaults", action="store_true",
                    help="check devices for surviving factory-default logins")
    ap.add_argument("--own", action="store_true",
                    help="assert you own/administer every device on this LAN (required for --audit-defaults)")
    args = ap.parse_args()

    print("• Discovering devices…", file=sys.stderr)
    scan = scan_network(ping_sweep=not args.no_ping)
    scan["devices"] = merge_registry(scan["devices"])
    print(f"  found {scan['count']} devices", file=sys.stderr)

    if not args.no_fingerprint:
        print("• Fingerprinting services…", file=sys.stderr)
        scan["devices"] = fingerprint_all(scan["devices"])

    if args.audit_defaults:
        if not args.own:
            print("  ! --audit-defaults requires --own (ownership assertion). Skipping audit.",
                  file=sys.stderr)
        else:
            print("• Checking factory-default logins (authorized self-audit)…", file=sys.stderr)
            for dev in scan["devices"]:
                finding = check_default_credentials(
                    dev, authorized=True, ownership_ack="I own these devices"
                )
                if not finding.get("skipped"):
                    dev.setdefault("findings", []).append(finding)

    print("• Building knowledge graph…", file=sys.stderr)
    graph = build_graph(scan)
    paths = save_graph(graph)

    print(json.dumps(
        {
            "devices": scan["count"],
            "nodes": graph["node_count"],
            "edges": graph["edge_count"],
            "exports": paths,
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
