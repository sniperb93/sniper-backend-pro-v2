import React, { useEffect, useMemo, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Toaster } from "@/components/ui/toaster";
import { useToast } from "@/hooks/use-toast";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const useAgentsApi = (headers) => {
  const api = useMemo(() => axios.create({ baseURL: API }), []);
  // apply headers on each request
  useEffect(() => {
    api.defaults.headers.common = { ...api.defaults.headers.common, ...headers };
  }, [api, headers]);
  return {
    list: () => api.get("/agents/list").then((r) => r.data),
    register: (payload) => api.post("/agents/register", payload).then((r) => r.data),
    activate: (id) => api.post(`/agents/${id}/activate`).then((r) => r.data),
    deactivate: (id) => api.post(`/agents/${id}/deactivate`).then((r) => r.data),
    status: (id) => api.get(`/agents/${id}/status`).then((r) => r.data),
  };
};

const prettyUptime = (seconds = 0) => {
  const s = Number(seconds) || 0;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${sec}s`;
  return `${sec}s`;
};

const StatusPill = ({ state, id }) => (
  <Badge
    data-testid={`status-badge-${id}`}
    variant={state === "active" ? "secondary" : "outline"}
    className={
      state === "active"
        ? "bg-emerald-600/10 text-emerald-700 border-emerald-200"
        : "text-neutral-600 border-neutral-300"
    }
  >
    {state === "active" ? "Active" : "Sleep"}
  </Badge>
);

const AgentCard = ({ agent, onActivate, onDeactivate, onCheck }) => {
  return (
    <Card data-testid={`agent-card-${agent.agent_id}`} className="group relative overflow-hidden border-neutral-200 hover:border-neutral-300 transition-colors">
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold tracking-tight flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-100 to-rose-50 text-amber-700 ring-1 ring-amber-200">
            {agent.name.charAt(0)}
          </span>
          {agent.name}
        </CardTitle>
        <StatusPill state={agent.state} id={agent.agent_id} />
      </CardHeader>
      <CardContent className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="text-sm text-neutral-600" data-testid={`agent-id-${agent.agent_id}`}>ID: {agent.agent_id}</div>
          <div className="text-sm text-neutral-600" data-testid={`agent-uptime-${agent.agent_id}`}>Uptime: {prettyUptime(agent.uptime)}</div>
        </div>
        <div className="flex gap-2">
          <Button
            data-testid={`activate-btn-${agent.agent_id}`}
            onClick={() => onActivate(agent.agent_id)}
            className="rounded-full bg-emerald-600 text-white hover:bg-emerald-700"
          >
            Activate
          </Button>
          <Button
            data-testid={`deactivate-btn-${agent.agent_id}`}
            onClick={() => onDeactivate(agent.agent_id)}
            variant="outline"
            className="rounded-full border-neutral-300 hover:bg-neutral-100"
          >
            Deactivate
          </Button>
          <Button
            data-testid={`check-status-btn-${agent.agent_id}`}
            onClick={() => onCheck(agent.agent_id)}
            variant="ghost"
            className="rounded-full hover:bg-neutral-100"
          >
            Check
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const HeaderControls = ({ mode, setMode, apiKey, setApiKey, onApply }) => {
  return (
    <div className="flex items-center gap-3" data-testid="header-controls">
      <div className="w-40">
        <Select value={mode} onValueChange={setMode}>
          <SelectTrigger data-testid="mode-select-trigger">
            <SelectValue placeholder="Mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem data-testid="mode-option-mock" value="mock">Mock</SelectItem>
            <SelectItem data-testid="mode-option-prod" value="prod">Prod</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Input
        data-testid="api-key-input"
        type="password"
        placeholder="X-API-KEY"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        className="w-64"
      />
      <Button data-testid="apply-headers-btn" className="rounded-full bg-stone-900 text-white hover:bg-stone-800" onClick={onApply}>Apply</Button>
    </div>
  );
};

const Dashboard = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState([]);
  const [mode, setMode] = useState("mock");
  const [apiKey, setApiKey] = useState("");
  const [headers, setHeaders] = useState({ "x-blaxing-source": "mock" });
  const api = useAgentsApi(headers);

  const applyHeaders = () => {
    const base = { "x-blaxing-source": mode };
    const hdrs = apiKey ? { ...base, "X-API-KEY": apiKey } : base;
    setHeaders(hdrs);
    toast({ title: "Headers applied", description: `Mode: ${mode}${apiKey ? " • API key set" : ""}` });
  };

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const data = await api.list();
      setAgents(data);
    } catch (e) {
      toast({ title: "Failed to load agents", description: String(e), variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, [headers]);

  const handleActivate = async (id) => {
    try {
      await api.activate(id);
      toast({ title: `Activated ${id}` });
      setAgents((prev) => prev.map((a) => (a.agent_id === id ? { ...a, state: "active" } : a)));
    } catch (e) {
      toast({ title: `Activate failed`, description: String(e), variant: "destructive" });
    }
  };

  const handleDeactivate = async (id) => {
    try {
      await api.deactivate(id);
      toast({ title: `Deactivated ${id}` });
      setAgents((prev) => prev.map((a) => (a.agent_id === id ? { ...a, state: "sleep", uptime: 0 } : a)));
    } catch (e) {
      toast({ title: `Deactivate failed`, description: String(e), variant: "destructive" });
    }
  };

  const handleCheck = async (id) => {
    try {
      const res = await api.status(id);
      toast({ title: `${id} • ${res.state}`, description: `Uptime ${prettyUptime(res.uptime)}` });
      setAgents((prev) => prev.map((a) => (a.agent_id === id ? { ...a, state: res.state, uptime: res.uptime } : a)));
    } catch (e) {
      toast({ title: `Status failed`, description: String(e), variant: "destructive" });
    }
  };

  return (
    <div data-testid="agents-dashboard" className="min-h-screen bg-gradient-to-b from-neutral-50 to-stone-50">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-end justify-between mb-8">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight" data-testid="page-title">Blaxing Agents</h1>
            <p className="text-neutral-600 mt-2" data-testid="page-subtitle">Manage and supervise your AI agents.</p>
          </div>
          <HeaderControls mode={mode} setMode={setMode} apiKey={apiKey} setApiKey={setApiKey} onApply={applyHeaders} />
        </div>

        {loading ? (
          <div data-testid="loading-state" className="text-neutral-600">Loading agents...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {agents.map((agent) => (
              <AgentCard
                key={agent.agent_id}
                agent={agent}
                onActivate={handleActivate}
                onDeactivate={handleDeactivate}
                onCheck={handleCheck}
              />
            ))}
          </div>
        )}
      </div>
      <Toaster />
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
