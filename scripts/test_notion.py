#!/usr/bin/env python3
"""Test Notion API connection. Requires NOTION_API_KEY or NOTION_TOKEN in env."""

import json
import os
import sys
import urllib.request
import urllib.error


def main():
    token = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
    if not token:
        print("FAIL: Set NOTION_API_KEY or NOTION_TOKEN (from notion.so/my-integrations)")
        return 1

    req = urllib.request.Request(
        "https://api.notion.com/v1/users/me",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            name = data.get("name") or "Integration"
            print("OK: Notion connection works")
            print(f"  Bot: {name} (id: {data.get('id', '?')})")
            return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"FAIL: {e.code} {e.reason}")
        if body:
            try:
                err = json.loads(body)
                print(f"  {err.get('message', body)}")
            except Exception:
                print(f"  {body[:200]}")
        return 1
    except Exception as e:
        print(f"FAIL: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
