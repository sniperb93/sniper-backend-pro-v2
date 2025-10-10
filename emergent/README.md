# Emergent Flask Service (Docker & Local)

## Local (venv) quick start
```bash
cd emergent
chmod +x scripts/setup_local_venv.sh
./scripts/setup_local_venv.sh
# or manual:
# python3 -m venv venv && source venv/bin/activate
# pip install -r requirements.txt
# pip install python-binance requests python-dotenv
```

Check imports:
```bash
python scripts/verify_python_env.py
# or
python -c "import binance, requests, dotenv; print('ok', binance, requests, dotenv)"
```

Run service:
```bash
python main.py
# or
venv/bin/gunicorn -w 4 -b 0.0.0.0:${PORT:-5000} main:app
```

## Docker Compose
```bash
cd emergent
docker compose up --build -d
```

## Environment (.env)
- See `.env` in this folder for example keys (Stripe/Binance/n8n/OpenAI)
- main.py uses `load_dotenv()` so `python main.py` auto-loads `.env`

## Notes
- This Flask bundle is independent of the main FastAPI app that powers the Blaxing Orchestrator.