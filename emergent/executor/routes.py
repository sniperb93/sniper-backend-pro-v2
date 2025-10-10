from flask import Blueprint, request, jsonify, current_app
from emergent.utils.emergent_forward import forward_to_emergent

agent_exec_bp = Blueprint("agent_exec_bp", __name__)

@agent_exec_bp.route("/agents/run/sniper", methods=["POST"])
def run_sniper():
    data = request.json or {}
    symbol = data.get("symbol", "BTCUSDT")
    timeframe = data.get("timeframe", "1h")
    lookback = int(data.get("lookback", 50))

    try:
        # Exemple de logique: ici on renvoie une action BUY mockée avec une confiance fixe
        result = {"symbol": symbol, "action": "BUY", "confidence": 0.87}

        # Forward vers Emergent (best-effort; respecte EMERGENT_* dans l'env)
        emergent_resp = forward_to_emergent("trade_signal", {
            "symbol": symbol,
            "timeframe": timeframe,
            "lookback": lookback,
            "result": result,
        })

        return jsonify({
            "status": "ok",
            "result": result,
            "emergent_response": emergent_resp,
        }), 200
    except Exception as e:
        current_app.logger.error("Erreur dans run_sniper : %s", e)
        return jsonify({"error": str(e)}), 500