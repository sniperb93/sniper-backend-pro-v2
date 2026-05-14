from flask import Blueprint, request, jsonify, current_app
from .models import BlaxingAgent
import json, os

builder_bp = Blueprint("builder_bp", __name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_FILE = os.path.join(BASE_DIR, "../data/agents.json")

@builder_bp.route("/create_agent", methods=["POST"])
def create_agent():
    data = request.json or {}
    # Validation des champs requis
    required_fields = ["name", "role", "mission"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"missing required field: {field}"}), 400
    
    new_agent = BlaxingAgent(**data)
    os.makedirs(os.path.dirname(AGENTS_FILE), exist_ok=True)
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE, "r") as f:
            try:
                agents = json.load(f)
            except Exception:
                agents = []
    else:
        agents = []
    # Sécurité: ne pas inclure les clés API dans le fichier JSON
    agents.append(new_agent.to_dict(include_sensitive=False))
    with open(AGENTS_FILE, "w") as f:
        json.dump(agents, f, indent=2)
    # Retourner sans la clé API pour sécurité
    return jsonify({"status":"success","agent": new_agent.to_dict(include_sensitive=False)}), 201

@builder_bp.route("/list_agents", methods=["GET"])
def list_agents():
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE, "r") as f:
            try:
                agents = json.load(f)
            except Exception:
                agents = []
    else:
        agents = []
    # Sécurité: filtrer les clés API si elles sont présentes dans le fichier
    safe_agents = []
    for agent in agents:
        if isinstance(agent, dict):
            safe_agent = {k: v for k, v in agent.items() if k != "api_key"}
            safe_agents.append(safe_agent)
        else:
            safe_agents.append(agent)
    return jsonify(safe_agents), 200