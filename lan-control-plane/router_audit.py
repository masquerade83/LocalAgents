#!/usr/bin/env python3
"""Default-login self-audit for the *owned* ISP gateway on this LAN.

Purpose: demonstrate whether the home router still accepts factory-default
web-admin credentials (a top security risk) so weak ones can be fixed.

HARD SCOPE:
- Runs ONLY against the LAN gateway (the device you administer).
- Requires authorized=True AND ownership_ack == 'i own these devices'.
- Tiny curated list of *published vendor defaults* — NOT a brute-forcer.
- Small attempt cap + delay to avoid any lockout on the gateway.
- Never stores a discovered password; reports only which pair succeeded.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import ipaddress
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"

# Published defaults for common Indian ISP CPE (public knowledge).
DEFAULTS_BY_ISP: dict[str, list[tuple[str, str]]] = {
    "Jio": [("admin", "admin"), ("administrator", "admin"), ("admin", "Ji0@fiber")],
    "Airtel": [("admin", "admin"), ("admin", "password"), ("admin", "Airtel@123")],
    "generic": [("admin", "admin"), ("admin", "password"), ("admin", "")],
}

MAX_ATTEMPTS = 4
DELAY_S = 1.6


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def _fetch(url: str, timeout: float = 6.0) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "lan-self-audit"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(20000).decode("latin-1", "ignore")
        return r.status, body, dict(r.headers)


def _discover_form(base: str) -> dict[str, Any] | None:
    """Parse the login page: form action + username/password field names."""
    try:
        _, html, _ = _fetch(base + "/")
    except Exception:
        return None
    if "type=\"password\"" not in html.lower() and "type='password'" not in html.lower():
        return None
    action = re.search(r'<form[^>]*action="([^"]+)"', html, re.IGNORECASE)
    user_f = re.search(r'name="([^"]*user[^"]*)"', html, re.IGNORECASE)
    pass_f = re.search(r'name="([^"]*pass[^"]*)"', html, re.IGNORECASE)
    hidden = dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"',
                             html, re.IGNORECASE))
    if not (action and user_f and pass_f):
        return None
    return {
        "action": urllib.parse.urljoin(base + "/", action.group(1)),
        "user_field": user_f.group(1),
        "pass_field": pass_f.group(1),
        "hidden": hidden,
        "login_html": html,
    }


def _looks_authenticated(status: int, body: str, headers: dict[str, str],
                         set_cookie: str) -> bool:
    low = body.lower()
    if "logout" in low or "sign out" in low:
        return True
    if re.search(r"device\s*info|status|dashboard|home\s*gateway\s*status", low) and "password" not in low:
        return True
    if status in (302, 303) and headers.get("Location", "").rstrip("/").endswith(("home.html", "status.html")):
        return True
    # A fresh session cookie WITHOUT the login error is a weak positive signal.
    if set_cookie and "loginerror" not in low and "invalid" not in low and "type=\"password\"" not in low:
        return True
    return False


def _try_form_login(form: dict[str, Any], user: str, pw: str) -> dict[str, Any]:
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj),
                                         _NoRedirect())
    data = dict(form["hidden"])
    data[form["user_field"]] = user
    data[form["pass_field"]] = pw
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(form["action"], data=body,
                                 headers={"User-Agent": "lan-self-audit",
                                          "Content-Type": "application/x-www-form-urlencoded"})
    try:
        resp = opener.open(req, timeout=6.0)
        status = resp.status
        rbody = resp.read(20000).decode("latin-1", "ignore")
        headers = dict(resp.headers)
    except urllib.error.HTTPError as e:
        status = e.code
        rbody = (e.read(20000).decode("latin-1", "ignore") if e.fp else "")
        headers = dict(e.headers or {})
    except Exception as e:
        return {"ok": False, "error": str(e)}
    set_cookie = headers.get("Set-Cookie", "")
    return {"ok": _looks_authenticated(status, rbody, headers, set_cookie), "status": status}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # keep 3xx so we can inspect Location


def audit_gateway(gateway: str, isp: str, *, authorized: bool = False,
                  ownership_ack: str = "", dry_run: bool = False) -> dict[str, Any]:
    if not authorized or ownership_ack.strip().lower() != "i own these devices":
        return {"skipped": True, "reason": "not authorized (needs explicit ownership ack)"}
    if not _is_private(gateway):
        return {"skipped": True, "reason": "refusing non-private address"}

    base = f"http://{gateway}"
    form = _discover_form(base)
    if not form:
        return {"gateway": gateway, "isp": isp, "login_type": "unknown/none",
                "result": "no HTTP login form detected"}

    creds = DEFAULTS_BY_ISP.get(isp) or DEFAULTS_BY_ISP["generic"]
    creds = creds[:MAX_ATTEMPTS]

    finding: dict[str, Any] = {
        "gateway": gateway,
        "isp": isp,
        "login_type": "web-form",
        "form_action": form["action"],
        "fields": {"user": form["user_field"], "pass": form["pass_field"]},
        "attempts": [],
    }

    if dry_run:
        finding["result"] = "dry-run (no credentials submitted)"
        finding["would_try"] = [f"{u}/****" for u, _ in creds]
        return finding

    for user, pw in creds:
        r = _try_form_login(form, user, pw)
        finding["attempts"].append({"user": user, "status": r.get("status"),
                                    "accepted": r.get("ok", False)})
        time.sleep(DELAY_S)
        if r.get("ok"):
            finding["result"] = "WEAK — factory-default credentials accepted"
            finding["severity"] = "critical"
            finding["accepted_user"] = user  # password intentionally not stored
            return finding

    finding["result"] = "OK — no tested default credentials accepted"
    finding["severity"] = "ok"
    return finding


def main() -> int:
    ap = argparse.ArgumentParser(description="Gateway default-login self-audit (own device only)")
    ap.add_argument("--gateway", default="192.168.29.1")
    ap.add_argument("--isp", default="Jio")
    ap.add_argument("--own", action="store_true", help="assert you own/administer this gateway")
    ap.add_argument("--dry-run", action="store_true", help="detect login form but submit nothing")
    args = ap.parse_args()

    result = audit_gateway(
        args.gateway, args.isp,
        authorized=args.own, ownership_ack="i own these devices" if args.own else "",
        dry_run=args.dry_run,
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "router_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
