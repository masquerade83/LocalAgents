"""Project-local helpers for jupyter-learning (this folder only).

Reads `project.json` for the default Ollama model. Does not touch other projects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parent
_CONFIG_PATH = PROJECT_ROOT / "project.json"


def load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return json.load(f)


def ollama_base_url() -> str:
    return load_config()["ollama"]["base_url"]


def default_model() -> str:
    return load_config()["ollama"]["default_model"]


def list_models(base_url: str | None = None) -> list[str]:
    url = (base_url or ollama_base_url()).rstrip("/")
    r = requests.get(f"{url}/api/tags", timeout=10)
    r.raise_for_status()
    return [m["name"] for m in r.json().get("models", [])]


def run_ollama(
    prompt: str,
    model: str | None = None,
    *,
    base_url: str | None = None,
    timeout: int = 120,
) -> str:
    """Generate text via local Ollama (stand-in for old BasicModelRunner)."""
    url = (base_url or ollama_base_url()).rstrip("/")
    name = model or default_model()
    resp = requests.post(
        f"{url}/api/generate",
        json={"model": name, "prompt": prompt, "stream": False},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["response"]


def ensure_model(model: str | None = None) -> str:
    """Return model name; raise a clear error if it is not pulled yet."""
    name = model or default_model()
    names = list_models()
    # Ollama may report "qwen2.5:0.5b" or with digest; exact or prefix match
    if name not in names and not any(n.startswith(name) for n in names):
        raise RuntimeError(
            f"Ollama model '{name}' not found. Pull it once with:\n"
            f"  ollama pull {name}\n"
            f"Available: {names}"
        )
    return name
