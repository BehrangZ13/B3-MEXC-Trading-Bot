import os
import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify

# === Get Secrets from Environment Variables ===
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = 'https://api.mexc.com'
SYMBOL = 'BTC_USDT'

app = Flask(__name__)

# === Telegram Notification ===
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

# === MEXC API Sign Helper ===
def signed_request(method, endpoint, params=None):
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    query = '&'.join([f"{k}={params[k]}" for k in sorted(params)])
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{endpoint}?{query}&signature={signature}"
    headers = {'X-MEXC-APIKEY': API_KEY}
    if method == 'GET':
        return requests.get(url, headers=headers).json()
    elif method == 'POST':
        return requests.post(url, headers=headers).json()
    elif method == 'DELETE':
        return requests.delete(url, headers=headers).json()

# === Place Order ===
def place_order(side, quantity):
    params = {
        'symbol': SYMBOL,
        'side': side,
        'type': 'MARKET',
        'quantity': quantity
    }
    result = signed_request('POST', '/api/v3/order', params)
    send_telegram(f"B3 Bot: {side.upper()} order placed — {quantity} {SYMBOL}")
    return result

# === Cancel All Open Orders ===
def cancel_all_orders():
    params = {'symbol': SYMBOL}
    result = signed_request('DELETE', '/api/v3/openOrders', params)
    send_telegram("B3 Bot: All open orders cancelled.")
    return result

# === TradingView Webhook ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    action = data.get("action", "").lower()
    quantity = float(data.get("qty", 0.01))

    if "buy" in action:
        cancel_all_orders()
        return jsonify(place_order("BUY", quantity))

    elif "sell" in action:
        cancel_all_orders()
        return jsonify(place_order("SELL", quantity))

    elif "close" in action:
        return jsonify(cancel_all_orders())

    else:
        return jsonify({"status": "ignored", "message": "Invalid action received."})

# === Start Server ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
