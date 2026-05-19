# L1-15: Flask App Setup & Imports
# L17-30: Utility for extracting text from Scrapling responses
# L32-55: API Endpoint - Real-time token acquisition
# L57-80: API Endpoint - Fetch complex list by region
# L82-110: API Endpoint - Fetch property listings per complex
# L112-116: Server execution entry point (Port 5000)

from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import json
import os
import requests
from datetime import datetime
from scrapling.fetchers import FetcherSession

app = Flask(__name__)
CORS(app)

def get_page_text(page) -> str:
    if hasattr(page, "body"):
        body = page.body
        if isinstance(body, (bytes, bytearray)):
            try: return body.decode('utf-8', errors='replace')
            except: pass
    if hasattr(page, "get"):
        try: 
            res = page.get()
            if res: return res
        except: pass
    return ""

@app.route('/api/token', methods=['GET'])
def api_get_token():
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'referer': 'https://www.naver.com/'
    }
    urls = ["https://new.land.naver.com/complexes", "https://new.land.naver.com/"]
    with FetcherSession() as session:
        for url in urls:
            try:
                page = session.get(url, headers=headers)
                html = get_page_text(page)
                if not html: continue
                match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
                if match:
                    app_state = json.loads(match.group(1).strip())
                    token = app_state.get("state", {}).get("token", {}).get("token") or app_state.get("config", {}).get("token")
                    if token: return jsonify({"token": token})
                match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
                if match:
                    next_data = json.loads(match.group(1))
                    paths = [["props", "pageProps", "token"], ["props", "pageProps", "initialState", "app", "token"]]
                    for path in paths:
                        val = next_data
                        for key in path:
                            val = val.get(key, {}) if isinstance(val, dict) else None
                            if val is None: break
                        if isinstance(val, str) and val: return jsonify({"token": val})
            except: continue
    return jsonify({"error": "Failed to acquire token"}), 500

@app.route('/api/complexes', methods=['GET'])
def api_get_complexes():
    cortarNo = request.args.get('cortarNo')
    token = request.args.get('token')
    if not cortarNo or not token: return jsonify({"error": "Missing params"}), 400
    headers = {
        'authority': 'new.land.naver.com',
        'accept': 'application/json, text/plain, */*',
        'authorization': f'Bearer {token}',
        'referer': 'https://new.land.naver.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    url = f"https://new.land.naver.com/api/regions/complexes?cortarNo={cortarNo}&realEstateType=APT&tradeType="
    with FetcherSession() as session:
        try:
            page = session.get(url, headers=headers)
            if page.status == 200:
                data = json.loads(get_page_text(page))
                return jsonify({"complexes": data.get('complexList', [])})
        except Exception as e: return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Fetch failed"}), 500

@app.route('/api/listings', methods=['GET'])
def api_get_listings():
    complexNo = request.args.get('complexNo')
    token = request.args.get('token')
    page_num = request.args.get('page', '1')
    headers = {
        'authority': 'new.land.naver.com',
        'accept': 'application/json, text/plain, */*',
        'authorization': f'Bearer {token}',
        'referer': 'https://new.land.naver.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    url = (f"https://new.land.naver.com/api/articles/complex/{complexNo}?realEstateType=APT&tradeType=&rentPriceMin=0&rentPriceMax=900000000"
           f"&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&showArticle=false&sameAddressGroup=false&priceType=RETAIL"
           f"&page={page_num}&complexNo={complexNo}&type=list&order=rank")
    with FetcherSession() as session:
        try:
            resp = session.get(url, headers=headers)
            if resp.status == 200:
                data = json.loads(get_page_text(resp))
                return jsonify({"listings": data.get('articleList', [])})
        except Exception as e: return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Fetch failed"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
