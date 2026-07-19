#!/usr/bin/env python3
"""Upload all cached SVGs to Notion via MCP create-attachment using stdio bridge.

Reads args from docs/diagrams/.mcp-args/*.json and prints upload results.
This script is meant to be run by an agent that calls notion-create-attachment
per file; it records results in upload-manifest.json.

Subcommand `invoke-via-cursor` is a placeholder — use MCP tool directly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARGS_DIR = ROOT / ".mcp-args"
MANIFEST = ROOT / "upload-manifest.json"


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


def record_upload(stem: str, response: dict) -> None:
    manifest = load_manifest()
    entry = manifest.get(stem, {})
    if not isinstance(entry, dict):
        entry = {"filename": f"{stem}.svg"}
    entry["file_upload_id"] = response.get("file_upload_id") or response.get("id")
    entry["markdown_source"] = response.get("markdown_source") or response.get("markdown")
    manifest[stem] = entry
    save_manifest(manifest)
    print(json.dumps({"stem": stem, "recorded": entry.get("markdown_source")}))


def list_pending() -> list[str]:
    manifest = load_manifest()
    done = {
        k
        for k, v in manifest.items()
        if isinstance(v, dict) and v.get("markdown_source")
    }
    return sorted(p.stem for p in ARGS_DIR.glob("*.json") if p.stem not in done)


def get_args(stem: str) -> dict:
    return json.loads((ARGS_DIR / f"{stem}.json").read_text())


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: notion_batch_upload.py [pending|args STEM|record STEM JSON]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "pending":
        print(json.dumps(list_pending(), indent=2))
        return
    if cmd == "args" and len(sys.argv) == 3:
        sys.stdout.write(json.dumps(get_args(sys.argv[2])))
        return
    if cmd == "record" and len(sys.argv) == 4:
        record_upload(sys.argv[2], json.loads(sys.argv[3]))
        return

    print("usage: notion_batch_upload.py [pending|args STEM|record STEM JSON]", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
