#!/usr/bin/env bash
# Restart a docker-compose service and stream recent logs
# Usage:
#   ./scripts/restart_compose_service.sh /root/blaxing blaxing_core
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <compose_dir> <service_name>" >&2
  exit 1
fi

COMPOSE_DIR="$1"
SERVICE="$2"

if [ ! -d "$COMPOSE_DIR" ]; then
  echo "Directory not found: $COMPOSE_DIR" >&2
  exit 2
fi

cd "$COMPOSE_DIR"

if command -v docker-compose >/dev/null 2>&1; then
  DC=docker-compose
elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  DC="docker compose"
else
  echo "docker-compose or docker compose not found" >&2
  exit 3
fi

# Show services for visibility
$DC ps || true

# Restart the target service
$DC restart "$SERVICE"

# Tail logs (last 200 lines) after restart
$DC logs -n 200 -f "$SERVICE"