# Redeploy helper for docker-compose services

## Manual steps (as you wrote)
```bash
cd /root/blaxing
# add deps if missing
grep -q "^python-binance" requirements.txt || echo "python-binance" >> requirements.txt
grep -q "^requests" requirements.txt || echo "requests" >> requirements.txt
grep -q "^python-dotenv" requirements.txt || echo "python-dotenv" >> requirements.txt

# rebuild & restart
docker-compose build blaxing_core
docker-compose up -d blaxing_core
# follow logs
docker-compose logs -f --tail=200 blaxing_core
```

## One-shot script (safer, handles docker compose vs docker-compose)
```bash
cd /path/to/emergent
chmod +x scripts/compose_update_requirements_and_redeploy.sh
sudo ./scripts/compose_update_requirements_and_redeploy.sh /root/blaxing blaxing_core
```

Notes
- The script only appends missing lines to requirements.txt (no duplicates)
- Works with docker-compose and the newer docker compose plugin
- Tail logs at the end so you can verify startup in real-time