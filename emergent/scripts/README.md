# Env loading helpers

## Linux (bash)
- Votre commande proposée fonctionne avec xargs GNU:
```bash
export $(grep -v '^#' .env | xargs -d '\n')
```

## macOS (BSD xargs ne supporte pas -d)
- Utilisez un chargement POSIX-safe:
```bash
set -a; [ -f .env ] && . ./.env; set +a
```
- Ou utilisez les scripts fournis:
```bash
./scripts/load_env.sh
```

## Démarrer gunicorn avec .env chargé
```bash
./scripts/run_gunicorn.sh
```

## Note
- main.py appelle `load_dotenv()` donc `python main.py` charge déjà `.env`.
- Pour les scripts CLI (ex: test_binance_conn.py) qui n'importent pas dotenv, lancez via:
```bash
set -a; . ./.env; set +a; python test_binance_conn.py
# ou
python -m dotenv run -- python test_binance_conn.py
```