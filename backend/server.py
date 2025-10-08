@@
 N8N_WEBHOOK_BASE = os.environ.get('N8N_WEBHOOK_BASE', '')
-N8N_WEBHOOK_AUTH = os.environ.get('N8N_WEBHOOK_AUTH', '')
+N8N_WEBHOOK_AUTH = os.environ.get('N8N_WEBHOOK_AUTH', '')
+N8N_WEBHOOK_TOKEN = os.environ.get('N8N_WEBHOOK_TOKEN', '')
+N8N_AUTH_ENABLED = (N8N_WEBHOOK_AUTH or '').lower() == 'enabled'
@@
 DEFAULT_AGENTS_FILE = (ROOT_DIR.parent / 'emergent' / 'agents' / 'data' / 'agents.json').resolve()
+DEFAULT_FLOW_PAYLOADS: Dict[str, Any] = {
+    'trade_alerts_flow': {"symbol": "BTCUSDT", "signal": "buy"},
+    'crystal_autopost': {"message": "Nouvelle publication automatique"},
+    'legal_guard': {"case": "Rappel de droits utilisateur"},
+    'auto_restart': {"service": "Emergent Core"},
+}
+N8N_CRON_ENABLED = (os.environ.get('N8N_CRON_ENABLED', 'false') or '').lower() in ('1','true','enabled','yes')
+N8N_ALERT_WEBHOOK_URL = os.environ.get('N8N_ALERT_WEBHOOK_URL', '')
@@
-    if N8N_WEBHOOK_AUTH:
-        headers['Authorization'] = N8N_WEBHOOK_AUTH
+    if N8N_AUTH_ENABLED and N8N_WEBHOOK_TOKEN:
+        headers['Authorization'] = f'Bearer {N8N_WEBHOOK_TOKEN}'
@@
-    if N8N_WEBHOOK_AUTH:
-        headers['Authorization'] = N8N_WEBHOOK_AUTH
+    if N8N_AUTH_ENABLED and N8N_WEBHOOK_TOKEN:
+        headers['Authorization'] = f'Bearer {N8N_WEBHOOK_TOKEN}'
@@
-    if N8N_WEBHOOK_AUTH:
-        headers['Authorization'] = N8N_WEBHOOK_AUTH
+    if N8N_AUTH_ENABLED and N8N_WEBHOOK_TOKEN:
+        headers['Authorization'] = f'Bearer {N8N_WEBHOOK_TOKEN}'
@@
 async def n8n_flows_trigger(flow: str, payload: Optional[Dict[str, Any]] = None):
@@
-    body = N8nTriggerUrlPayload(url=rec.get("url"), payload=(payload or {}))
+    effective_payload = payload if (payload and len(payload) > 0) else DEFAULT_FLOW_PAYLOADS.get(flow, {})
+    body = N8nTriggerUrlPayload(url=rec.get("url"), payload=effective_payload)
     return await n8n_trigger_url(body)
@@
 app.add_middleware(
@@
     client.close()
+
+# Optional background diagnostics every 15 minutes
+import asyncio
+
+async def _cron_n8n_health():
+    while True:
+        try:
+            flows = await db.n8n_flows.find({}, {"_id": 0}).to_list(100)
+            for rec in flows:
+                url = rec.get('url')
+                if not url:
+                    continue
+                # inline diagnostics call
+                headers = {'Content-Type': 'application/json'}
+                if N8N_AUTH_ENABLED and N8N_WEBHOOK_TOKEN:
+                    headers['Authorization'] = f'Bearer {N8N_WEBHOOK_TOKEN}'
+                try:
+                    start = time.time()
+                    resp = await httpx_client.post(url, headers=headers, json=DEFAULT_FLOW_PAYLOADS.get(rec.get('flow'), {}))
+                    latency_ms = int((time.time() - start) * 1000)
+                    ok = resp.status_code < 400
+                    hint = _n8n_hint_for_response(resp.status_code, resp.text)
+                    await log_audit(AuditEntry(action='n8n_cron_check', method='POST', path=url[:40]+'...', success=ok, upstream_status=resp.status_code, error=None if ok else hint))
+                    if (not ok) and N8N_ALERT_WEBHOOK_URL:
+                        try:
+                            await httpx_client.post(N8N_ALERT_WEBHOOK_URL, json={"text": f"Flow {rec.get('flow')} down: {hint}", "latency_ms": latency_ms})
+                        except Exception:
+                            pass
+                except Exception as e:
+                    await log_audit(AuditEntry(action='n8n_cron_check', method='POST', path=url[:40]+'...', success=False, upstream_status=None, error=str(e)[:300]))
+        except Exception:
+            pass
+        await asyncio.sleep(900)
+
+@app.on_event("startup")
+async def _maybe_start_cron():
+    if N8N_CRON_ENABLED:
+        asyncio.create_task(_cron_n8n_health())
*** End Patch