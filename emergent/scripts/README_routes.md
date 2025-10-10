# Lister les routes Flask (dans le conteneur)

Option A — flask CLI
```bash
docker exec -it blaxing_core bash
source venv/bin/activate 2>/dev/null || true
# Selon l'endroit où se trouve l'app
export FLASK_APP=emergent.main:app   # si vous êtes dans /root/blaxing (dossier parent)
# ou
export FLASK_APP=main:app            # si vous êtes cd /root/blaxing/emergent
# (si votre app historique est backend.main, laissez FLASK_APP=backend.main)
flask routes
```

Option B — script Python (pas besoin de flask CLI)
```bash
docker exec -it blaxing_core bash
cd /root/blaxing/emergent
source venv/bin/activate 2>/dev/null || true
# Par défaut le script cible emergent.main:app; pour autre module, précisez EMERGENT_FLASK_APP
EMERGENT_FLASK_APP=backend.main:app python scripts/print_routes.py
# ou simplement
python scripts/print_routes.py
```