"""Authorized self-audit of credential hygiene for devices YOU own.

Two capabilities, both defensive:

1. score_password() / audit_known_passwords()
   Pure-local password-strength scoring (entropy, length, charset, common-list,
   keyboard/sequence patterns). No network activity. Use this to document how
   strong the passwords you already set on your devices are.

2. check_default_credentials()
   Checks whether a device's HTTP login STILL accepts well-known factory-default
   credentials (e.g. admin/admin). Leaving factory defaults is the #1 IoT risk,
   so this flags "still on defaults" devices so you can change them.

SAFETY GUARDRAILS (do not remove):
- Only runs against RFC1918 (private) addresses.
- Requires explicit authorized=True AND an ownership acknowledgement.
- Uses a TINY curated list of *published vendor defaults* only. It is NOT a
  brute-force / dictionary cracker and must not be turned into one.
- One attempt per known default pair, stops on first hit, small delay between
  tries to avoid locking out or stressing the device.
- Never stores or logs any password it discovers beyond the local finding.
"""

from __future__ import annotations

import base64
import math
import re
import socket
import time
import ipaddress
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# --- Published vendor default credentials (well-known, public knowledge) ---
# Kept intentionally small: this documents "still on factory defaults", it is
# not a password cracker.
DEFAULT_CREDS: list[tuple[str, str]] = [
    ("admin", "admin"),
    ("admin", "password"),
    ("admin", ""),
    ("admin", "1234"),
    ("admin", "12345"),
    ("admin", "admin123"),
    ("root", "root"),
    ("root", "admin"),
    ("user", "user"),
    ("admin", "jiofiber"),  # common ISP CPE default
]

COMMON_PASSWORDS = {
    "password", "123456", "12345678", "qwerty", "admin", "welcome",
    "letmein", "iloveyou", "1234567890", "abc123", "111111", "000000",
    "password1", "admin123", "changeme", "jiofiber", "reliance",
}

_KEYBOARD_RUNS = ["qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890"]


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


# --------------------------- password strength ---------------------------

def score_password(pw: str) -> dict[str, Any]:
    """Return a strength report for a single password (local only)."""
    if pw is None:
        pw = ""
    length = len(pw)
    classes = {
        "lower": bool(re.search(r"[a-z]", pw)),
        "upper": bool(re.search(r"[A-Z]", pw)),
        "digit": bool(re.search(r"\d", pw)),
        "symbol": bool(re.search(r"[^A-Za-z0-9]", pw)),
    }
    pool = 0
    if classes["lower"]:
        pool += 26
    if classes["upper"]:
        pool += 26
    if classes["digit"]:
        pool += 10
    if classes["symbol"]:
        pool += 33
    entropy_bits = round(length * math.log2(pool), 1) if pool else 0.0

    warnings: list[str] = []
    low = pw.lower()
    if low in COMMON_PASSWORDS:
        warnings.append("appears in common-password list")
    if length < 8:
        warnings.append("shorter than 8 characters")
    if pw and len(set(pw)) <= 2:
        warnings.append("very low character variety")
    if re.search(r"(.)\1{2,}", pw):
        warnings.append("contains repeated characters")
    for run in _KEYBOARD_RUNS:
        if len(pw) >= 4 and (low in run or low[::-1] in run):
            warnings.append("keyboard/sequential pattern")
            break
    if re.fullmatch(r"\d+", pw or "x"):
        warnings.append("digits only")

    if warnings or entropy_bits < 28:
        rating = "very weak"
    elif entropy_bits < 36:
        rating = "weak"
    elif entropy_bits < 60:
        rating = "moderate"
    elif entropy_bits < 80:
        rating = "strong"
    else:
        rating = "very strong"

    return {
        "length": length,
        "char_classes": [k for k, v in classes.items() if v],
        "entropy_bits": entropy_bits,
        "rating": rating,
        "warnings": warnings,
    }


def audit_known_passwords(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """entries: [{'ip' or 'device', 'label', 'password'}]. Never stores the raw pw."""
    out = []
    for e in entries:
        report = score_password(e.get("password", ""))
        out.append(
            {
                "device": e.get("ip") or e.get("device") or "?",
                "label": e.get("label", ""),
                **report,
            }
        )
    return out


# --------------------------- default-cred check ---------------------------

def _try_http_basic(ip: str, port: int, tls: bool, user: str, pw: str,
                    timeout: float = 2.5) -> int | None:
    scheme = "https" if tls else "http"
    url = f"{scheme}://{ip}:{port}/"
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    req = Request(url, headers={"Authorization": f"Basic {token}",
                                "User-Agent": "lan-self-audit"})
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urlopen(req, timeout=timeout, context=ctx if tls else None) as resp:
            return resp.status
    except HTTPError as e:
        return e.code
    except (URLError, socket.timeout, OSError, ValueError):
        return None


def check_default_credentials(
    device: dict[str, Any],
    *,
    authorized: bool = False,
    ownership_ack: str = "",
    delay_s: float = 0.7,
) -> dict[str, Any]:
    """Check ONE device's HTTP login for surviving factory-default creds.

    Requires authorized=True and ownership_ack == 'I own these devices'.
    Returns a finding describing whether defaults still work (weak) or not.
    """
    ip = device["ip"]
    if not authorized or ownership_ack.strip().lower() != "i own these devices":
        return {"skipped": True, "reason": "not authorized (needs explicit ownership ack)"}
    if not _is_private(ip):
        return {"skipped": True, "reason": "refusing non-private address"}

    ports = device.get("login_surface") or []
    http_targets = [(p, p in (443, 8443)) for p in ports if p in (80, 443, 8080, 8000, 8443, 5000, 9000)]
    if not http_targets:
        return {"skipped": True, "reason": "no HTTP login surface"}

    tested = 0
    for port, tls in http_targets:
        # Only probe defaults when the endpoint actually challenges for auth.
        first = _try_http_basic(ip, port, tls, "x-none", "x-none")
        if first != 401:
            continue  # not HTTP-Basic protected; skip (avoids blind guessing)
        for user, pw in DEFAULT_CREDS:
            tested += 1
            status = _try_http_basic(ip, port, tls, user, pw)
            time.sleep(delay_s)
            if status in (200, 301, 302):
                return {
                    "id": "default-credentials",
                    "severity": "high",
                    "port": port,
                    "detail": f"factory-default login accepted on :{port} "
                              f"(user='{user}', pw hidden) — change immediately",
                    "attempts": tested,
                }
    return {
        "id": "default-credentials",
        "severity": "ok",
        "detail": f"no published default credentials accepted ({tested} pairs tried)",
        "attempts": tested,
    }
