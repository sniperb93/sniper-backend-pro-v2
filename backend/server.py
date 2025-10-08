from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import httpx
import yaml
import json
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection - MUST use existing MONGO_URL and DB_NAME from env
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Environment configuration (no hardcoding)
BLA_API_KEY = os.environ.get('BLA_API_KEY')
AGENT_MANAGER_BASE_URL = os.environ.get('AGENT_MANAGER_BASE_URL', 'https://blaxing.fr/api')
EMERGENT_DRY_RUN = os.environ.get('EMERGENT_DRY_RUN', 'true').lower() in ['1', 'true', 'yes']
N8N_WEBHOOK_BASE = os.environ.get('N8N_WEBHOOK_BASE', '')
N8N_WEBHOOK_AUTH = os.environ.get('N8N_WEBHOOK_AUTH', '')
N8N_WEBHOOK_TOKEN = os.environ.get('N8N_WEBHOOK_TOKEN', '')
N8N_AUTH_ENABLED = (N8N_WEBHOOK_AUTH or '').lower() == 'enabled'
# Emergent LLM integration
EMERGENT_LLM_URL = os.environ.get('EMERGENT_LLM_URL', 'https://api.emergent-llm.ai')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Paths for default agents file (optional fallback)
DEFAULT_AGENTS_FILE = (ROOT_DIR.parent / 'emergent' / 'agents' / 'data' / 'agents.json').resolve()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# HTTPX client for upstream calls
httpx_client = httpx.AsyncClient(
    timeout=httpx.Timeout(20.0, connect=5.0),
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=25)
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inject Universal Key middleware (simple fallback). Prefer platform injection if available.
@app.middleware("http")
async def inject_universal_key(request: Request, call_next):
    if not os.environ.get('EMERGENT_UNIVERSAL_KEY') and os.environ.get('EMERGENT_LLM_KEY'):
        os.environ['EMERGENT_UNIVERSAL_KEY'] = os.environ['EMERGENT_LLM_KEY']
    response = await call_next(request)
    return response

# Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class AuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    agent_id: Optional[str] = None
    method: str
    path: str
    success: bool
    upstream_status: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RegisterAgentPayload(BaseModel):
    agent_id: str
    image: str
    env: Dict[str, Any] = Field(default_factory=dict)

class N8nTriggerUrlPayload(BaseModel):
    url: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class N8nFlowUpsert(BaseModel):
    flow: str
    url: str

class N8nDiagnosticsRequest(BaseModel):
    url: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class BuilderAgentCreate(BaseModel):
    name: str
    role: str
    personality: str
    mission: str
    api_key: Optional[str] = None
    active: bool = True
    use_openai: bool = False

class BuilderAgentOut(BaseModel):
    id: str
    name: str
    role: str
    personality: str
    mission: str
    active: bool
    use_openai: bool
    created_at: datetime

class AgentAskRequest(BaseModel):
    agent_id: str
    prompt: str

class AgentAskGatewayRequest(BaseModel):
    agent_id: Optional[str] = None
    prompt: str

# Helpers
async def log_audit(entry: AuditEntry) -> None:
    try:
        doc = entry.model_dump()
        doc['_id'] = doc['id']
        doc['timestamp'] = doc['timestamp'].isoformat()
        await db.audit_logs.insert_one(doc)
    except Exception as e:
        logger.error(f"Failed to persist audit log: {e}")

async def upstream_request(method: str, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not BLA_API_KEY:
        raise HTTPException(status_code=400, detail="BLA_API_KEY not configured")
    url = f"{AGENT_MANAGER_BASE_URL}{path}"
    headers = {'X-API-KEY': BLA_API_KEY, 'Content-Type': 'application/json'}
    try:
        resp = await httpx_client.request(method, url, headers=headers, json=json)
        try:
            content = resp.json()
        except Exception:
            content = {'text': resp.text}
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=content)
        return {'status': resp.status_code, 'data': content}
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Upstream request error to {url}: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach agent-manager")

async def emergent_llm_infer(agent_name: str, prompt: str) -> str:
    uni_key = os.environ.get('EMERGENT_UNIVERSAL_KEY') or EMERGENT_LLM_KEY
    if not uni_key:
        return "⚠️ Universal Key non détectée. Vérifie ton Integration Manager."
    url = f"{EMERGENT_LLM_URL.rstrip('/')}/infer"
    headers = {'Authorization': f'Bearer {uni_key}', 'Content-Type': 'application/json'}
    payload = {'model': 'emergent-llm-v1', 'agent': agent_name, 'prompt': prompt}
    try:
        resp = await httpx_client.post(url, headers=headers, json=payload)
        try:
            data = resp.json()
        except Exception:
            data = {'text': resp.text}
        if resp.status_code >= 400:
            return data.get('detail') or data.get('error') or data.get('text') or "Aucune réponse reçue du moteur Emergent."
        return data.get('response') or data.get('text') or "Aucune réponse reçue du moteur Emergent."
    except httpx.RequestError:
        return "Aucune réponse reçue du moteur Emergent."

async def universal_llm_gateway(prompt: str, agent_name: Optional[str] = None) -> Dict[str, Any]:
    resp = await emergent_llm_infer(agent_name or 'anonymous-agent', prompt)
    engine = 'Emergent LLM'
    return {"engine_used": engine, "response": resp}

# File helpers for defaults
def read_default_agents_file() -> List[Dict[str, Any]]:
    try:
        if DEFAULT_AGENTS_FILE.exists():
            with open(DEFAULT_AGENTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Failed reading default agents file: {e}")
    return []

# --- Base endpoints ---
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.model_dump())
    doc = status_obj.model_dump(); doc['_id'] = doc['id']; doc['timestamp'] = doc['timestamp'].isoformat()
    await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    items = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for it in items:
        if isinstance(it.get('timestamp'), str):
            it['timestamp'] = datetime.fromisoformat(it['timestamp'])
    return items

# --- Config endpoint ---
@api_router.get("/config")
async def get_config():
    return {
        'hasKey': bool(BLA_API_KEY),
        'dryRun': EMERGENT_DRY_RUN,
        'agentManagerBase': AGENT_MANAGER_BASE_URL,
        'n8nWebhookBase': N8N_WEBHOOK_BASE if N8N_WEBHOOK_BASE else None,
        'emergentLlmConfigured': bool(os.environ.get('EMERGENT_UNIVERSAL_KEY') or EMERGENT_LLM_KEY)
    }

# --- Agent manager proxy endpoints ---
@api_router.get("/agents/list")
async def agents_list(request: Request):
    result = await upstream_request('GET', '/agents/list')
    await log_audit(AuditEntry(action='agents_list', method='GET', path='/agents/list', success=True, upstream_status=result['status']))
    return result['data']

@api_router.post("/agents/register")
async def agents_register(payload: RegisterAgentPayload):
    if EMERGENT_DRY_RUN:
        await log_audit(AuditEntry(action='agents_register', agent_id=payload.agent_id, method='POST', path='/agents/register', success=True, upstream_status=200))
        return {"dry_run": True, "message": "Register simulated", "payload": payload.model_dump()}
    result = await upstream_request('POST', '/agents/register', json=payload.model_dump())
    await log_audit(AuditEntry(action='agents_register', agent_id=payload.agent_id, method='POST', path='/agents/register', success=True, upstream_status=result['status']))
    return result['data']

@api_router.post("/agents/{agent_id}/activate")
async def agent_activate(agent_id: str):
    if EMERGENT_DRY_RUN:
        await log_audit(AuditEntry(action='agent_activate', agent_id=agent_id, method='POST', path=f'/agents/{agent_id}/activate', success=True, upstream_status=200))
        return {"dry_run": True, "message": f"Activate {agent_id} simulated"}
    result = await upstream_request('POST', f'/agents/{agent_id}/activate')
    await log_audit(AuditEntry(action='agent_activate', agent_id=agent_id, method='POST', path=f'/agents/{agent_id}/activate', success=True, upstream_status=result['status']))
    return result['data']

@api_router.post("/agents/{agent_id}/deactivate")
async def agent_deactivate(agent_id: str):
    if EMERGENT_DRY_RUN:
        await log_audit(AuditEntry(action='agent_deactivate', agent_id=agent_id, method='POST', path=f'/agents/{agent_id}/deactivate', success=True, upstream_status=200))
        return {"dry_run": True, "message": f"Deactivate {agent_id} simulated"}
    result = await upstream_request('POST', f'/agents/{agent_id}/deactivate')
    await log_audit(AuditEntry(action='agent_deactivate', agent_id=agent_id, method='POST', path=f'/agents/{agent_id}/deactivate', success=True, upstream_status=result['status']))
    return result['data']

@api_router.get("/agents/{agent_id}/status")
async def agent_status(agent_id: str):
    result = await upstream_request('GET', f'/agents/{agent_id}/status')
    await log_audit(AuditEntry(action='agent_status', agent_id=agent_id, method='GET', path=f'/agents/{agent_id}/status', success=True, upstream_status=result['status']))
    return result['data']

@api_router.post("/agents/activate-all")
async def agents_activate_all():
    if EMERGENT_DRY_RUN:
        await log_audit(AuditEntry(action='agents_activate_all', method='POST', path='/agents/activate-all', success=True, upstream_status=200))
        return {"dry_run": True, "message": "Activate-all simulated"}
    result = await upstream_request('POST', '/agents/activate-all')
    await log_audit(AuditEntry(action='agents_activate_all', method='POST', path='/agents/activate-all', success=True, upstream_status=result['status']))
    return result['data']

@api_router.post("/agents/deactivate-all")
async def agents_deactivate_all():
    if EMERGENT_DRY_RUN:
        await log_audit(AuditEntry(action='agents_deactivate_all', method='POST', path='/agents/deactivate-all', success=True, upstream_status=200))
        return {"dry_run": True, "message": "Deactivate-all simulated"}
    result = await upstream_request('POST', '/agents/deactivate-all')
    await log_audit(AuditEntry(action='agents_deactivate_all', method='POST', path='/agents/deactivate-all', success=True, upstream_status=result['status']))
    return result['data']

# --- n8n trigger endpoints ---
@api_router.post("/n8n/trigger/{flow}")
async def n8n_trigger(flow: str, payload: Dict[str, Any]):
    if not N8N_WEBHOOK_BASE:
        raise HTTPException(status_code=400, detail="N8N_WEBHOOK_BASE not configured")
    url = f"{N8N_WEBHOOK_BASE}/{flow}"
    headers = {'Content-Type': 'application/json'}
    if N8N_AUTH_ENABLED and N8N_WEBHOOK_TOKEN:
        headers['Authorization'] = f'Bearer {N8N_WEBHOOK_TOKEN}'
    try:
        resp = await httpx_client.post(url, headers=headers, json=payload)
        try:
            data = resp.json()
        except Exception:
            data = {'text': resp.text}
        if resp.status_code >= 400:
            await log_audit(AuditEntry(action='n8n_trigger', method='POST', path=f'/webhook/{flow}', success=False, upstream_status=resp.status_code, error=str(data)[:400]))
            raise HTTPException(status_code=resp.status_code, detail=data)
        await log_audit(AuditEntry(action='n8n_trigger', method='POST', path=f'/webhook/{flow}', success=True, upstream_status=resp.status_code))
        return data
    except httpx.RequestError as e:
        await log_audit(AuditEntry(action='n8n_trigger', method='POST', path=f'/webhook/{flow}', success=False, error=str(e)[:400]))
        raise HTTPException(status_code=502, detail="Failed to reach n8n")

@api_router.post("/n8n/trigger-url")
async def n8n_trigger_url(body: N8nTriggerUrlPayload):
    url = body.url
    if not (url.startswith('http://') or url.startswith('https://')):
        raise HTTPException(status_code=400, detail="Invalid URL")
    headers = {'Content-Type': 'application/json'}
    if N8N_AUTH_ENABLED and N8N_WEBHOOK_TOKEN:
        headers['Authorization'] = f'Bearer {N8N_WEBHOOK_TOKEN}'
    try:
        resp = await httpx_client.post(url, headers=headers, json=body.payload)
        try:
            data = resp.json()
        except Exception:
            data = {'text': resp.text}
        masked_path = url[:40] + '...' + url[-6:] if len(url) > 50 else url
        if resp.status_code >= 400:
            await log_audit(AuditEntry(action='n8n_trigger_url', method='POST', path=masked_path, success=False, upstream_status=resp.status_code, error=str(data)[:400]))
            raise HTTPException(status_code=resp.status_code, detail=data)
        await log_audit(AuditEntry(action='n8n_trigger_url', method='POST', path=masked_path, success=True, upstream_status=resp.status_code))
        return data
    except httpx.RequestError as e:
        masked_path = url[:40] + '...' + url[-6:] if len(url) > 50 else url
        await log_audit(AuditEntry(action='n8n_trigger_url', method='POST', path=masked_path, success=False, error=str(e)[:400]))
        raise HTTPException(status_code=502, detail="Failed to reach n8n")

@api_router.get("/n8n/flows/list")
async def n8n_flows_list():
    items = await db.n8n_flows.find({}, {"_id": 0}).to_list(200)
    return {"flows": items}

@api_router.post("/n8n/flows/upsert")
async def n8n_flows_upsert(body: N8nFlowUpsert):
    if not body.flow or not body.url:
        raise HTTPException(status_code=400, detail="flow and url required")
    doc = {"flow": body.flow, "url": body.url, "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.n8n_flows.update_one({"flow": body.flow}, {"$set": doc}, upsert=True)
    await log_audit(AuditEntry(action='n8n_flow_upsert', method='POST', path='/n8n/flows/upsert', success=True, upstream_status=200))
    return {"ok": True}

@api_router.post("/n8n/flows/trigger/{flow}")
async def n8n_flows_trigger(flow: str, payload: Optional[Dict[str, Any]] = None):
    rec = await db.n8n_flows.find_one({"flow": flow})
    if not rec:
        raise HTTPException(status_code=404, detail="Flow not configured")
    effective_payload = payload if (payload and len(payload) > 0) else {
        'trade_alerts_flow': {"symbol": "BTCUSDT", "signal": "buy"},
        'crystal_autopost': {"message": "Nouvelle publication automatique"},
        'legal_guard': {"case": "Rappel de droits utilisateur"},
        'auto_restart': {"service": "Emergent Core"},
    }.get(flow, {})
    body = N8nTriggerUrlPayload(url=rec.get("url"), payload=effective_payload)
    return await n8n_trigger_url(body)

# Diagnostics
def _n8n_hint_for_response(code: int, body_text: str) -> str:
    txt = (body_text or '').lower()
    if code == 404 and 'webhook' in txt and 'register' in txt:
        return "Webhook non armé. Cliquez sur 'Execute Workflow' dans n8n, ou utilisez l'URL /webhook avec le workflow activé."
    if code in (401, 403):
        return "Non autorisé. Vérifiez l'authentification/ACL côté n8n."
    if code in (502, 503, 504):
        return "Service n8n indisponible. Réessayez plus tard ou vérifiez le service."
    if code >= 400:
        return "Erreur côté n8n. Vérifiez l'URL exacte et l'état du workflow."
    return "OK"

@api_router.post("/n8n/diagnostics")
async def n8n_diagnostics(body: N8nDiagnosticsRequest):
    url = body.url
    if not (url and (url.startswith('http://') or url.startswith('https://'))):
        raise HTTPException(status_code=400, detail="Invalid URL")
    headers = {'Content-Type': 'application/json'}
    if N8N_AUTH_ENABLED and N8N_WEBHOOK_TOKEN:
        headers['Authorization'] = f'Bearer {N8N_WEBHOOK_TOKEN}'
    started = time.time()
    try:
        resp = await httpx_client.post(url, headers=headers, json=body.payload)
        latency_ms = int((time.time() - started) * 1000)
        text = resp.text
        hint = _n8n_hint_for_response(resp.status_code, text)
        details = text[:500]
        status = 'ok' if resp.status_code < 400 else 'error'
        await log_audit(AuditEntry(action='n8n_diagnostics', method='POST', path=url[:40]+'...', success=(status=='ok'), upstream_status=resp.status_code, error=None if status=='ok' else details))
        return {
            'status': status,
            'http_code': resp.status_code,
            'latency_ms': latency_ms,
            'hint': hint,
            'details': f"Response: {details}"
        }
    except httpx.RequestError as e:
        latency_ms = int((time.time() - started) * 1000)
        await log_audit(AuditEntry(action='n8n_diagnostics', method='POST', path=url[:40]+'...', success=False, upstream_status=None, error=str(e)[:300]))
        return {
            'status': 'error',
            'http_code': 0,
            'latency_ms': latency_ms,
            'hint': 'Impossible de joindre n8n (réseau/host).',
            'details': str(e)
        }

# --- Agent Builder (FastAPI) ---
@api_router.post("/agent-builder/create", response_model=BuilderAgentOut)
async def builder_create_agent(body: BuilderAgentCreate):
    doc = {
        'id': str(uuid.uuid4()),
        'name': body.name,
        'role': body.role,
        'personality': body.personality,
        'mission': body.mission,
        'api_key': body.api_key,
        'active': body.active,
        'use_openai': body.use_openai,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    to_store = dict(doc); to_store['_id'] = doc['id']
    try:
        await db.agents_builder.insert_one(to_store)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create agent")
    await log_audit(AuditEntry(action='builder_create_agent', agent_id=doc['id'], method='POST', path='/agent-builder/create', success=True, upstream_status=201))
    return BuilderAgentOut(**{**doc, 'created_at': datetime.fromisoformat(doc['created_at'])})

@api_router.get("/agent-builder/list", response_model=List[BuilderAgentOut])
async def builder_list_agents():
    items = await db.agents_builder.find({}, {"_id": 0, "api_key": 0}).sort("created_at", -1).to_list(1000)
    if not items:
        defaults = read_default_agents_file()
        provisional = []
        for a in defaults:
            provisional.append(BuilderAgentOut(
                id=str(uuid.uuid4()),
                name=a.get('name',''),
                role=a.get('role',''),
                personality=a.get('personality',''),
                mission=a.get('mission',''),
                active=True,
                use_openai=bool(a.get('use_openai')),
                created_at=datetime.now(timezone.utc)
            ))
        return provisional
    normalized: List[BuilderAgentOut] = []
    for it in items:
        ca = it.get('created_at')
        if isinstance(ca, str):
            try:
                it['created_at'] = datetime.fromisoformat(ca)
            except Exception:
                it['created_at'] = datetime.now(timezone.utc)
        normalized.append(BuilderAgentOut(**it))
    return normalized

@api_router.post("/agent-builder/ask")
async def builder_ask_agent(body: AgentAskRequest):
    agent = await db.agents_builder.find_one({'_id': body.agent_id})
    if not agent:
        agent = await db.agents_builder.find_one({'id': body.agent_id})
    if not agent:
        agent = await db.agents_builder.find_one({'name': body.agent_id})
    if not agent:
        await db.audit_logs.insert_one({
            '_id': str(uuid.uuid4()),
            'id': str(uuid.uuid4()),
            'event': 'builder_agent_ask_failed',
            'reason': 'agent_not_found',
            'provided_agent_id': body.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        raise HTTPException(status_code=404, detail="Agent introuvable")
    response_text = await emergent_llm_infer(agent_name=agent.get('name', body.agent_id), prompt=body.prompt)
    audit_payload = {
        'id': str(uuid.uuid4()),
        'event': 'builder_agent_ask',
        'agent': agent.get('name'),
        'prompt': body.prompt[:1000],
        'response': (response_text or '')[:4000],
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    audit_payload['_id'] = audit_payload['id']
    await db.audit_logs.insert_one(audit_payload)
    return {'agent': agent.get('name'), 'response': response_text, 'timestamp': audit_payload['timestamp']}

@api_router.post("/agent-builder/ask/gateway")
async def builder_ask_gateway(body: AgentAskGatewayRequest):
    agent_name = None
    if body.agent_id:
        ag = await db.agents_builder.find_one({'_id': body.agent_id}) or \
             await db.agents_builder.find_one({'id': body.agent_id}) or \
             await db.agents_builder.find_one({'name': body.agent_id})
        agent_name = (ag or {}).get('name') if ag else None
    result = await universal_llm_gateway(body.prompt, agent_name)
    await db.audit_logs.insert_one({
        '_id': str(uuid.uuid4()),
        'id': str(uuid.uuid4()),
        'event': 'builder_agent_ask_gateway',
        'agent': agent_name or body.agent_id or 'anonymous',
        'prompt': body.prompt[:1000],
        'engine': result.get('engine_used'),
        'response': (result.get('response') or '')[:4000],
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    return result

# --- Health check cron (optional) ---
import asyncio

async def _cron_n8n_health():
    while True:
        try:
            flows = await db.n8n_flows.find({}, {"_id": 0}).to_list(100)
            for rec in flows:
                url = rec.get('url')
                if not url:
                    continue
                headers = {'Content-Type': 'application/json'}
                if N8N_AUTH_ENABLED and N8N_WEBHOOK_TOKEN:
                    headers['Authorization'] = f'Bearer {N8N_WEBHOOK_TOKEN}'
                try:
                    start = time.time()
                    resp = await httpx_client.post(url, headers=headers, json={})
                    latency_ms = int((time.time() - start) * 1000)
                    ok = resp.status_code < 400
                    hint = _n8n_hint_for_response(resp.status_code, resp.text)
                    await log_audit(AuditEntry(action='n8n_cron_check', method='POST', path=url[:40]+'...', success=ok, upstream_status=resp.status_code, error=None if ok else hint))
                except Exception as e:
                    await log_audit(AuditEntry(action='n8n_cron_check', method='POST', path=url[:40]+'...', success=False, upstream_status=None, error=str(e)[:300]))
        except Exception:
            pass
        await asyncio.sleep(900)

@app.on_event("startup")
async def _maybe_start_cron():
    # Opt-in via env N8N_CRON_ENABLED=true if needed
    if (os.environ.get('N8N_CRON_ENABLED', 'false').lower() in ('1','true','enabled','yes')):
        asyncio.create_task(_cron_n8n_health())

# --- Audit queries ---
@api_router.get("/audit")
async def get_audit(limit: int = 50, skip: int = 0):
    cursor = db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    for it in items:
        if isinstance(it.get('timestamp'), str):
            it['timestamp'] = it['timestamp']
    return {"items": items, "skip": skip, "limit": limit}

# --- Daily report ---
@api_router.get("/report/daily")
async def daily_report():
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    cursor = db.audit_logs.find({"timestamp": {"$gte": start.isoformat()}}, {"_id": 0})
    items = await cursor.to_list(length=1000)
    actions = [f"{it.get('event') or it.get('action')} {it.get('agent') or it.get('agent_id')}".strip() for it in items]
    errors = []
    agents_data: List[Dict[str, Any]] = []
    try:
        list_resp = await upstream_request('GET', '/agents/list')
        agents_list = list_resp['data'] if isinstance(list_resp['data'], list) else list_resp['data'].get('agents', [])
        for a in agents_list:
            if isinstance(a, dict):
                agents_data.append({'name': a.get('name') or a.get('agent_id') or a.get('id'), 'state': a.get('state') or a.get('status') or 'unknown', 'uptime': a.get('uptime') or a.get('metrics', {}).get('uptime')})
            else:
                agents_data.append({'name': str(a), 'state': 'unknown'})
    except Exception:
        pass
    next_steps = ["connect n8n flows (trade_alerts_flow, crystal_autopost, legal_guard, auto_restart)", "rotate API key in 30 days"]
    return {"actionsPerformed": actions[:10], "agents": agents_data, "errors": errors[:10], "nextSteps": next_steps}

# --- OpenAPI YAML ---
@api_router.get("/openapi.yaml")
async def openapi_yaml():
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(title="Blaxing Orchestrator API", version="1.0.0", description="Emergent-powered orchestration for Blaxing", routes=app.routes)
    text = yaml.dump(schema, sort_keys=False)
    from fastapi.responses import Response
    return Response(content=text, media_type="application/x-yaml")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await httpx_client.aclose()
    except Exception:
        pass
    client.close()