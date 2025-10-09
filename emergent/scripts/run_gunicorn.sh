#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Load .env into current shell for gunicorn
set -a
if [ -f .env ]; then
  # shellcheck disable=SC1091
  . ./.env
fi
set +a
exec venv/bin/gunicorn -w 4 -b 0.0.0.0:${PORT:-5000} main:app