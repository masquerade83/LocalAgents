#!/usr/bin/env python3
"""Print MCP create-attachment args one stem at a time (for agent batch upload).

Usage:
  python3 mcp_upload_all.py list          # stems not yet in manifest upload IDs
  python3 mcp_upload_all.py next          # print next stem to upload
  python3 mcp_upload_all.py args STEM     # write args JSON to stdout (may be large)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".upload-cache"
MANIFEST = ROOT / "upload-manifest.json"


def load_manifest() -> dict:
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text())


def pending_stems() -> list[str]:
    manifest = load_manifest()
    done = {k for k, v in manifest.items() if isinstance(v, dict) and v.get("file_upload_id")}
    return sorted(p.stem for p in CACHE.glob("*.json") if p.stem not in done)


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: mcp_upload_all.py [list|next|args STEM]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list":
        print(json.dumps(pending_stems(), indent=2))
        return
    if cmd == "next":
        stems = pending_stems()
        print(stems[0] if stems else "")
        return
    if cmd == "args" and len(sys.argv) == 3:
        stem = sys.argv[2]
        payload = json.loads((CACHE / f"{stem}.json").read_text())
        args = {
            "filename": payload["filename"],
            "content_type": payload.get("content_type", "image/svg+xml"),
            "content": payload["content"],
        }
        sys.stdout.write(json.dumps(args))
        return

    print("usage: mcp_upload_all.py [list|next|args STEM]", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
