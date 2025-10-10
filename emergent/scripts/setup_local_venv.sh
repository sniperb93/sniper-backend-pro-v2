#!/usr/bin/env bash
# Local setup helper for the Flask bundle
# Usage:
#   cd /path/to/emergent
#   ./scripts/setup_local_venv.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# Create venv if missing
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip

# Install project requirements
pip install -r requirements.txt

# Ensure extra libs (explicit per your command)
pip install python-binance requests python-dotenv

# Quick import check
python - << 'PY'
try:
    import binance, requests, dotenv
    print('ok', binance.__version__ if hasattr(binance, '__version__') else 'n/a', requests.__version__, dotenv.__version__ if hasattr(dotenv, '__version__') else 'n/a')
except Exception as e:
    import sys
    print('import error:', e)
    sys.exit(1)
PY