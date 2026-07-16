#!/usr/bin/env bash
# One-time / repeat setup: Postgres tables + Prisma client for LiteLLM UI.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.local/share/uv/tools/litellm/bin:$PATH"
export DATABASE_URL="${DATABASE_URL:-postgresql://litellm:litellm@127.0.0.1:5432/litellm}"
SCHEMA="$HOME/.local/share/uv/tools/litellm/lib/python3.13/site-packages/litellm/proxy/schema.prisma"

echo "Ensuring Postgres is up..."
docker compose -f "$DIR/docker-compose.yml" up -d postgres
for _ in $(seq 1 30); do
  docker compose -f "$DIR/docker-compose.yml" exec -T postgres pg_isready -U litellm -d litellm >/dev/null 2>&1 && break
  sleep 1
done

echo "Installing prisma + Pillow (if missing)..."
uv pip install --python "$HOME/.local/share/uv/tools/litellm/bin/python" prisma Pillow >/dev/null 2>&1 || true

echo "Generating Prisma client..."
cd "$(dirname "$SCHEMA")"
prisma generate --schema schema.prisma

echo "Pushing schema to database..."
prisma db push --schema schema.prisma

echo "LiteLLM database ready."
