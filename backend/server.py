@@
 from typing import List, Optional, Dict, Any
@@
 import json
+import time
@@
 class N8nFlowUpsert(BaseModel):
     flow: str
     url: str
+
+class N8nDiagnosticsRequest(BaseModel):
+    url: str
+    payload: Dict[str, Any] = Field(default_factory=dict)
@@
 @api_router.post("/n8n/flows/trigger/{flow}")
 async def n8n_flows_trigger(flow: str, payload: Optional[Dict[str, Any]] = None):
@@
     return await n8n_trigger_url(body)
+
+def _n8n_hint_for_response(code: int, body_text: str) -> str:
+    txt = (body_text or '').lower()
+    if code == 404 and 'webhook' in txt and 'register' in txt:
+        return "Webhook non armé. Cliquez sur 'Execute Workflow' dans n8n, ou utilisez l'URL /webhook avec le workflow activé."
+    if code in (401, 403):
+        return "Non autorisé. Vérifiez l'authentification/ACL côté n8n."
+    if code in (502, 503, 504):
+        return "Service n8n indisponible. Réessayez plus tard ou vérifiez le service."
+    if code >= 400:
+        return "Erreur côté n8n. Vérifiez l'URL exacte et l'état du workflow."
+    return "OK"
+
+@api_router.post("/n8n/diagnostics")
+async def n8n_diagnostics(body: N8nDiagnosticsRequest):
+    url = body.url
+    if not (url and (url.startswith('http://') or url.startswith('https://'))):
+        raise HTTPException(status_code=400, detail="Invalid URL")
+    headers = {'Content-Type': 'application/json'}
+    if N8N_WEBHOOK_AUTH:
+        headers['Authorization'] = N8N_WEBHOOK_AUTH
+    started = time.time()
+    try:
+        resp = await httpx_client.post(url, headers=headers, json=body.payload)
+        latency_ms = int((time.time() - started) * 1000)
+        text = resp.text
+        hint = _n8n_hint_for_response(resp.status_code, text)
+        details = text[:500]
+        status = 'ok' if resp.status_code < 400 else 'error'
+        await log_audit(AuditEntry(action='n8n_diagnostics', method='POST', path=url[:40]+'...', success=(status=='ok'), upstream_status=resp.status_code, error=None if status=='ok' else details))
+        return {
+            'status': status,
+            'http_code': resp.status_code,
+            'latency_ms': latency_ms,
+            'hint': hint,
+            'details': f"Response: {details}"
+        }
+    except httpx.RequestError as e:
+        latency_ms = int((time.time() - started) * 1000)
+        await log_audit(AuditEntry(action='n8n_diagnostics', method='POST', path=url[:40]+'...', success=False, upstream_status=None, error=str(e)[:300]))
+        return {
+            'status': 'error',
+            'http_code': 0,
+            'latency_ms': latency_ms,
+            'hint': 'Impossible de joindre n8n (réseau/host).',
+            'details': str(e)
+        }
*** End Patch