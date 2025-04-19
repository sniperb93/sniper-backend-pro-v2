from flask import Flask, jsonify
from binance.client import Client
import os
import requests
import threading
import time
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Initialisation Binance
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = Client(api_key, api_secret)

# Infos Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.route("/", methods=["GET"])
def index():
    return "API Sniper active"

@app.route("/check_balance", methods=["GET"])
def check_balance():
    return jsonify(_check_and_send())

def _check_and_send():
    try:
        account = client.get_account()
        balances = account["balances"]
        non_zero_balances = [b for b in balances if float(b["free"]) > 0]

        for item in non_zero_balances:
            free_amount = float(item["free"])
            if free_amount > 0.5:
                message = f"SNIPER SIGNAL : {item['asset']} : {item['free']} dispo"
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message
                }
                requests.post(url, json=payload)

        return non_zero_balances
    except Exception as e:
        return {"error": str(e)}

def auto_loop():
    while True:
        print("Vérification auto des soldes en cours...")
        _check_and_send()
        time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=auto_loop, daemon=True).start()
    app.run(debug=True, port=5000)
