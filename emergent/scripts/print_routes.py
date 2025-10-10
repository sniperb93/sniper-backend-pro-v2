import os
import importlib

# Try to resolve target app from env (FLASK_APP-style: module[:attr])
TARGET = os.getenv("FLASK_APP") or os.getenv("EMERGENT_FLASK_APP") or "emergent.main:app"

module_name, _, attr = TARGET.partition(":")
if not module_name:
    raise SystemExit("No FLASK_APP provided and default failed")

mod = importlib.import_module(module_name)
app = getattr(mod, attr or "app")

print(f"Listing routes for {module_name}:{attr or 'app'}\n")

rules = sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, sorted(r.methods)))
for r in rules:
    methods = ",".join(sorted(m for m in r.methods if m not in {"HEAD", "OPTIONS"}))
    print(f"{methods:20s} {r.rule}")