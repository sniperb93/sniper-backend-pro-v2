import os
import requests
import logging

# Configuration du logger
logger = logging.getLogger("emergent_forward")

# Lecture des variables d'environnement
EMERGENT_BASE_URL = os.getenv("EMERGENT_BASE_URL", "").rstrip("/")
EMERGENT_API_KEY = os.getenv("EMERGENT_API_KEY", "")
EMERGENT_AGENT_SLUG = os.getenv("EMERGENT_AGENT_SLUG", "blaxing-sniper")
EMERGENT_DRY_RUN = (os.getenv("EMERGENT_DRY_RUN", "false") or "").lower() == "true"


def forward_to_emergent(event_type: str, payload: dict, timeout: int = 5):
    """
    Envoie un événement vers Emergent (non bloquant, sûr, avec logs).
    """
    if not EMERGENT_BASE_URL or not EMERGENT_API_KEY:
        logger.warning("⚠️ Emergent non configuré (pas d'URL ou de clé).")
        return {"status": "skipped", "reason": "missing_config"}

    url = f"{EMERGENT_BASE_URL}/api/v1/webhooks"
    headers = {
        "Authorization": f"Bearer {EMERGENT_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "agent": EMERGENT_AGENT_SLUG,
        "event": event_type,
        "payload": payload or {},
    }

    # Mode dry-run
    if EMERGENT_DRY_RUN:
        logger.info("🧪 [Dry-run] Payload Emergent : %s", {**body, "Authorization": "***"})
        return {"dry_run": True, "payload": body}

    try:
        response = requests.post(url, json=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        logger.info("✅ Envoyé à Emergent : %s (status %s)", event_type, response.status_code)
        return response.json() if "application/json" in response.headers.get("Content-Type", "") else {"status": response.status_code}
    except requests.exceptions.RequestException as e:
        logger.error("❌ Erreur Emergent : %s", e)
        return {"error": str(e), "status": "failed"}