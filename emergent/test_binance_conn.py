from binance.client import Client
import os
import sys

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_SECRET_KEY")

if not api_key or not api_secret:
    print("❌ BINANCE_API_KEY ou BINANCE_SECRET_KEY manquante dans .env")
    sys.exit(1)

client = Client(api_key, api_secret)
try:
    account = client.get_account()
    usdc = next((b for b in account.get('balances', []) if b.get('asset') == 'USDC'), None)
    print("✅ Connexion OK.")
    print("Solde USDC:", usdc)
except Exception as e:
    print("❌ Erreur connexion Binance:", e)
    sys.exit(2)