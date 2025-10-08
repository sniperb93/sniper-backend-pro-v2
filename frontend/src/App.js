@@
   const [flows, setFlows] = useState([]);
   const [flowInputs, setFlowInputs] = useState({
     trade_alerts_flow: "",
     crystal_autopost: "",
     legal_guard: "",
     auto_restart: ""
   });
+  const [diag, setDiag] = useState(null);
@@
   const triggerNamedFlow = async (flowName) => {
@@
   };
+
+  const diagnoseFlow = async (flowName) => {
+    const url = flowInputs[flowName];
+    if (!url) { toast.error("URL requise"); return; }
+    try {
+      setLoading(true);
+      const { data } = await api.post(`/n8n/diagnostics`, { url, payload: {} });
+      setDiag({ flow: flowName, ...data });
+      const msg = data.status === 'ok' ? `OK (${data.http_code})` : `Erreur ${data.http_code}`;
+      toast[data.status === 'ok' ? 'success' : 'error'](`${flowName}: ${msg}`);
+      logLine(`diagnostics ${flowName}: ${JSON.stringify(data)}`);
+    } catch (e) {
+      console.error(e);
+      toast.error(`Diagnostics failed`);
+    } finally {
+      setLoading(false);
+    }
+  };
@@
             {Object.keys(flowInputs).map((fname) => (
               <div key={fname} className="bg-[#0b1220] p-3 rounded-lg" data-testid={`n8n-flow-card-${fname}`}>
                 <div className="mb-2 font-semibold">{fname}</div>
                 <input
@@
                 />
                 <div className="mt-2" style={{display:'flex', gap:8}}>
                   <button data-testid={`n8n-flow-save-${fname}`} disabled={loading} onClick={() => saveFlowUrl(fname)}>Enregistrer</button>
                   <button data-testid={`n8n-flow-trigger-${fname}`} disabled={loading} onClick={() => triggerNamedFlow(fname)}>Déclencher</button>
+                  <button data-testid={`n8n-flow-diagnose-${fname}`} disabled={loading} onClick={() => diagnoseFlow(fname)}>Diagnostiquer</button>
                 </div>
               </div>
             ))}
           </div>
+          {diag && (
+            <div className="mt-3 p-3 bg-[#0b1220] rounded-lg" data-testid="n8n-diagnostics-box">
+              <div><strong>Flow:</strong> {diag.flow}</div>
+              <div><strong>Status:</strong> {diag.status} (HTTP {diag.http_code})</div>
+              <div><strong>Latency:</strong> {diag.latency_ms} ms</div>
+              <div><strong>Hint:</strong> {diag.hint}</div>
+              <div className="text-xs text-gray-400 break-all"><strong>Détails:</strong> {diag.details}</div>
+            </div>
+          )}
         </Section>
*** End Patch