import React, { useEffect, useState } from "react";

export default function AgentBuilderPanel() {
  const [agents, setAgents] = useState([]);
  const [newAgent, setNewAgent] = useState({
    name: "",
    role: "",
    personality: "",
    mission: "",
  });
  const [askPrompt, setAskPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("");
  const [loading, setLoading] = useState(false);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL;
  const API = `${BACKEND_URL}/api`;

  const fetchAgents = async () => {
    try {
      const res = await fetch(`${API}/agent-builder/list`);
      const data = await res.json();
      setAgents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Erreur de chargement des agents :", err);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleCreate = async () => {
    if (!newAgent.name) return alert("Nom obligatoire !");
    setLoading(true);
    try {
      const res = await fetch(`${API}/agent-builder/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newAgent),
      });
      if (res.ok) {
        setNewAgent({ name: "", role: "", personality: "", mission: "" });
        await fetchAgents();
      } else {
        const t = await res.text();
        console.error("Create agent failed:", t);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAsk = async () => {
    if (!selectedAgent || !askPrompt) return;
    setLoading(true);
    setResponse("Réflexion en cours...");
    try {
      const res = await fetch(`${API}/agent-builder/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_id: selectedAgent, prompt: askPrompt }),
      });
      const data = await res.json();
      setResponse(data.response || "Aucune réponse.");
    } catch (err) {
      setResponse("Erreur lors de la requête.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 text-white p-6 rounded-2xl shadow-lg space-y-8" data-testid="agent-builder-panel">
      <h2 className="text-2xl font-bold text-center mb-4">🧠 Agent Builder</h2>

      <div className="bg-gray-800 p-4 rounded-xl">
        <h3 className="text-lg font-semibold mb-2">Créer un nouvel agent</h3>
        <div className="grid md:grid-cols-2 gap-4">
          <input
            data-testid="new-agent-name-input"
            type="text"
            placeholder="Nom"
            className="p-2 rounded bg-gray-700 text-white"
            value={newAgent.name}
            onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
          />
          <input
            data-testid="new-agent-role-input"
            type="text"
            placeholder="Rôle"
            className="p-2 rounded bg-gray-700 text-white"
            value={newAgent.role}
            onChange={(e) => setNewAgent({ ...newAgent, role: e.target.value })}
          />
          <input
            data-testid="new-agent-personality-input"
            type="text"
            placeholder="Personnalité"
            className="p-2 rounded bg-gray-700 text-white"
            value={newAgent.personality}
            onChange={(e) => setNewAgent({ ...newAgent, personality: e.target.value })}
          />
          <input
            data-testid="new-agent-mission-input"
            type="text"
            placeholder="Mission"
            className="p-2 rounded bg-gray-700 text-white"
            value={newAgent.mission}
            onChange={(e) => setNewAgent({ ...newAgent, mission: e.target.value })}
          />
        </div>
        <button
          onClick={handleCreate}
          disabled={loading}
          data-testid="create-agent-button"
          className="mt-3 bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg font-semibold"
        >
          {loading ? "Création..." : "Créer l'agent"}
        </button>
      </div>

      <div className="bg-gray-800 p-4 rounded-xl">
        <h3 className="text-lg font-semibold mb-3">Agents enregistrés</h3>
        {agents.length === 0 ? (
          <p className="text-gray-400">Aucun agent enregistré.</p>
        ) : (
          <ul className="space-y-2">
            {agents.map((agent) => (
              <li
                key={agent.id}
                className="p-3 rounded-lg bg-gray-700 hover:bg-gray-600 cursor-pointer"
                data-testid={`agent-list-item-${agent.id}`}
                onClick={() => setSelectedAgent(agent.name)}
              >
                <strong>{agent.name}</strong> — {agent.role}
                <p className="text-sm text-gray-400">{agent.mission}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-gray-800 p-4 rounded-xl">
        <h3 className="text-lg font-semibold mb-2">Interroger un agent</h3>
        <select
          className="p-2 rounded bg-gray-700 text-white w-full mb-2"
          data-testid="ask-agent-select"
          onChange={(e) => setSelectedAgent(e.target.value)}
          value={selectedAgent}
        >
          <option value="">-- Sélectionner un agent --</option>
          {agents.map((a) => (
            <option key={a.id} value={a.name} data-testid={`ask-option-${a.id}`}>
              {a.name}
            </option>
          ))}
        </select>
        <textarea
          rows={3}
          placeholder="Pose ta question..."
          className="w-full p-2 rounded bg-gray-700 text-white"
          data-testid="ask-prompt-textarea"
          value={askPrompt}
          onChange={(e) => setAskPrompt(e.target.value)}
        />
        <button
          onClick={handleAsk}
          disabled={loading}
          data-testid="ask-submit-button"
          className="mt-3 bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-semibold"
        >
          {loading ? "Réflexion..." : "Envoyer"}
        </button>

        {response && (
          <div className="mt-4 p-3 bg-gray-700 rounded-lg" data-testid="ask-response-box">
            <h4 className="font-semibold">Réponse :</h4>
            <p className="text-gray-200 mt-1">{response}</p>
          </div>
        )}
      </div>
    </div>
  );
}