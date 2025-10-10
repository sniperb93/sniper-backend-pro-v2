import os
import httpx
from typing import Any, Dict

EMERGENT_BASE_URL = (os.getenv('EMERGENT_BASE_URL', '') or '').rstrip('/')
EMERGENT_API_KEY = os.getenv('EMERGENT_API_KEY', '')
EMERGENT_AGENT_SLUG = os.getenv('EMERGENT_AGENT_SLUG', 'blaxing-sniper')
EMERGENT_DRY_RUN = (os.getenv('EMERGENT_DRY_RUN', 'false') or '').lower() == 'true'


def forward_to_emergent(event_type: str, payload: Dict[str, Any], timeout: int = 5) -> Dict[str, Any]:
    if not EMERGENT_BASE_URL or not EMERGENT_API_KEY:
        return {'status': 'skipped', 'reason': 'missing_config'}
    url = f"{EMERGENT_BASE_URL}/api/v1/webhooks"
    headers = {
        'Authorization': f'Bearer {EMERGENT_API_KEY}',
        'Content-Type': 'application/json',
    }
    body = {
        'agent': EMERGENT_AGENT_SLUG,
        'event': event_type,
        'payload': payload or {},
    }
    if EMERGENT_DRY_RUN:
        return {'dry_run': True, 'payload': body}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=body)
            ct = resp.headers.get('Content-Type', '')
            if resp.status_code >= 400:
                return {'status': 'failed', 'code': resp.status_code, 'text': resp.text[:400]}
            return resp.json() if 'application/json' in ct else {'status': resp.status_code}
    except httpx.RequestError as e:
        return {'status': 'failed', 'error': str(e)}