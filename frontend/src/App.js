@@
   const [flows, setFlows] = useState([]);
@@
   const [diag, setDiag] = useState(null);
+  const HIDE_URLS = (process.env.REACT_APP_HIDE_URLS || import.meta.env.REACT_APP_HIDE_URLS) === 'true';
@@
-                <input
-                  data-testid={`n8n-flow-url-input-${fname}`}
-                  placeholder="http://host:5678/webhook(-test)/<token>"
-                  value={flowInputs[fname]}
-                  onChange={(e) => setFlowInputs(prev => ({...prev, [fname]: e.target.value}))}
-                  className="p-2 rounded bg-gray-700 text-white"
-                  style={{minWidth: 360}}
-                />
-                <div className="mt-2" style={{display:'flex', gap:8}}>
-                  <button data-testid={`n8n-flow-save-${fname}`} disabled={loading} onClick={() => saveFlowUrl(fname)}>Enregistrer</button>
+                {!HIDE_URLS && (
+                  <>
+                    <input
+                      data-testid={`n8n-flow-url-input-${fname}`}
+                      placeholder="http://host:5678/webhook(-test)/<token>"
+                      value={flowInputs[fname]}
+                      onChange={(e) => setFlowInputs(prev => ({...prev, [fname]: e.target.value}))}
+                      className="p-2 rounded bg-gray-700 text-white"
+                      style={{minWidth: 360}}
+                    />
+                    <div className="mt-2" style={{display:'flex', gap:8}}>
+                      <button data-testid={`n8n-flow-save-${fname}`} disabled={loading} onClick={() => saveFlowUrl(fname)}>Enregistrer</button>
+                    </div>
+                  </>
+                )}
+                <div className="mt-2" style={{display:'flex', gap:8}}>
                   <button data-testid={`n8n-flow-trigger-${fname}`} disabled={loading} onClick={() => triggerNamedFlow(fname)}>Déclencher</button>
                   <button data-testid={`n8n-flow-diagnose-${fname}`} disabled={loading} onClick={() => diagnoseFlow(fname)}>Diagnostiquer</button>
                 </div>
*** End Patch