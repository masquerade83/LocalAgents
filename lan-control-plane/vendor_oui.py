"""Vendor / ISP classification for LAN devices via MAC OUI + hostname hints.

Focus: distinguish ISP CPE (Jio vs Airtel) from client devices, and flag
MAC-randomised (privacy) addresses so we don't mislabel phones as gear.
"""

from __future__ import annotations

from typing import Any

# Curated OUI → vendor/ISP. Extend as more gear is seen on this LAN.
# (Only high-confidence entries; unknown OUIs are reported as such.)
OUI_VENDOR: dict[str, dict[str, str]] = {
    "a8:88:1f": {"vendor": "Reliance Jio", "isp": "Jio", "kind": "isp-cpe"},
    "ac:f8:cc": {"vendor": "Reliance Jio", "isp": "Jio", "kind": "isp-cpe"},
    "6c:99:89": {"vendor": "Reliance Jio", "isp": "Jio", "kind": "isp-cpe"},
    # Airtel Xstream / Bharti CPE commonly ships on these ODM OUIs:
    "44:d1:fa": {"vendor": "Shenzhen (Airtel CPE ODM)", "isp": "Airtel", "kind": "isp-cpe"},
    "d8:47:32": {"vendor": "TP-Link (Airtel-branded)", "isp": "Airtel", "kind": "isp-cpe"},
    "10:be:f5": {"vendor": "D-Link (Airtel-branded)", "isp": "Airtel", "kind": "isp-cpe"},
    "b0:be:76": {"vendor": "TP-Link (Airtel-branded)", "isp": "Airtel", "kind": "isp-cpe"},
}

# Substrings in reverse-DNS / hostname that reveal the ISP.
HOSTNAME_ISP = [
    ("reliance", "Jio"),
    ("jio", "Jio"),
    ("airtel", "Airtel"),
    ("bharti", "Airtel"),
]


def _is_randomized(mac: str) -> bool:
    """Locally-administered bit set => randomized/private MAC (usually a phone)."""
    if not mac or ":" not in mac:
        return False
    try:
        first = int(mac.split(":")[0], 16)
    except ValueError:
        return False
    return bool(first & 0b10)  # bit 1 of the first octet


def classify(device: dict[str, Any]) -> dict[str, Any]:
    mac = (device.get("mac") or "").lower()
    host = (device.get("hostname") or "").lower()
    oui = mac[:8]

    isp = ""
    vendor = device.get("vendor") or ""
    kind = "client"

    hit = OUI_VENDOR.get(oui)
    if hit:
        vendor = hit["vendor"]
        isp = hit["isp"]
        kind = hit["kind"]

    for needle, name in HOSTNAME_ISP:
        if needle in host:
            isp = isp or name
            if device.get("is_gateway"):
                kind = "isp-cpe"

    randomized = _is_randomized(mac)
    if randomized and not hit:
        vendor = vendor or "randomized MAC (private)"
        kind = "client (MAC-randomised)"

    if device.get("is_gateway") and not isp:
        isp = "unknown ISP"
        kind = "isp-cpe"

    return {
        "vendor": vendor or "unknown",
        "isp": isp or "",
        "kind": kind,
        "mac_randomized": randomized,
    }


def classify_all(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for d in devices:
        row = dict(d)
        row.update(classify(d))
        out.append(row)
    return out
