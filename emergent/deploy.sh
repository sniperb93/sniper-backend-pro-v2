#!/bin/bash
# emergent/deploy.sh
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Pull latest (optional, safe fail)
if command -v git >/dev/null 2>&1; then
  git pull origin main || true
fi

# Python venv
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip

# Install emergent-specific requirements (local to this folder)
pip install -r requirements.txt

# Restart via systemd if present
if systemctl list-units --full -all | grep -q emergent.service; then
  sudo systemctl restart emergent
else
  # Fallback: run gunicorn in background (Flask app: emergent/main.py -> app)
  pkill -f "gunicorn .* main:app" || true
  nohup venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 main:app &>/dev/null &
fi

echo "Deploy finished"