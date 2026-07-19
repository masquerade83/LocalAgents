# LAN Control Plane

Discover WiFi/LAN devices on the home network and expose them through one Control Plane UI.

**Network:** JioFiber / Reliance gateway `192.168.29.1` (`192.168.29.0/24`).

## Quick start

```bash
cd lan-control-plane
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Open http://127.0.0.1:8765

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/devices` | Last scan results (+ known registry) |
| `POST` | `/api/scan` | Run discovery now (ARP + optional ping sweep) |
| `GET` | `/api/health` | Service health |

## Architecture (roadmap)

```
Discovery (ARP / mDNS / router)
    → Device Registry
    → Capability adapters (Homey, RTSP cameras, MQTT, …)
    → Control Plane UI
```

### Phase 1 (current)

- ARP table + subnet ping sweep
- Device list UI with IP, MAC, hostname, vendor hint, online status
- Local JSON registry for nicknames / rooms / tags

### Phase 2 (next)

- Homey adapter (lights, scenes)
- Camera deep-link to `rtsp-viewer`
- Stable device IDs + capability model

### Phase 3

- Agent / Hermes hooks via the same `/api/devices` surface
- Optional Home Assistant as a mega-adapter

## Related clawd projects

- `rtsp-viewer/` — camera streams
- `neo4j/` — Homey room/device graph sketch
