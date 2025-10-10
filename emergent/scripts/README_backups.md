# Backups before Emergent integration (remote host)

## One-liners you posted
```bash
cd /root/blaxing
mkdir -p backups_before_emergent_$(date +%Y%m%d_%H%M%S)
cp backend/routes/agent_executor_routes.py backups_before_emergent_*/ || true
cp -a backend/utils backups_before_emergent_*/ || true
```

Ces commandes fonctionnent, mais le `*` peut viser le mauvais dossier si plusieurs existent.

## Script sécurisé (recommandé)
Copiez ce repo sur votre hôte et lancez:
```bash
cd /path/to/emergent
chmod +x scripts/backup_paths.sh
./scripts/backup_paths.sh /root/blaxing \
  backend/routes/agent_executor_routes.py \
  backend/utils
```

Résultat:
- /root/blaxing/backups_before_emergent_YYYYMMDD_HHMMSS/
  - backend/routes/agent_executor_routes.py
  - backend/utils/ (copié en entier)

## Restauration
```bash
# Exemple, choisir votre dossier de backup exact
RESTORE_FROM=/root/blaxing/backups_before_emergent_20251008_153012
cd /root/blaxing
cp -a "$RESTORE_FROM/backend/routes/agent_executor_routes.py" backend/routes/ || true
cp -a "$RESTORE_FROM/backend/utils" backend/ || true
```

## Notes
- Le script préserve l’arborescence relative sous le répertoire racine fourni.
- Les chemins passés en absolu sont également supportés.
- Le script ignore silencieusement les chemins absents (log en WARN).