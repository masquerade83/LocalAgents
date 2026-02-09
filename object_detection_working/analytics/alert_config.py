"""
Alert message template and options (include frame with WhatsApp, public base URL).
Stored in analytics/alert_config.json.
"""
import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_config.json")

DEFAULTS = {
    "message_template": "Alert: {trigger_name} - {message}",
    "include_frame_with_whatsapp": False,
    "public_base_url": "",
}


def _load():
    if os.path.isfile(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r") as f:
                data = json.load(f)
                return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def get_config():
    """Return current alert config (message_template, include_frame_with_whatsapp, public_base_url)."""
    return _load()


def set_config(message_template=None, include_frame_with_whatsapp=None, public_base_url=None):
    """Update alert config. None values leave existing unchanged."""
    cfg = _load()
    if message_template is not None:
        cfg["message_template"] = message_template
    if include_frame_with_whatsapp is not None:
        cfg["include_frame_with_whatsapp"] = bool(include_frame_with_whatsapp)
    if public_base_url is not None:
        cfg["public_base_url"] = (public_base_url or "").strip()
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg
