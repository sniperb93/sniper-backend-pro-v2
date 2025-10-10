# Restart docker-compose service (remote host)

On your VPS/Hostinger (SSH):

```bash
cd /root/blaxing
# Restart the service
sudo docker-compose restart blaxing_core

# (or) if using docker compose plugin
sudo docker compose restart blaxing_core

# Check status and tail logs
sudo docker-compose ps
sudo docker-compose logs -n 200 -f blaxing_core
```

Optional helper (if you copy this repo to the server):
```bash
cd /path/to/emergent
chmod +x scripts/restart_compose_service.sh
sudo ./scripts/restart_compose_service.sh /root/blaxing blaxing_core
```

Troubleshooting:
- If the service keeps restarting:
  - Inspect `docker-compose.yml` for env file paths and volume mounts
  - Check `.env` presence and required variables (Stripe/Binance/n8n)
  - Run `sudo docker-compose logs blaxing_core | tail -n 200` for errors
- If compose command differs, use `docker compose` instead of `docker-compose`.