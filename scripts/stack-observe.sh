#!/usr/bin/env bash
# Hermes stack observability + explainability snapshot (JSON).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/observability/stack_observe.py" "$@"
