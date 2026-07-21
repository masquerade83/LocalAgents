#!/usr/bin/env python3
"""Scan nearby Wi-Fi access points (routers) and score their SECURITY POSTURE.

Ethics/scope:
- Read-only RF observation via macOS `system_profiler SPAirPortDataType`.
- We do NOT retrieve or crack any network's password. "Scoring" here rates the
  observable security posture (encryption scheme, signal, band) of each AP.
- macOS redacts SSIDs/BSSIDs unless the calling process has Location permission,
  so networks are labelled AP-1, AP-2… That's intentional and fine.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
SWIFT_SCANNER = Path(__file__).resolve().parent / "wifi_corewlan.swift"

# SSID name-pattern → ISP. Only meaningful once macOS unredacts SSIDs
# (requires Location permission). Observation only — never used for access.
import re as _re
ISP_SSID_PATTERNS: list[tuple[str, str]] = [
    (r"jio", "Jio"),
    (r"airtel|xstream", "Airtel"),
    (r"\bBSNL\b", "BSNL"),
    (r"\bACT\b|actfibernet", "ACT"),
    (r"excitel", "Excitel"),
    (r"hathway", "Hathway"),
    (r"tata|t-fiber", "Tata Play"),
]


def isp_from_ssid(ssid: str) -> str:
    if not ssid or ssid == "<redacted>":
        return ""
    for pat, name in ISP_SSID_PATTERNS:
        if _re.search(pat, ssid, _re.IGNORECASE):
            return name
    return ""


# How each encryption scheme rates as a security posture (0-100, higher=safer).
SECURITY_SCORE = {
    "None": (5, "critical", "Open network — no encryption, anyone can read traffic"),
    "WEP": (10, "critical", "WEP is trivially crackable in minutes"),
    "WPA Personal": (45, "weak", "WPA (TKIP) is deprecated and attackable"),
    "WPA/WPA2 Personal": (60, "moderate", "Mixed mode allows downgrade to weak WPA"),
    "WPA2 Personal": (78, "good", "WPA2-AES — solid; ensure a strong passphrase"),
    "WPA2/WPA3 Personal": (88, "good", "Transition mode — strong, WPA3 where supported"),
    "WPA3 Personal": (95, "strong", "WPA3-SAE — resistant to offline guessing"),
    "WPA2 Enterprise": (90, "strong", "802.1X enterprise auth"),
    "WPA3 Enterprise": (97, "strong", "802.1X + WPA3"),
}


def _signal_bar(rssi: int | None) -> str:
    if rssi is None:
        return "unknown"
    if rssi >= -55:
        return "excellent"
    if rssi >= -67:
        return "good"
    if rssi >= -75:
        return "fair"
    return "weak"


def parse_airport() -> dict[str, Any]:
    out = subprocess.check_output(
        ["system_profiler", "SPAirPortDataType"], text=True, stderr=subprocess.DEVNULL
    )
    lines = out.splitlines()

    aps: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    section = None  # 'current' | 'other'

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if stripped.startswith("Current Network Information"):
            section = "current"
            continue
        if stripped.startswith("Other Local Wi-Fi Networks"):
            section = "other"
            continue
        if stripped.startswith("awdl0") or stripped.startswith("Supported Channels"):
            section = None

        if section is None:
            continue

        # A network name header is an indented "Name:" with no value after colon,
        # at the shallow indent used for network entries (14 spaces in profiler).
        if stripped.endswith(":") and indent in (12, 14) and ":" not in stripped[:-1].strip()[:0] + "":
            # start a new AP
            name = stripped[:-1]
            if name in ("Current Network Information", "Other Local Wi-Fi Networks"):
                continue
            cur = {
                "ssid_observed": name,  # usually "<redacted>" without Location perm
                "connected": section == "current",
                "phy": "",
                "channel": "",
                "band": "",
                "security": "",
                "rssi": None,
                "noise": None,
            }
            aps.append(cur)
            continue

        if cur is None:
            continue

        if stripped.startswith("PHY Mode:"):
            cur["phy"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Channel:"):
            val = stripped.split(":", 1)[1].strip()
            cur["channel"] = val
            m = re.search(r"\((\d?GHz)", val)
            if m:
                cur["band"] = m.group(1)
        elif stripped.startswith("Security:"):
            cur["security"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Signal / Noise:"):
            m = re.findall(r"(-?\d+)\s*dBm", stripped)
            if len(m) >= 1:
                cur["rssi"] = int(m[0])
            if len(m) >= 2:
                cur["noise"] = int(m[1])

    # De-dupe placeholder headers with no security captured
    aps = [a for a in aps if a.get("security")]
    return {"count": len(aps), "aps": aps}


def scan_corewlan() -> dict[str, Any] | None:
    """Preferred source: CoreWLAN via a Swift helper — returns real SSIDs.

    Requires the calling app (Terminal/iTerm/Cursor) to hold Location permission.
    Returns None if swift/the helper is unavailable or yields nothing usable.
    """
    if not SWIFT_SCANNER.exists():
        return None
    try:
        out = subprocess.check_output(
            ["swift", str(SWIFT_SCANNER)], text=True, stderr=subprocess.DEVNULL, timeout=40
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None

    aps: list[dict[str, Any]] = []
    for n in data.get("networks", []):
        ssid = n.get("ssid") or ""
        chan = n.get("channel") or 0
        band = n.get("band") or ""
        aps.append(
            {
                "ssid_observed": ssid if ssid and ssid != "<hidden>" else "<hidden>",
                "connected": bool(n.get("connected")),
                "phy": "",
                "channel": f"{chan} ({band})" if chan else "",
                "band": band,
                "security": n.get("security") or "",
                "rssi": n.get("rssi") if n.get("rssi") not in (0, None) else None,
                "noise": n.get("noise") if n.get("noise") not in (0, None) else None,
            }
        )
    # De-dupe APs that broadcast the same SSID on multiple radios; keep strongest.
    best: dict[str, dict[str, Any]] = {}
    for ap in aps:
        key = f"{ap['ssid_observed']}|{ap['band']}"
        cur = best.get(key)
        if cur is None or (ap["rssi"] or -200) > (cur["rssi"] or -200):
            best[key] = ap
    deduped = list(best.values())
    if not deduped:
        return None
    return {"count": len(deduped), "aps": deduped, "source": "corewlan"}


def score_aps(scan: dict[str, Any]) -> dict[str, Any]:
    scored = []
    for i, ap in enumerate(scan["aps"], 1):
        sec = ap.get("security", "").strip()
        score, level, why = SECURITY_SCORE.get(sec, (50, "unknown", f"Unrecognised scheme: {sec}"))
        scored.append(
            {
                "label": f"AP-{i}",
                "ssid": ap["ssid_observed"],
                "isp": isp_from_ssid(ap["ssid_observed"]),
                "connected": ap["connected"],
                "band": ap.get("band", ""),
                "channel": ap.get("channel", ""),
                "phy": ap.get("phy", ""),
                "security": sec,
                "rssi": ap.get("rssi"),
                "signal_quality": _signal_bar(ap.get("rssi")),
                "posture_score": score,
                "posture_level": level,
                "posture_note": why,
            }
        )
    scored.sort(key=lambda a: (a["posture_score"], -(a["rssi"] or -100)))
    return {
        "scanned_at": _now(),
        "count": len(scored),
        "location_unredacted": any(a["ssid"] not in ("<redacted>", "<hidden>", "") for a in scored),
        "source": scan.get("source", "system_profiler"),
        "note": "Observation only: names, encryption scheme, signal. Posture score reflects "
                "the encryption scheme — not any password; no network is accessed or joined. "
                "SSIDs require Location permission for the scanning app; if a name shows as "
                "'<hidden>' the AP is not broadcasting it.",
        "networks": scored,
    }


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def save(result: dict[str, Any]) -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = DATA_DIR / "wifi.json"
    p.write_text(json.dumps(result, indent=2) + "\n")
    return str(p)


if __name__ == "__main__":
    # Prefer CoreWLAN (real SSIDs when Location is granted); fall back to system_profiler.
    scan = scan_corewlan() or parse_airport()
    result = score_aps(scan)
    path = save(result)
    print(json.dumps(result, indent=2))
    print(f"\nsource={result.get('source')} unredacted={result.get('location_unredacted')}")
    print(f"saved -> {path}", flush=True)
