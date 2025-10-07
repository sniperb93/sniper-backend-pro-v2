from fastapi import FastAPI, APIRouter, HTTPException
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


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# ---------- Helpers for datetime serialization ----------

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
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field

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
    state: str = Field(default="sleep")  # "active" | "sleep"
    uptime: int = 0  # seconds (computed server-side)
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None


# ---------- Seed Data ----------

DEFAULT_AGENTS = [
    {
        "agent_id": "sniper",
        "name": "Sniper",
        "image": "blaxing/sniper:latest",
    },
    {
        "agent_id": "crystal",
        "name": "Crystal",
        "image": "blaxing/crystal:latest",
    },
    {
        "agent_id": "sonia",
        "name": "Sonia",
        "image": "blaxing/sonia:latest",
    },
    {
        "agent_id": "corerouter",
        "name": "CoreRouter",
        "image": "blaxing/corerouter:latest",
    },
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


# ---------- Routes ----------

@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)

    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()

    _ = await db.status_checks.insert_one(doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)

    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check.get('timestamp'), str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])

    return status_checks


# ---- Agent Manager (Mock) ----

async def compute_uptime(doc: Dict[str, Any]) -> int:
    if doc.get("state") != "active":
        return 0
    act = parse_iso(doc.get("activated_at"))
    if not act:
        return 0
    return max(0, int((datetime.now(timezone.utc) - act).total_seconds()))


def parse_agent(doc: Dict[str, Any]) -> Agent:
    # Convert ISO string fields to datetime objects
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


@api_router.get("/agents/list", response_model=List[Agent])
async def list_agents():
    await ensure_seed_agents()
    items = await db.agents.find({}, {"_id": 0}).to_list(length=None)
    # Compute uptime live
    result: List[Agent] = []
    for it in items:
        it = dict(it)
        it["uptime"] = await compute_uptime(it)
        result.append(parse_agent(it))
    return result


@api_router.post("/agents/register", response_model=Agent)
async def register_agent(payload: AgentCreate):
    # Upsert by agent_id
    existing = await db.agents.find_one({"agent_id": payload.agent_id}, {"_id": 0})
    now = now_iso()
    base_doc = {
        "agent_id": payload.agent_id,
        "name": payload.name or payload.agent_id.capitalize(),
        "image": payload.image,
        "env": payload.env or {},
        "state": "sleep",
        "created_at": now,
        "updated_at": now,
        "activated_at": None,
        "last_heartbeat": None,
    }
    if existing:
        # Keep original created_at
        base_doc["created_at"] = existing.get("created_at", now)
    await db.agents.update_one(
        {"agent_id": payload.agent_id},
        {"$set": base_doc},
        upsert=True,
    )
    doc = await db.agents.find_one({"agent_id": payload.agent_id}, {"_id": 0})
    # Attach computed uptime
    doc = dict(doc)
    doc["uptime"] = await compute_uptime(doc)
    return parse_agent(doc)


@api_router.post("/agents/{agent_id}/activate")
async def activate_agent(agent_id: str):
    doc = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    now = now_iso()
    await db.agents.update_one(
        {"agent_id": agent_id},
        {"$set": {"state": "active", "activated_at": now, "updated_at": now}}
    )
    return {"ok": True, "agent_id": agent_id, "state": "active"}


@api_router.post("/agents/{agent_id}/deactivate")
async def deactivate_agent(agent_id: str):
    doc = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    now = now_iso()
    await db.agents.update_one(
        {"agent_id": agent_id},
        {"$set": {"state": "sleep", "updated_at": now}}
    )
    return {"ok": True, "agent_id": agent_id, "state": "sleep"}


@api_router.get("/agents/{agent_id}/status")
async def agent_status(agent_id: str):
    doc = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    uptime = await compute_uptime(doc)
    return {
        "agent_id": agent_id,
        "state": doc.get("state", "sleep"),
        "uptime": uptime,
        "status": "ok",
    }


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
