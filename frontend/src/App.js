@@
-import AgentBuilderPanel from "@/components/AgentBuilderPanel.jsx";
+import AgentBuilderPanel from "@/components/AgentBuilderPanel.jsx";
@@
-const N8N_ABS_BASE = "http://31.97.193.13:5678/webhook-test";
+// Removed hardcoded N8N base to respect env rules. Flows are configured server-side in DB.
@@
   const [flow, setFlow] = useState("");
   const [flowPayload, setFlowPayload] = useState("{\n  \"demo\": true\n}");
   const [absUrl, setAbsUrl] = useState("");
   const [absPayload, setAbsPayload] = useState("{\n  \"demo\": true\n}");
   const [log, setLog] = useState("");
+  const [flows, setFlows] = useState([]);
+  const [flowInputs, setFlowInputs] = useState({
+    trade_alerts_flow: "",
+    crystal_autopost: "",
+    legal_guard: "",
+    auto_restart: ""
+  });
@@
   const fetchAudit = async () => {
@@
   };
+
+  const fetchFlows = async () => {
+    try {
+      const { data } = await api.get(`/n8n/flows/list`);
+      setFlows(data.flows || []);
+      const next = { ...flowInputs };
+      for (const f of data.flows || []) {
+        if (next[f.flow] !== undefined) next[f.flow] = f.url || "";
+      }
+      setFlowInputs(next);
+    } catch (e) {
+      console.error(e);
+    }
+  };
@@
   useEffect(() => {
     fetchConfig();
     fetchAgents();
     fetchAudit();
+    fetchFlows();
     const t = setInterval(() => { fetchAgents(); fetchAudit(); }, 30000);
     return () => clearInterval(t);
   }, []);
@@
-  const postTriggerUrl = async (url, flowNameForUi) => {
+  const postTriggerUrl = async (url, flowNameForUi) => {
@@
   };
+
+  const saveFlowUrl = async (flowName) => {
+    const url = flowInputs[flowName];
+    if (!url) { toast.error("URL requise"); return; }
+    try {
+      await api.post(`/n8n/flows/upsert`, { flow: flowName, url });
+      toast.success(`Flow ${flowName} enregistré`);
+      await fetchFlows();
+    } catch (e) {
+      console.error(e);
+      toast.error("Echec d'enregistrement du flow");
+    }
+  };
+
+  const triggerNamedFlow = async (flowName) => {
+    try {
+      setLoading(true);
+      const payload = {};
+      const { data } = await api.post(`/n8n/flows/trigger/${encodeURIComponent(flowName)}`, payload);
+      toast.success(`Flow triggered: ${flowName}`);
+      logLine(`n8n-named ${flowName}: ${JSON.stringify(data)}`);
+      await fetchAudit();
+    } catch (e) {
+      console.error(e);
+      toast.error(`Trigger failed: ${e?.response?.data?.detail || e?.message || "Unknown error"}`);
+      logLine(`n8n-named ${flowName} failed`);
+    } finally {
+      setLoading(false);
+    }
+  };
@@
-        <Section title="Quick n8n Flows">
-          <div className="quick-actions">
-            <button data-testid="n8n-trade-btn" disabled={loading} onClick={() => postTriggerUrl(`${N8N_ABS_BASE}/trade_alerts_flow`, 'trade_alerts_flow')}>⚡ Trade Alerts Flow</button>
-            <button data-testid="n8n-crystal-btn" disabled={loading} onClick={() => postTriggerUrl(`${N8N_ABS_BASE}/crystal_autopost`, 'crystal_autopost')}>💅 Crystal AutoPost</button>
-            <button data-testid="n8n-legal-btn" disabled={loading} onClick={() => postTriggerUrl(`${N8N_ABS_BASE}/legal_guard`, 'legal_guard')}>⚖️ Legal Guard</button>
-            <button data-testid="n8n-restart-btn" disabled={loading} onClick={() => postTriggerUrl(`${N8N_ABS_BASE}/auto_restart`, 'auto_restart')}>🔁 Auto Restart</button>
-          </div>
-        </Section>
+        <Section title="Quick n8n Flows (config + trigger)">
+          <div className="quick-actions" style={{gap:12, display:'flex', flexWrap:'wrap'}}>
+            {Object.keys(flowInputs).map((fname) => (
+              <div key={fname} className="bg-[#0b1220] p-3 rounded-lg" data-testid={`n8n-flow-card-${fname}`}>
+                <div className="mb-2 font-semibold">{fname}</div>
+                <input
+                  data-testid={`n8n-flow-url-input-${fname}`}
+                  placeholder="http://host:5678/webhook(-test)/<token>"
+                  value={flowInputs[fname]}
+                  onChange={(e) => setFlowInputs(prev => ({...prev, [fname]: e.target.value}))}
+                  className="p-2 rounded bg-gray-700 text-white"
+                  style={{minWidth: 360}}
+                />
+                <div className="mt-2" style={{display:'flex', gap:8}}>
+                  <button data-testid={`n8n-flow-save-${fname}`} disabled={loading} onClick={() => saveFlowUrl(fname)}>Enregistrer</button>
+                  <button data-testid={`n8n-flow-trigger-${fname}`} disabled={loading} onClick={() => triggerNamedFlow(fname)}>Déclencher</button>
+                </div>
+              </div>
+            ))}
+          </div>
+        </Section>
*** End Patch