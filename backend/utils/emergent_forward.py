import os
import logging
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("emergent_forward")

EMERGENT_BASE_URL = os.getenv("EMERGENT_BASE_URL", "").rstrip("/")
EMERGENT_API_KEY = os.getenv("EMERGENT_API_KEY", "")
EMERGENT_AGENT_SLUG = os.getenv("EMERGENT_AGENT_SLUG", "blaxing-sniper")
EMERGENT_DRY_RUN = (os.getenv("EMERGENT_DRY_RUN", "false") or "").lower() == "true"


async def forward_to_emergent_async(event_type: str, payload: Dict[str, Any], timeout: int = 5) -> Dict[str, Any]:
    """Envoie un événement vers Emergent (asynchrone, sûr)."""
    if not EMERGENT_BASE_URL or not EMERGENT_API_KEY:
        logger.warning("Emergent non configuré (EMERGENT_BASE_URL/EMERGENT_API_KEY manquants)")
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

    if EMERGENT_DRY_RUN:
        logger.info("[Dry-run] Emergent payload: %s", {**body, "Authorization": "***"})
        return {"dry_run": True, "payload": body}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            ct = resp.headers.get("Content-Type", "")
            if resp.status_code >= 400:
                logger.error("Emergent error: %s %s", resp.status_code, resp.text[:400])
                return {"status": "failed", "code": resp.status_code, "text": resp.text[:400]}
            return resp.json() if "application/json" in ct else {"status": resp.status_code}
    except httpx.RequestError as e:
        logger.error("Emergent request error: %s", e)
        return {"status": "failed", "error": str(e)}