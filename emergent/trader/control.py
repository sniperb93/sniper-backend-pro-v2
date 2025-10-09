from flask import Blueprint, request, jsonify, current_app
import os
from binance.client import Client
from decimal import Decimal, ROUND_DOWN
import requests

control_bp = Blueprint("control_bp", __name__)

def get_binance_client():
    api = os.getenv("BINANCE_API_KEY")
    sec = os.getenv("BINANCE_SECRET_KEY")
    if not api or not sec:
        raise Exception("Binance keys missing")
    return Client(api, sec)

@control_bp.route("/status_sniper", methods=["GET"])
def status_sniper():
    try:
        from emergent.trader.manager import SNIPER_MANAGER
        return jsonify(SNIPER_MANAGER.status()), 200
    except Exception:
        return jsonify({"status":"unknown"}), 200

@control_bp.route("/stop_sniper", methods=["POST"])
def stop_sniper():
    try:
        from emergent.trader.manager import SNIPER_MANAGER
        res = SNIPER_MANAGER.stop()
        return jsonify(res), 200
    except Exception as e:
        current_app.logger.error("stop_sniper: %s", e)
        return jsonify({"error": str(e)}), 500

@control_bp.route("/start_sniper", methods=["POST"])
def start_sniper():
    try:
        from emergent.trader.manager import SNIPER_MANAGER
        res = SNIPER_MANAGER.start()
        return jsonify(res), 200
    except Exception as e:
        current_app.logger.error("start_sniper: %s", e)
        return jsonify({"error": str(e)}), 500

@control_bp.route("/test_trade", methods=["POST"])
def test_trade():
    data = request.json or {}
    symbol = data.get("symbol","SOLUSDT")
    amount_usdc = float(data.get("amount_usdc", 10))
    simulate = data.get("simulate", True)

    try:
        # Mode simulation: ne nécessite pas de clés Binance; utilise endpoint public
        if simulate:
            base = os.getenv("BINANCE_REST_BASE", "https://api.binance.com")
            r = requests.get(f"{base.rstrip('/')}/api/v3/ticker/price", params={"symbol": symbol}, timeout=8)
            if r.status_code >= 400:
                return jsonify({"error": "Ticker fetch failed", "code": r.status_code, "text": r.text[:200]}), 400
            ticker = r.json()
            price = float(ticker["price"]) if isinstance(ticker, dict) and "price" in ticker else float(ticker)
            qty = (Decimal(amount_usdc) / Decimal(price)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN)
            result = {"symbol": symbol, "price": price, "qty": str(qty), "amount_usdc": amount_usdc, "note": "Simulé, pas d'ordre placé"}
            return jsonify(result), 200

        # Mode réel: nécessite des clés
        client = get_binance_client()
        ticker = client.get_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])
        qty = (Decimal(amount_usdc) / Decimal(price)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN)
        order = client.create_order(symbol=symbol, side='BUY', type='MARKET', quantity=str(qty))
        result = {"symbol": symbol, "price": price, "qty": str(qty), "amount_usdc": amount_usdc, "order": order}
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error("test_trade error: %s", e)
        return jsonify({"error": str(e)}), 400