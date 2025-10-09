#!/usr/bin/env bash
# Usage: ./scripts/load_env.sh && <your command>
set -euo pipefail
cd "$(dirname "$0")/.."
# POSIX-safe .env loader (supports comments). Beware of values with spaces; quote in .env.
set -a
if [ -f .env ]; then
  # shellcheck disable=SC1091
  . ./.env
fi
set +a
# Print a small snapshot (optional)
printenv | grep -E '^(FLASK_ENV|PORT|N8N_|STRIPE_|BINANCE_|OPENAI_|EMERGENT_)' || true