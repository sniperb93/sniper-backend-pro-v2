import os
import requests
import logging

logger = logging.getLogger("emergent_forward")

EMERGENT_BASE_URL = os.getenv("EMERGENT_BASE_URL", "").rstrip("/")
EMERGENT_API_KEY = os.getenv("EMERGENT_API_KEY", "")
EMERGENT_AGENT_SLUG = os.getenv("EMERGENT_AGENT_SLUG", "blaxing-sniper")
EMERGENT_DRY_RUN = os.getenv("EMERGENT_DRY_RUN", "false").lower() == "true"


def forward_to_emergent(event_type: str, payload: dict, timeout: int = 5):
    if not EMERGENT_BASE_URL or not EMERGENT_API_KEY:
        logger.warning("Emergent not configured (missing URL/API key).")
        return {"status": "skipped", "reason": "missing_config"}
    url = f"{EMERGENT_BASE_URL}/api/v1/webhooks"
    headers = {"Authorization": f"Bearer {EMERGENT_API_KEY}", "Content-Type": "application/json"}
    body = {"agent": EMERGENT_AGENT_SLUG, "event": event_type, "payload": payload}
    if EMERGENT_DRY_RUN:
        logger.info("[Dry-run] Emergent payload: %s", body)
        return {"dry_run": True, "payload": body}
    try:
        r = requests.post(url, json=body, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json() if "application/json" in r.headers.get("Content-Type", "") else {"status": r.status_code}
    except Exception as e:
        logger.error("Emergent forward error: %s", e)
        return {"error": str(e), "status": "failed"}