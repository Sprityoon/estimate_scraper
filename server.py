# L1-15: Flask Setup and Imports
# L17-30: Utility for extraction and Session management
# L32-55: /api/token - Forced real-time acquisition from Naver
# L57-85: /api/complexes - Fetch using fresh token
# L87-115: /api/listings - Fetch listings with robust headers
# L117-122: Health check and Server start

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import json
import os
import requests
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

def get_headers(token=None):
    headers = {
        'authority': 'new.land.naver.com',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'referer': 'https://new.land.naver.com/',
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    if token:
        headers['authorization'] = f'Bearer {token}'
    return headers

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/token')
def api_get_token():
    url = "https://new.land.naver.com/complexes"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        html = resp.text
        match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
        if match:
            app_state = json.loads(match.group(1).strip())
            token = app_state.get("state", {}).get("token", {}).get("token") or app_state.get("config", {}).get("token")
            if token: return jsonify({"token": token})
        
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            token = data.get("props", {}).get("pageProps", {}).get("token")
            if token: return jsonify({"token": token})
    except Exception as e:
        return jsonify({"error": f"Token acquisition failed: {str(e)}"}), 500
    return jsonify({"error": "No token found in page source"}), 500

@app.route('/api/complexes')
def api_get_complexes():
    c_no = request.args.get('cortarNo')
    tk = request.args.get('token')
    if not c_no or not tk: return jsonify({"error": "Missing params"}), 400
    
    url = f"https://new.land.naver.com/api/regions/complexes?cortarNo={c_no}&realEstateType=APT&tradeType="
    try:
        resp = requests.get(url, headers=get_headers(tk), timeout=10)
        if resp.status_code == 200:
            return jsonify({"complexes": resp.json().get('complexList', [])})
        return jsonify({"error": f"Naver API Error: {resp.status_code}"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/listings')
def api_get_listings():
    c_no = request.args.get('complexNo')
    tk = request.args.get('token')
    pg = request.args.get('page', '1')
    
    url = (f"https://new.land.naver.com/api/articles/complex/{c_no}?realEstateType=APT&tradeType=&rentPriceMin=0&rentPriceMax=900000000"
           f"&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&showArticle=false&sameAddressGroup=false&priceType=RETAIL"
           f"&page={pg}&complexNo={c_no}&type=list&order=rank")
    try:
        resp = requests.get(url, headers=get_headers(tk), timeout=10)
        if resp.status_code == 200:
            return jsonify({"listings": resp.json().get('articleList', [])})
        return jsonify({"error": f"Naver API Error: {resp.status_code}"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "time": datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
