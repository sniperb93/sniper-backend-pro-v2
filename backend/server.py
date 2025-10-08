@@
 from typing import List, Optional, Dict, Any
@@
 import yaml
 import json
@@
 class N8nTriggerUrlPayload(BaseModel):
     url: str
     payload: Dict[str, Any] = Field(default_factory=dict)
+
+class N8nFlowUpsert(BaseModel):
+    flow: str
+    url: str
@@
 @api_router.post("/n8n/trigger-url")
 async def n8n_trigger_url(body: N8nTriggerUrlPayload):
@@
         await log_audit(AuditEntry(action='n8n_trigger_url', method='POST', path=masked_path, success=False, error=str(e)[:400]))
         raise HTTPException(status_code=502, detail="Failed to reach n8n")
 
+@api_router.get("/n8n/flows/list")
+async def n8n_flows_list():
+    items = await db.n8n_flows.find({}, {"_id": 0}).to_list(200)
+    return {"flows": items}
+
+@api_router.post("/n8n/flows/upsert")
+async def n8n_flows_upsert(body: N8nFlowUpsert):
+    if not body.flow or not body.url:
+        raise HTTPException(status_code=400, detail="flow and url required")
+    doc = {"flow": body.flow, "url": body.url, "updated_at": datetime.now(timezone.utc).isoformat()}
+    await db.n8n_flows.update_one({"flow": body.flow}, {"$set": doc}, upsert=True)
+    await log_audit(AuditEntry(action='n8n_flow_upsert', method='POST', path='/n8n/flows/upsert', success=True, upstream_status=200))
+    return {"ok": True}
+
+@api_router.post("/n8n/flows/trigger/{flow}")
+async def n8n_flows_trigger(flow: str, payload: Dict[str, Any] | None = None):
+    rec = await db.n8n_flows.find_one({"flow": flow})
+    if not rec:
+        raise HTTPException(status_code=404, detail="Flow not configured")
+    body = N8nTriggerUrlPayload(url=rec.get("url"), payload=(payload or {}))
+    return await n8n_trigger_url(body)
+
*** End Patch