# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Cameras

### RTSP Streams
- **Camera 1** (192.168.29.221): `rtsp://kush.sood:admin@123@192.168.29.221/stream1`
  - Username: `kush.sood`
  - Password: `admin@123`
  - IP: `192.168.29.221`
  - Stream: `stream1`
  - **Status**: ✅ Working - Stream is accessible and functional
  - **Last tested**: 2026-01-26

## Notion

- **API key:** Set `NOTION_API_KEY` or `NOTION_TOKEN` (from <https://www.notion.so/my-integrations>).
- **Test:** `python scripts/test_notion.py` (from repo root).

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin

### TTS
- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
