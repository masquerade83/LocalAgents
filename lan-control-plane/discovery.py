"""LAN device discovery via ARP table and optional ping sweep."""

from __future__ import annotations

import concurrent.futures
import platform
import re
import socket
import subprocess
import time
from typing import Any

# JioFiber home LAN (override via env later if needed)
DEFAULT_SUBNET_PREFIX = "192.168.29"
DEFAULT_GATEWAY = "192.168.29.1"

ARP_LINE_RE = re.compile(
    r"^(?P<host>\S+)\s+\((?P<ip>\d+\.\d+\.\d+\.\d+)\)\s+at\s+(?P<mac>[0-9a-fA-F:.-]+)",
)

# Tiny OUI hints for gear already in this home (expand over time)
KNOWN_OUI: dict[str, str] = {
    "a8:88:1f": "Jio / Reliance CPE",
}


def _normalize_mac(mac: str) -> str:
    mac = mac.strip().lower().replace("-", ":")
    if mac in ("(incomplete)", "ff:ff:ff:ff:ff:ff"):
        return ""
    parts = mac.split(":")
    if len(parts) != 6:
        return mac
    return ":".join(p.zfill(2)[-2:] for p in parts)


def _vendor_hint(mac: str) -> str:
    if not mac or len(mac) < 8:
        return ""
    oui = mac[:8]
    return KNOWN_OUI.get(oui, "")


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((DEFAULT_GATEWAY, 80))
            return s.getsockname()[0]
    except OSError:
        return ""


def _run_arp() -> list[dict[str, Any]]:
    try:
        out = subprocess.check_output(["arp", "-a"], text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    devices: list[dict[str, Any]] = []
    for line in out.splitlines():
        m = ARP_LINE_RE.match(line.strip())
        if not m:
            continue
        ip = m.group("ip")
        mac = _normalize_mac(m.group("mac"))
        if not mac:
            continue
        # Skip broadcast / multicast noise
        if ip.endswith(".255") or ip.startswith("224."):
            continue
        host = m.group("host")
        if host in ("?", ip):
            host = ""
        devices.append(
            {
                "ip": ip,
                "mac": mac,
                "hostname": host,
                "vendor": _vendor_hint(mac),
                "source": "arp",
                "online": True,
            }
        )
    return devices


def _ping_host(ip: str, timeout_s: float = 0.4) -> bool:
    system = platform.system().lower()
    if system == "darwin":
        # macOS ping: -W is milliseconds
        cmd = ["ping", "-c", "1", "-W", str(int(timeout_s * 1000)), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout_s))), ip]
    try:
        subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _ping_sweep(prefix: str, workers: int = 64) -> set[str]:
    """Ping .1–.254; returns IPs that responded."""
    alive: set[str] = set()
    ips = [f"{prefix}.{i}" for i in range(1, 255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_ping_host, ip): ip for ip in ips}
        for fut in concurrent.futures.as_completed(futures):
            ip = futures[fut]
            try:
                if fut.result():
                    alive.add(ip)
            except Exception:
                pass
    return alive


def _reverse_dns(ip: str) -> str:
    try:
        name, _, _ = socket.gethostbyaddr(ip)
        return name
    except (socket.herror, socket.gaierror, OSError):
        return ""


def scan_network(
    *,
    subnet_prefix: str = DEFAULT_SUBNET_PREFIX,
    ping_sweep: bool = True,
) -> dict[str, Any]:
    """
    Discover devices. Prefer ARP (authoritative for recently seen L2),
    optionally warm the table with a ping sweep first.
    """
    started = time.time()
    local = _local_ip()

    ping_alive: set[str] = set()
    if ping_sweep:
        ping_alive = _ping_sweep(subnet_prefix)

    by_ip: dict[str, dict[str, Any]] = {}
    for d in _run_arp():
        by_ip[d["ip"]] = d

    # After sweep, ARP may have more entries — re-read once
    if ping_sweep:
        for d in _run_arp():
            prev = by_ip.get(d["ip"])
            if prev:
                if not prev.get("hostname") and d.get("hostname"):
                    prev["hostname"] = d["hostname"]
                if not prev.get("mac") and d.get("mac"):
                    prev["mac"] = d["mac"]
                    prev["vendor"] = d.get("vendor") or _vendor_hint(d["mac"])
            else:
                by_ip[d["ip"]] = d

    for ip in ping_alive:
        if ip not in by_ip:
            by_ip[ip] = {
                "ip": ip,
                "mac": "",
                "hostname": _reverse_dns(ip),
                "vendor": "",
                "source": "ping",
                "online": True,
            }
        else:
            by_ip[ip]["online"] = True
            if not by_ip[ip].get("hostname"):
                by_ip[ip]["hostname"] = _reverse_dns(ip)

    devices = sorted(by_ip.values(), key=lambda d: tuple(int(x) for x in d["ip"].split(".")))
    for d in devices:
        d["is_gateway"] = d["ip"] == DEFAULT_GATEWAY
        d["is_self"] = bool(local) and d["ip"] == local

    return {
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "duration_ms": int((time.time() - started) * 1000),
        "subnet": f"{subnet_prefix}.0/24",
        "gateway": DEFAULT_GATEWAY,
        "local_ip": local,
        "count": len(devices),
        "devices": devices,
    }
