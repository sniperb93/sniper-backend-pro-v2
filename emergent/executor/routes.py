from flask import Blueprint, request, jsonify, current_app
from emergent.utils.emergent_forward import forward_to_emergent

agent_exec_bp = Blueprint("agent_exec_bp", __name__)

@agent_exec_bp.route("/agents/run/sniper", methods=["POST"])
def run_sniper():
    data = request.json or {}
    symbol = data.get("symbol", "BTCUSDT")
    
    # Validation du symbole
    if not isinstance(symbol, str) or len(symbol) < 4:
        return jsonify({"error": "invalid symbol format"}), 400
    
    timeframe = data.get("timeframe", "1h")
    # Validation du timeframe
    valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    if timeframe not in valid_timeframes:
        return jsonify({"error": f"invalid timeframe, must be one of: {', '.join(valid_timeframes)}"}), 400
    
    try:
        lookback = int(data.get("lookback", 50))
        if lookback <= 0 or lookback > 1000:
            return jsonify({"error": "lookback must be between 1 and 1000"}), 400
    except ValueError:
        return jsonify({"error": "invalid lookback value"}), 400

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