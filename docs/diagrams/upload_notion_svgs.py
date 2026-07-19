#!/usr/bin/env python3
"""Upload SVG diagrams to Notion via MCP create-attachment.

Run from repo root with Cursor agent calling notion-create-attachment per file,
or invoke manually: prints JSON payloads for each SVG in .upload-cache/.

This script writes upload-manifest.json mapping diagram keys to file-upload IDs
after successful MCP uploads (append mode for batch runs).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".upload-cache"
MANIFEST = ROOT / "upload-manifest.json"


def load_payload(stem: str) -> dict:
    path = CACHE / f"{stem}.json"
    return json.loads(path.read_text())


def save_upload_id(stem: str, file_upload_id: str, markdown_source: str) -> None:
    manifest = {}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
    manifest[stem] = {
        "file_upload_id": file_upload_id,
        "markdown_source": markdown_source,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


def record(stem: str, file_upload_id: str, markdown_source: str) -> None:
    save_upload_id(stem, file_upload_id, markdown_source)
    print(f"recorded {stem} -> {markdown_source}")


def main() -> None:
    if len(sys.argv) < 2:
        stems = sorted(p.stem for p in CACHE.glob("*.json"))
        print(json.dumps({"stems": stems, "manifest": str(MANIFEST)}, indent=2))
        return

    cmd = sys.argv[1]
    if cmd == "payload" and len(sys.argv) == 3:
        print(json.dumps(load_payload(sys.argv[2])))
        return
    if cmd == "record" and len(sys.argv) == 5:
        record(sys.argv[2], sys.argv[3], sys.argv[4])
        return

    print("usage: upload_notion_svgs.py [payload STEM | record STEM ID SOURCE]", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
