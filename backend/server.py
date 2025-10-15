from fastapi import FastAPI, APIRouter, HTTPException, Header
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
import requests


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# External endpoints (not internal service URLs)
BLAXING_API_BASE = os.environ.get("BLAXING_API_BASE", "https://blaxing.fr/api")
BLAXING_STAGING_API_BASE = os.environ.get("BLAXING_STAGING_API_BASE", "https://staging.blaxing.fr/api")
N8N_WEBHOOK_BASE = os.environ.get("N8N_WEBHOOK_BASE", "https://n8n.blaxing.fr/webhook")
REQ_TIMEOUT = 10
EMERGENT_DRY_RUN = os.environ.get("EMERGENT_DRY_RUN", "true").lower() == "true"

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# ---------- Helpers ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
    if dt_str is None:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


# ---------- Models ----------

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


class AgentCreate(BaseModel):
    agent_id: str
    image: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    name: Optional[str] = None


class Agent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    agent_id: str
    name: str
    image: Optional[str] = None
    env: Dict[str, str] = Field(default_factory=dict)
    state: str = Field(default="sleep")
    uptime: int = 0
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None


class HooksConfig(BaseModel):
    activation_flow: Optional[str] = None
    deactivation_flow: Optional[str] = None
    status_change_flow: Optional[str] = None


class HookNotifyRequest(BaseModel):
    flow: str
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)


class TriggerUrlRequest(BaseModel):
    url: str
    payload: Optional[Dict[str, Any]] = None


# ---------- Seed Data ----------

DEFAULT_AGENTS = [
    {"agent_id": "sniper", "name": "Sniper", "image": "blaxing/sniper:latest"},
    {"agent_id": "crystal", "name": "Crystal", "image": "blaxing/crystal:latest"},
    {"agent_id": "sonia", "name": "Sonia", "image": "blaxing/sonia:latest"},
    {"agent_id": "corerouter", "name": "CoreRouter", "image": "blaxing/corerouter:latest"},
]


async def ensure_seed_agents():
    try:
        count = await db.agents.count_documents({})
        if count == 0:
            now = now_iso()
            docs = []
            for a in DEFAULT_AGENTS:
                docs.append({
                    "agent_id": a["agent_id"],
                    "name": a.get("name", a["agent_id"].capitalize()),
                    "image": a.get("image"),
                    "env": {},
                    "state": "sleep",
                    "created_at": now,
                    "updated_at": now,
                    "activated_at": None,
                    "last_heartbeat": None,
                })
            if docs:
                await db.agents.insert_many(docs)
    except Exception as e:
        logger.exception(f"Seeding agents failed: {e}")


# ---------- N8N helpers ----------

def n8n_target(flow: str, custom_base: Optional[str] = None) -> str:
    base = (custom_base or N8N_WEBHOOK_BASE).rstrip('/')
    return f"{base}/{flow}"


def send_n8n(flow: str, payload: Dict[str, Any], custom_base: Optional[str] = None) -> Dict[str, Any]:
    url = n8n_target(flow, custom_base)
    if EMERGENT_DRY_RUN:
        return {"ok": True, "dry_run": True, "url": url, "payload": payload}
    try:
        resp = requests.post(url, json=payload, timeout=REQ_TIMEOUT)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=f"n8n error: {resp.text}")
        return {"ok": True, "status": resp.status_code}
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="n8n timeout")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"n8n upstream error: {str(e)}")


def trigger_url(url: str, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    body = payload or {"source": "dashboard", "timestamp": now_iso()}
    if EMERGENT_DRY_RUN:
        logger.info(f"n8n_trigger_url ok url={url} dry_run=True")
        return {"ok": True, "dry_run": True, "url": url, "payload": body, "message": "Workflow was started"}
    try:
        resp = requests.post(url, json=body, timeout=REQ_TIMEOUT)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=f"n8n error: {resp.text}")
        logger.info(f"n8n_trigger_url ok url={url} status={resp.status_code}")
        return {"ok": True, "status": resp.status_code, "message": "Workflow was started"}
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="n8n timeout")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"n8n upstream error: {str(e)}")


async def get_hooks_config() -> HooksConfig:
    doc = await db.config.find_one({"_id": "webhooks"}, {"_id": 0})
    if not doc:
        return HooksConfig()
    return HooksConfig(**doc)


async def set_hooks_config(cfg: HooksConfig) -> HooksConfig:
    await db.config.update_one({"_id": "webhooks"}, {"$set": cfg.model_dump()}, upsert=True)
    return await get_hooks_config()


async def emit_event(flow: Optional[str], event: str, data: Dict[str, Any]):
    if not flow:
        return {"ok": True, "skipped": True, "reason": "no-flow"}
    payload = {"event": event, "data": data, "timestamp": now_iso()}
    try:
        return send_n8n(flow, payload)
    except HTTPException as e:
        logger.warning(f"n8n emit failed: {e.detail}")
        return {"ok": False, "error": e.detail}


# ---------- Routes ----------

@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check.get('timestamp'), str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks


# ---- Agent Manager (Mock + Optional Remote Proxy) ----

async def compute_uptime(doc: Dict[str, Any]) -> int:
    if doc.get("state") != "active":
        return 0
    act = parse_iso(doc.get("activated_at"))
    if not act:
        return 0
    return max(0, int((datetime.now(timezone.utc) - act).total_seconds()))


def parse_agent(doc: Dict[str, Any]) -> Agent:
    parsed = dict(doc)
    for k in ["created_at", "updated_at", "activated_at", "last_heartbeat"]:
        if isinstance(parsed.get(k), str):
            parsed[k] = parse_iso(parsed[k])
    return Agent(
        agent_id=parsed["agent_id"],
        name=parsed.get("name", parsed["agent_id"].capitalize()),
        image=parsed.get("image"),
        env=parsed.get("env", {}),
        state=parsed.get("state", "sleep"),
        uptime=parsed.get("uptime", 0),
        created_at=parsed.get("created_at") or datetime.now(timezone.utc),
        updated_at=parsed.get("updated_at") or datetime.now(timezone.utc),
        activated_at=parsed.get("activated_at"),
        last_heartbeat=parsed.get("last_heartbeat"),
    )


def resolve_base_from_header(source: str, header_base: Optional[str]) -> str:
    if header_base:
        return header_base.strip()
    if source == "staging":
        return BLAXING_STAGING_API_BASE
    return BLAXING_API_BASE


def forward_blaxing(method: str, path: str, api_key: Optional[str], source: str, header_base: Optional[str], json: Optional[dict] = None):
    key = api_key or os.environ.get("BLA_API_KEY")
    if not key:
        raise HTTPException(status_code=401, detail="X-API-KEY required for prod/staging mode")
    base = resolve_base_from_header(source, header_base)
    url = f"{base}{path}"
    headers = {"X-API-KEY": key}
    try:
        resp = requests.request(method, url, json=json, headers=headers, timeout=REQ_TIMEOUT)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json() if resp.text else {}
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")


@api_router.get("/agents/list", response_model=List[Agent])
async def list_agents(x_blaxing_source: Optional[str] = Header(default="mock"), x_api_key: Optional[str] = Header(default=None), x_blaxing_base: Optional[str] = Header(default=None)):
    src = (x_blaxing_source or "mock").lower()
    if src in ("prod", "staging"):
        try:
            data = forward_blaxing("GET", "/agents/list", x_api_key, src, x_blaxing_base)
            items = []
            for it in data or []:
                items.append(parse_agent({
                    "agent_id": it.get("agent_id") or it.get("id") or it.get("name"),
                    "name": it.get("name") or (it.get("agent_id") or "").capitalize(),
                    "image": it.get("image"),
                    "env": it.get("env") or {},
                    "state": it.get("state", "sleep"),
                    "uptime": it.get("uptime", 0),
                    "created_at": it.get("created_at") or now_iso(),
                    "updated_at": it.get("updated_at") or now_iso(),
                    "activated_at": it.get("activated_at"),
                    "last_heartbeat": it.get("last_heartbeat"),
                }))
            return items
        except HTTPException:
            pass
    await ensure_seed_agents()
    items = await db.agents.find({}, {"_id": 0}).to_list(length=None)
    result: List[Agent] = []
    for it in items:
        it = dict(it)
        it["uptime"] = await compute_uptime(it)
        result.append(parse_agent(it))
    return result


@api_router.get("/health")
async def health(x_blaxing_source: Optional[str] = Header(default="mock"), x_api_key: Optional[str] = Header(default=None), x_blaxing_base: Optional[str] = Header(default=None)):
    src = (x_blaxing_source or "mock").lower()
    if src in ("prod", "staging"):
        data = forward_blaxing("GET", "/health", x_api_key, src, x_blaxing_base)
        return {"status": data.get("status", "ok"), "source": src}
    return {"status": "ok", "source": "mock"}


@api_router.post("/agents/register", response_model=Agent)
async def register_agent(payload: AgentCreate, x_blaxing_source: Optional[str] = Header(default="mock"), x_api_key: Optional[str] = Header(default=None), x_blaxing_base: Optional[str] = Header(default=None)):
    src = (x_blaxing_source or "mock").lower()
    if src in ("prod", "staging"):
        if EMERGENT_DRY_RUN:
            return parse_agent({
                "agent_id": payload.agent_id,
                "name": payload.name or payload.agent_id.capitalize(),
                "image": payload.image,
                "env": payload.env or {},
                "state": "sleep",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "activated_at": None,
                "last_heartbeat": None,
                "uptime": 0,
            })
        data = forward_blaxing("POST", "/agents/register", x_api_key, src, x_blaxing_base, json=payload.model_dump())
        doc = {
            "agent_id": data.get("agent_id") or payload.agent_id,
            "name": data.get("name") or payload.name or payload.agent_id.capitalize(),
            "image": data.get("image"),
            "env": data.get("env") or {},
            "state": data.get("state", "sleep"),
            "created_at": data.get("created_at") or now_iso(),
            "updated_at": data.get("updated_at") or now_iso(),
            "activated_at": data.get("activated_at"),
            "last_heartbeat": data.get("last_heartbeat"),
            "uptime": data.get("uptime", 0),
        }
        return parse_agent(doc)

    existing = await db.agents.find_one({"agent_id": payload.agent_id}, {"_id": 0})
    now = now_iso()
    base_doc = {
        "agent_id": payload.agent_id,
        "name": payload.name or payload.agent_id.capitalize(),
        "image": payload.image,
        "env": payload.env or {},
        "state": "sleep",
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
        "activated_at": None,
        "last_heartbeat": None,
    }
    await db.agents.update_one({"agent_id": payload.agent_id}, {"$set": base_doc}, upsert=True)
    doc = await db.agents.find_one({"agent_id": payload.agent_id}, {"_id": 0})
    doc = dict(doc)
    doc["uptime"] = await compute_uptime(doc)
    return parse_agent(doc)


class CoreRouteRequest(BaseModel):
    agent: str
    action: str
    message: str


@api_router.post("/core-router")
async def core_router_route(body: CoreRouteRequest):
    # Minimal mock of CoreRouter behaviour
    payload = body.model_dump()
    agent = payload.get("agent", "").lower()
    routed = None
    if agent in {"sniper", "crystal", "sonia", "corerouter"}:
        routed = agent
    else:
        # naive routing by keywords
        text = (payload.get("message") or "").lower()
        if any(k in text for k in ["trade", "buy", "sell", "signal"]):
            routed = "sniper"
        elif any(k in text for k in ["legal", "contrat", "rgpd", "compliance"]):
            routed = "sonia"
        elif any(k in text for k in ["post", "tweet", "tiktok", "content", "publie"]):
            routed = "crystal"
        else:
            routed = "corerouter"
    return {
        "ok": True,
        "received": payload,
        "routed_to": routed,
    }


@api_router.post("/agents/activate-all")
async def activate_all(x_blaxing_source: Optional[str] = Header(default="mock"), x_api_key: Optional[str] = Header(default=None), x_blaxing_base: Optional[str] = Header(default=None)):
    src = (x_blaxing_source or "mock").lower()
    if src in ("prod", "staging"):
        if EMERGENT_DRY_RUN:
            return {"ok": True, "dry_run": True, "action": "activate-all"}
        _ = forward_blaxing("POST", "/agents/activate-all", x_api_key, src, x_blaxing_base)
        return {"ok": True, "action": "activate-all"}
    await ensure_seed_agents()
    now = now_iso()
    res = await db.agents.update_many({}, {"$set": {"state": "active", "activated_at": now, "updated_at": now}})
    return {"ok": True, "updated": res.modified_count, "state": "active"}


@api_router.post("/agents/deactivate-all")
async def deactivate_all(x_blaxing_source: Optional[str] = Header(default="mock"), x_api_key: Optional[str] = Header(default=None), x_blaxing_base: Optional[str] = Header(default=None)):
    src = (x_blaxing_source or "mock").lower()
    if src in ("prod", "staging"):
        if EMERGENT_DRY_RUN:
            return {"ok": True, "dry_run": True, "action": "deactivate-all"}
        _ = forward_blaxing("POST", "/agents/deactivate-all", x_api_key, src, x_blaxing_base)
        return {"ok": True, "action": "deactivate-all"}
    await ensure_seed_agents()
    now = now_iso()
    res = await db.agents.update_many({}, {"$set": {"state": "sleep", "updated_at": now}})
    return {"ok": True, "updated": res.modified_count, "state": "sleep"}


@api_router.post("/agents/{agent_id}/activate")
async def activate_agent(agent_id: str, x_blaxing_source: Optional[str] = Header(default="mock"), x_api_key: Optional[str] = Header(default=None), x_blaxing_base: Optional[str] = Header(default=None)):
    src = (x_blaxing_source or "mock").lower()
    if src in ("prod", "staging"):
        if EMERGENT_DRY_RUN:
            cfg = await get_hooks_config()
            await emit_event(cfg.activation_flow, "agent_activation", {"agent_id": agent_id, "source": src})
            return {"ok": True, "dry_run": True, "agent_id": agent_id, "state": "active"}
        _ = forward_blaxing("POST", f"/agents/{agent_id}/activate", x_api_key, src, x_blaxing_base)
        cfg = await get_hooks_config()
        await emit_event(cfg.activation_flow, "agent_activation", {"agent_id": agent_id, "source": src})
        return {"ok": True, "agent_id": agent_id, "state": "active"}

    doc = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    now = now_iso()
    await db.agents.update_one({"agent_id": agent_id}, {"$set": {"state": "active", "activated_at": now, "updated_at": now}})
    cfg = await get_hooks_config()
    await emit_event(cfg.activation_flow, "agent_activation", {"agent_id": agent_id, "source": "mock"})
    return {"ok": True, "agent_id": agent_id, "state": "active"}


@api_router.post("/agents/{agent_id}/deactivate")
async def deactivate_agent(agent_id: str, x_blaxing_source: Optional[str] = Header(default="mock"), x_api_key: Optional[str] = Header(default=None), x_blaxing_base: Optional[str] = Header(default=None)):
    src = (x_blaxing_source or "mock").lower()
    if src in ("prod", "staging"):
        if EMERGENT_DRY_RUN:
            cfg = await get_hooks_config()
            await emit_event(cfg.deactivation_flow, "agent_deactivation", {"agent_id": agent_id, "source": src})
            return {"ok": True, "dry_run": True, "agent_id": agent_id, "state": "sleep"}
        _ = forward_blaxing("POST", f"/agents/{agent_id}/deactivate", x_api_key, src, x_blaxing_base)
        cfg = await get_hooks_config()
        await emit_event(cfg.deactivation_flow, "agent_deactivation", {"agent_id": agent_id, "source": src})
        return {"ok": True, "agent_id": agent_id, "state": "sleep"}

    doc = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    now = now_iso()
    await db.agents.update_one({"agent_id": agent_id}, {"$set": {"state": "sleep", "updated_at": now}})
    cfg = await get_hooks_config()
    await emit_event(cfg.deactivation_flow, "agent_deactivation", {"agent_id": agent_id, "source": "mock"})
    return {"ok": True, "agent_id": agent_id, "state": "sleep"}


@api_router.get("/agents/{agent_id}/status")
async def agent_status(agent_id: str, x_blaxing_source: Optional[str] = Header(default="mock"), x_api_key: Optional[str] = Header(default=None), x_blaxing_base: Optional[str] = Header(default=None)):
    src = (x_blaxing_source or "mock").lower()
    if src in ("prod", "staging"):
        try:
            data = forward_blaxing("GET", f"/agents/{agent_id}/status", x_api_key, src, x_blaxing_base)
            state = data.get("state", "sleep")
            uptime = int(data.get("uptime", 0)) if str(data.get("uptime", "0")).isdigit() else 0
            cached = await db.agent_state_cache.find_one({"agent_id": agent_id}, {"_id": 0})
            if not cached or cached.get("state") != state:
                await db.agent_state_cache.update_one({"agent_id": agent_id}, {"$set": {"state": state, "updated_at": now_iso()}}, upsert=True)
                cfg = await get_hooks_config()
                await emit_event(cfg.status_change_flow, "status_change", {"agent_id": agent_id, "state": state, "source": src})
            return {"agent_id": agent_id, "state": state, "uptime": uptime, "status": data.get("status", "ok")}
        except HTTPException:
            pass

    doc = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    state = doc.get("state", "sleep")
    uptime = await compute_uptime(doc)
    cached = await db.agent_state_cache.find_one({"agent_id": agent_id}, {"_id": 0})
    if not cached or cached.get("state") != state:
        await db.agent_state_cache.update_one({"agent_id": agent_id}, {"$set": {"state": state, "updated_at": now_iso()}}, upsert=True)
        cfg = await get_hooks_config()
        await emit_event(cfg.status_change_flow, "status_change", {"agent_id": agent_id, "state": state, "source": "mock"})
    return {"agent_id": agent_id, "state": state, "uptime": uptime, "status": "ok"}


# ---- Hooks management ----

@api_router.get("/hooks/config", response_model=HooksConfig)
async def hooks_get_config():
    return await get_hooks_config()


@api_router.post("/hooks/config", response_model=HooksConfig)
async def hooks_set_config(cfg: HooksConfig):
    return await set_hooks_config(cfg)


@api_router.post("/hooks/notify")
async def hooks_notify(body: HookNotifyRequest):
    res = send_n8n(body.flow, {"event": body.event, "data": body.data, "timestamp": now_iso()})
    return res


@api_router.post("/n8n/trigger-url")
async def n8n_trigger_url(body: TriggerUrlRequest):
    return trigger_url(body.url, body.payload)


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
