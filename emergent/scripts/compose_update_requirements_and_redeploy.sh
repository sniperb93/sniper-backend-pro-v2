#!/usr/bin/env bash
# Update requirements.txt with missing deps and rebuild/restart a compose service
# Usage:
#   ./scripts/compose_update_requirements_and_redeploy.sh /root/blaxing blaxing_core
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <compose_dir> <service_name>" >&2
  exit 1
fi

COMPOSE_DIR="$1"
SERVICE="$2"
REQ_FILE="$COMPOSE_DIR/requirements.txt"

if [ ! -d "$COMPOSE_DIR" ]; then
  echo "Directory not found: $COMPOSE_DIR" >&2
  exit 2
fi

# Ensure requirements.txt exists
if [ ! -f "$REQ_FILE" ]; then
  echo "requirements.txt not found in $COMPOSE_DIR" >&2
  exit 3
fi

ensure_line() {
  local line="$1"
  local file="$2"
  if ! grep -q "^${line}\b" "$file" 2>/dev/null; then
    echo "$line" >> "$file"
    echo "> Added $line to $(basename "$file")"
  else
    echo "> $line already present"
  fi
}

# Add deps if missing
ensure_line "python-binance" "$REQ_FILE"
ensure_line "requests" "$REQ_FILE"
ensure_line "python-dotenv" "$REQ_FILE"

# Choose compose CLI
if command -v docker-compose >/dev/null 2>&1; then
  DC=docker-compose
elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  DC="docker compose"
else
  echo "docker-compose or docker compose not found" >&2
  exit 4
fi

cd "$COMPOSE_DIR"

# Build & redeploy target service
$DC build "$SERVICE"
$DC up -d "$SERVICE"

# Tail logs
$DC logs -f --tail=200 "$SERVICE"