import { useEffect, useMemo, useState } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster, toast } from "sonner";
import AgentBuilderPanel from "@/components/AgentBuilderPanel.jsx";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const defaultAgents = ["sniper", "crystal", "sonia", "corerouter"];
const N8N_ABS_BASE = "http://31.97.193.13:5678/webhook-test";

function useApi() {
  const api = useMemo(() => {
    const instance = axios.create({ baseURL: API, timeout: 20000 });
    return instance;
  }, []);
  return api;
}

function Section({ title, children }) {
  return (
    <div className="section">
      <h2 className="section-title" data-testid="section-title">{title}</h2>
      <div className="section-body">{children}</div>
    </div>
  );
}

export default function App() {
  const api = useApi();
  const [config, setConfig] = useState({ hasKey: false, dryRun: true });
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [audit, setAudit] = useState([]);
  const [flow, setFlow] = useState("");
  const [flowPayload, setFlowPayload] = useState("{\n  \"demo\": true\n}");
  const [absUrl, setAbsUrl] = useState("");
  const [absPayload, setAbsPayload] = useState("{\n  \"demo\": true\n}");
  const [log, setLog] = useState("");

  const logLine = (msg) => setLog((l) => `${new Date().toLocaleTimeString()} - ${msg}\n${l}`);

  const fetchConfig = async () => {
    try {
      const { data } = await api.get(`/config`);
      setConfig(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const { data } = await api.get(`/agents/list`);
      const arr = Array.isArray(data) ? data : data.agents || [];
      setAgents(arr);
      logLine("Fetched agents list");
    } catch (e) {
      console.error(e);
      logLine("Failed to fetch agents list");
    } finally {
      setLoading(false);
    }
  };

  const fetchAudit = async () => {
    try {
      const { data } = await api.get(`/audit?limit=20`);
      setAudit(data.items || []);
    } catch (e) {
      console.error(e);
    }
  };

  const agentAction = async (id, action) => {
    try {
      setLoading(true);
      const { data } = await api.post(`/agents/${id}/${action}`);
      logLine(`${action} ${id}: ${JSON.stringify(data)}`);
      await fetchAudit();
    } catch (e) {
      console.error(e);
      logLine(`${action} ${id} failed`);
    } finally {
      setLoading(false);
    }
  };

  const globalAction = async (action) => {
    try {
      setLoading(true);
      const { data } = await api.post(`/agents/${action}`);
      logLine(`${action}: ${JSON.stringify(data)}`);
      await fetchAudit();
    } catch (e) {
      console.error(e);
      logLine(`${action} failed`);
    } finally {
      setLoading(false);
    }
  };

  const registerAgent = async () => {
    const agent_id = window.prompt("Agent ID? e.g., sniper");
    if (!agent_id) return;
    const image = window.prompt("Docker image? e.g., blaxing/sniper:latest", "blaxing/sniper:latest");
    if (!image) return;
    let env = {};
    try {
      const payload = window.prompt("ENV JSON (optional)", "{\n  \"MODE\": \"prod\"\n}");
      env = payload ? JSON.parse(payload) : {};
    } catch (e) { alert("Invalid JSON for env"); return; }

    try {
      setLoading(true);
      const { data } = await api.post(`/agents/register`, { agent_id, image, env });
      logLine(`register ${agent_id}: ${JSON.stringify(data)}`);
      await fetchAudit();
    } catch (e) {
      console.error(e);
      logLine(`register ${agent_id} failed`);
    } finally {
      setLoading(false);
    }
  };

  const triggerFlow = async () => {
    if (!flow) { alert("Enter flow name"); return; }
    let json = {};
    try { json = JSON.parse(flowPayload || "{}"); } catch (e) { alert("Invalid JSON"); return; }
    try {
      setLoading(true);
      const { data } = await api.post(`/n8n/trigger/${encodeURIComponent(flow)}`, json);
      toast.success(`Flow triggered: ${flow}`);
      logLine(`n8n ${flow}: ${JSON.stringify(data)}`);
      await fetchAudit();
    } catch (e) {
      console.error(e);
      toast.error(`Trigger failed: ${e?.response?.data?.detail || e?.message || "Unknown error"}`);
      logLine(`n8n ${flow} failed`);
    } finally {
      setLoading(false);
    }
  };

  const postTriggerUrl = async (url, flowNameForUi) => {
    try {
      setLoading(true);
      const { data } = await api.post(`/n8n/trigger-url`, { url });
      toast.success(`Flow triggered: ${flowNameForUi}`);
      logLine(`n8n-absolute ${flowNameForUi}: ${JSON.stringify(data)}`);
      await fetchAudit();
    } catch (e) {
      console.error("[Blaxing Error - Quick Flow]", e?.response?.data || e);
      toast.error(`Trigger failed: ${e?.response?.data?.detail || e?.message || "Unknown error"}`);
      logLine(`n8n-absolute ${flowNameForUi} failed`);
    } finally {
      setLoading(false);
    }
  };

  const triggerAbsolute = async () => {
    if (!absUrl) { alert("Enter absolute webhook URL"); return; }
    let payload = {};
    try { payload = JSON.parse(absPayload || "{}"); } catch (e) { alert("Invalid JSON"); return; }
    try {
      setLoading(true);
      const { data } = await api.post(`/n8n/trigger-url`, { url: absUrl, payload });
      toast.success("Flow triggered via absolute URL");
      logLine(`n8n-absolute: ${JSON.stringify(data)}`);
      await fetchAudit();
    } catch (e) {
      console.error(e);
      toast.error(`Trigger failed: ${e?.response?.data?.detail || e?.message || "Unknown error"}`);
      logLine(`n8n-absolute failed`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
    fetchAgents();
    fetchAudit();
    const t = setInterval(() => { fetchAgents(); fetchAudit(); }, 30000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="App">
      <Toaster position="top-right" richColors />
      <header className="App-header">
        <a className="App-link" href="https://emergent.sh" target="_blank" rel="noopener noreferrer">
          <img alt="Emergent" src="https://avatars.githubusercontent.com/in/1201222?s=120&u=2686cf91179bbafbc7a71bfbc43004cf9ae1acea&v=4" />
        </a>
        <p className="mt-5">Blaxing Orchestration Dashboard</p>
      </header>

      <div className="container">
        <Section title="Configuration">
          <div className="kv">
            <div data-testid="config-has-key">API Key: {config.hasKey ? 'present' : 'missing'}</div>
            <div data-testid="config-dry-run">Dry-Run: {String(config.dryRun)}</div>
            <div data-testid="config-agent-base">Agent Manager: {config.agentManagerBase}</div>
            <div data-testid="config-n8n-base">n8n Webhook: {config.n8nWebhookBase || 'not set'}</div>
          </div>
        </Section>

        <Section title="Agents">
          <div className="actions">
            <button data-testid="activate-all-btn" disabled={loading} onClick={() => globalAction('activate-all')}>Activate All</button>
            <button data-testid="deactivate-all-btn" disabled={loading} onClick={() => globalAction('deactivate-all')}>Deactivate All</button>
            <button data-testid="register-agent-btn" disabled={loading} onClick={registerAgent}>Register Agent</button>
            <button data-testid="refresh-agents-btn" disabled={loading} onClick={fetchAgents}>Refresh</button>
          </div>
          <div className="agents-grid">
            {(agents.length ? agents : defaultAgents).map((a, idx) => {
              const item = typeof a === 'string' ? { name: a } : a;
              const id = item.name || item.agent_id || item.id || `agent-${idx}`;
              const state = item.state || item.status || 'unknown';
              return (
                <div className="agent-card" key={id} data-testid={`agent-card-${id}`}>
                  <div className="agent-name">{id}</div>
                  <div className={`agent-state state-${state}`} data-testid={`agent-state-${id}`}>{state}</div>
                  <div className="agent-actions">
                    <button data-testid={`activate-${id}`} disabled={loading} onClick={() => agentAction(id, 'activate')}>Activate</button>
                    <button data-testid={`deactivate-${id}`} disabled={loading} onClick={() => agentAction(id, 'deactivate')}>Deactivate</button>
                  </div>
                </div>
              );
            })}
          </div>
        </Section>

        <Section title="n8n Webhook Trigger (flow)">
          <div className="n8n-form">
            <input data-testid="n8n-flow-input" placeholder="workflow name e.g., trade_alerts_flow" value={flow} onChange={(e) => setFlow(e.target.value)} />
            <textarea data-testid="n8n-payload-input" rows={6} value={flowPayload} onChange={(e) => setFlowPayload(e.target.value)} />
            <button data-testid="n8n-trigger-btn" disabled={loading} onClick={triggerFlow}>Trigger Flow</button>
          </div>
        </Section>

        <Section title="n8n Absolute Webhook URL">
          <div className="n8n-form">
            <input data-testid="n8n-abs-url-input" placeholder="https://host:5678/webhook-test/&lt;token&gt;" value={absUrl} onChange={(e) => setAbsUrl(e.target.value)} />
            <textarea data-testid="n8n-abs-payload-input" rows={6} value={absPayload} onChange={(e) => setAbsPayload(e.target.value)} />
            <button data-testid="n8n-abs-trigger-btn" disabled={loading} onClick={triggerAbsolute}>Trigger Absolute</button>
          </div>
        </Section>

        <Section title="Quick n8n Flows">
          <div className="quick-actions">
            <button data-testid="n8n-trade-btn" disabled={loading} onClick={() => postTriggerUrl(`${N8N_ABS_BASE}/trade_alerts_flow`, 'trade_alerts_flow')}>⚡ Trade Alerts Flow</button>
            <button data-testid="n8n-crystal-btn" disabled={loading} onClick={() => postTriggerUrl(`${N8N_ABS_BASE}/crystal_autopost`, 'crystal_autopost')}>💅 Crystal AutoPost</button>
            <button data-testid="n8n-legal-btn" disabled={loading} onClick={() => postTriggerUrl(`${N8N_ABS_BASE}/legal_guard`, 'legal_guard')}>⚖️ Legal Guard</button>
            <button data-testid="n8n-restart-btn" disabled={loading} onClick={() => postTriggerUrl(`${N8N_ABS_BASE}/auto_restart`, 'auto_restart')}>🔁 Auto Restart</button>
          </div>
        </Section>

        <Section title="Agent Builder">
          <AgentBuilderPanel />
        </Section>

        <Section title="Audit (latest)">
          <div className="audit-list" data-testid="audit-list">
            {audit.map((it) => (
              <div className="audit-row" key={it.id}>
                <div>{new Date(it.timestamp).toLocaleString()}</div>
                <div>{it.action || it.event}</div>
                <div>{it.agent_id || it.agent || '-'}</div>
                <div>{typeof it.success === 'boolean' ? (it.success ? 'ok' : 'err') : '-'}</div>
                <div>{it.upstream_status || '-'}</div>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Activity Log">
          <pre data-testid="activity-log" className="logbox">{log}</pre>
        </Section>
      </div>
    </div>
  );
}