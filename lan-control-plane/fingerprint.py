"""Lightweight service fingerprinting for discovered LAN devices.

Non-intrusive: a small curated TCP connect-scan of common management / IoT
ports plus HTTP(S) title & header grab. Used to enrich the knowledge graph and
to know which devices even expose a login surface worth auditing.

Scope guard: only scans RFC1918 (private) addresses. It refuses public IPs.
"""

from __future__ import annotations

import concurrent.futures
import ipaddress
import socket
import ssl
import re
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Curated ports: management + common IoT/camera/home-automation surfaces.
COMMON_PORTS: dict[int, str] = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    53: "dns",
    80: "http",
    443: "https",
    445: "smb",
    554: "rtsp",
    1883: "mqtt",
    5000: "http-alt/upnp",
    8000: "http-alt",
    8080: "http-proxy",
    8443: "https-alt",
    8883: "mqtts",
    9000: "http-alt",
    37777: "dahua-dvr",
    34567: "xmeye-dvr",
    49152: "upnp",
}

HTTP_PORTS = {80, 8080, 8000, 5000, 9000}
HTTPS_PORTS = {443, 8443}

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def _check_port(ip: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((ip, port)) == 0
    except OSError:
        return False


def _grab_banner(ip: str, port: int, timeout: float = 1.0) -> str:
    """Read a short banner for plaintext services (ssh/telnet/ftp/mqtt)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) != 0:
                return ""
            try:
                data = s.recv(160)
            except socket.timeout:
                return ""
            return data.decode("latin-1", "ignore").strip().splitlines()[0][:120] if data else ""
    except OSError:
        return ""


def _http_probe(ip: str, port: int, tls: bool) -> dict[str, Any]:
    scheme = "https" if tls else "http"
    url = f"{scheme}://{ip}:{port}/"
    info: dict[str, Any] = {}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = Request(url, headers={"User-Agent": "lan-control-plane/fingerprint"})
        with urlopen(req, timeout=2.0, context=ctx if tls else None) as resp:
            info["status"] = resp.status
            server = resp.headers.get("Server")
            if server:
                info["server"] = server[:80]
            auth = resp.headers.get("WWW-Authenticate")
            if auth:
                info["auth_scheme"] = auth.split(" ")[0][:40]
            body = resp.read(8192).decode("latin-1", "ignore")
            m = _TITLE_RE.search(body)
            if m:
                info["title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:80]
    except HTTPError as e:
        info["status"] = e.code
        auth = e.headers.get("WWW-Authenticate") if e.headers else None
        if auth:
            info["auth_scheme"] = auth.split(" ")[0][:40]
        server = e.headers.get("Server") if e.headers else None
        if server:
            info["server"] = server[:80]
    except (URLError, ssl.SSLError, socket.timeout, OSError, ValueError):
        pass
    return info


def _guess_type(dev: dict[str, Any], services: dict[int, dict[str, Any]]) -> str:
    ports = set(services)
    text = " ".join(
        [
            dev.get("vendor", ""),
            dev.get("hostname", ""),
            " ".join(str(s.get("title", "")) for s in services.values()),
            " ".join(str(s.get("server", "")) for s in services.values()),
            " ".join(str(s.get("banner", "")) for s in services.values()),
        ]
    ).lower()

    if dev.get("is_gateway"):
        return "router"
    if 554 in ports or 37777 in ports or 34567 in ports or "camera" in text or "rtsp" in text:
        return "camera"
    if 1883 in ports or 8883 in ports or "mqtt" in text:
        return "iot-broker"
    if any(k in text for k in ("printer", "hp ", "epson", "canon")):
        return "printer"
    if any(k in text for k in ("router", "gateway", "openwrt", "mikrotik")):
        return "router"
    if 22 in ports and not (HTTP_PORTS & ports):
        return "host/server"
    if HTTP_PORTS & ports or HTTPS_PORTS & ports:
        return "web-admin device"
    return "unknown"


def fingerprint_device(dev: dict[str, Any], workers: int = 16) -> dict[str, Any]:
    ip = dev["ip"]
    out = dict(dev)
    if not is_private(ip):
        out["services"] = {}
        out["device_type"] = "skipped (non-private)"
        return out

    services: dict[int, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_check_port, ip, p): p for p in COMMON_PORTS}
        for fut in concurrent.futures.as_completed(futures):
            port = futures[fut]
            try:
                if fut.result():
                    services[port] = {"service": COMMON_PORTS[port]}
            except Exception:
                pass

    for port in list(services):
        if port in HTTP_PORTS:
            services[port].update(_http_probe(ip, port, tls=False))
        elif port in HTTPS_PORTS:
            services[port].update(_http_probe(ip, port, tls=True))
        elif port in (22, 23, 21, 1883):
            banner = _grab_banner(ip, port)
            if banner:
                services[port]["banner"] = banner

    out["services"] = {str(k): v for k, v in sorted(services.items())}
    out["open_ports"] = sorted(services)
    out["device_type"] = _guess_type(dev, services)
    out["login_surface"] = sorted(
        p for p in services if p in HTTP_PORTS | HTTPS_PORTS | {22, 23, 21}
    )
    return out


def fingerprint_all(devices: list[dict[str, Any]], workers: int = 8) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = [None] * len(devices)  # type: ignore
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fingerprint_device, d): i for i, d in enumerate(devices)}
        for fut in concurrent.futures.as_completed(futures):
            i = futures[fut]
            try:
                results[i] = fut.result()
            except Exception:
                results[i] = dict(devices[i], services={}, device_type="error")
    return results
