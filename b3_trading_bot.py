import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify

# === CONFIG ===
API_KEY = 'YOUR_MEXC_API_KEY'
API_SECRET = 'YOUR_MEXC_API_SECRET'
BASE_URL = 'https://api.mexc.com'

SYMBOL = 'BTC_USDT'

TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_USER_ID'

app = Flask(__name__)

# === Utils ===
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)

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

def place_order(side, quantity):
    endpoint = '/api/v3/order'
    params = {
        'symbol': SYMBOL,
        'side': side,
        'type': 'MARKET',
        'quantity': quantity
    }
    result = signed_request('POST', endpoint, params)
    send_telegram(f"B3 Bot: {side} order placed for {quantity} {SYMBOL}")
    return result

def cancel_all_orders():
    endpoint = '/api/v3/openOrders'
    params = {'symbol': SYMBOL}
    result = signed_request('DELETE', endpoint, params)
    send_telegram("B3 Bot: All open orders cancelled.")
    return result

# === Webhook Endpoint ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Webhook received:", data)

    signal = data.get("action", "").lower()
    quantity = float(data.get("qty", 0.01))

    if "buy" in signal:
        cancel_all_orders()
        result = place_order("BUY", quantity)
        return jsonify(result)

    elif "sell" in signal:
        cancel_all_orders()
        result = place_order("SELL", quantity)
        return jsonify(result)

    elif "close" in signal:
        result = cancel_all_orders()
        return jsonify(result)

    else:
        return jsonify({"msg": "Invalid action"})

# === Start Server ===
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
