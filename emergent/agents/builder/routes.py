from flask import Blueprint, request, jsonify
from .models import BlaxingAgent
import json, os

builder_bp = Blueprint("builder_bp", __name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_FILE = os.path.join(BASE_DIR, "../data/agents.json")

@builder_bp.route("/create_agent", methods=["POST"])
def create_agent():
    data = request.json or {}
    new_agent = BlaxingAgent(**data)
    os.makedirs(os.path.dirname(AGENTS_FILE), exist_ok=True)
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE, "r", encoding="utf-8") as f:
            try:
                agents = json.load(f)
            except Exception:
                agents = []
    else:
        agents = []
    agents.append(new_agent.to_dict())
    with open(AGENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(agents, f, indent=2, ensure_ascii=False)
    return jsonify({"status": "success", "agent": new_agent.to_dict()}), 201

@builder_bp.route("/list_agents", methods=["GET"])
def list_agents():
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE, "r", encoding="utf-8") as f:
            try:
                agents = json.load(f)
            except Exception:
                agents = []
    else:
        agents = []
    return jsonify(agents), 200