import importlib
import sys

mods = [
    ("binance", "python-binance"),
    ("requests", "requests"),
    ("dotenv", "python-dotenv"),
]

ok = True
for mod, pkg in mods:
    try:
        m = importlib.import_module(mod)
        ver = getattr(m, "__version__", "n/a")
        print(f"✓ {mod} ({pkg}) version: {ver}")
    except Exception as e:
        ok = False
        print(f"✗ Failed to import {mod} ({pkg}): {e}")

sys.exit(0 if ok else 1)