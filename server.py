# L1-15: Flask and Core Config
# L17-40: Advanced Header and Session Management
# L42-75: /api/token - Internal retry and mobile-first strategy
# L77-120: /api/complexes & listings - Robust data fetching
# L122-130: Server Execution

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import json
import os
import requests
import time
import random

app = Flask(__name__, static_folder='static')
CORS(app)

def get_session_headers(is_mobile=False):
    if is_mobile:
        return {
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'ko-KR,ko;q=0.9',
            'referer': 'https://m.land.naver.com/'
        }
    return {
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

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/token')
def api_get_token():
    session = requests.Session()
    # 모바일과 PC 페이지를 번갈아 시도하여 보안 우회
    targets = [
        {"url": "https://m.land.naver.com/", "mobile": True},
        {"url": "https://new.land.naver.com/complexes", "mobile": False}
    ]
    
    for target in targets:
        for attempt in range(2): # 각 타겟별 2회 시도
            try:
                resp = session.get(target["url"], headers=get_session_headers(target["mobile"]), timeout=7)
                if resp.status_code != 200: continue
                
                html = resp.text
                # 모바일/PC 통합 토큰 추출 정규식
                token_match = re.search(r'token\s*:\s*["\']([^"\']+)["\']', html)
                if token_match: return jsonify({"token": token_match.group(1)})
                
                app_match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
                if app_match:
                    data = json.loads(app_match.group(1).strip())
                    token = data.get("state", {}).get("token", {}).get("token") or data.get("config", {}).get("token")
                    if token: return jsonify({"token": token})
            except:
                time.sleep(random.uniform(0.5, 1.5))
                continue
                
    return jsonify({"error": "Failed to acquire token after retries"}), 500

@app.route('/api/complexes')
def api_get_complexes():
    c_no, tk = request.args.get('cortarNo'), request.args.get('token')
    if not c_no or not tk: return jsonify({"error": "Params missing"}), 400
    
    url = f"https://new.land.naver.com/api/regions/complexes?cortarNo={c_no}&realEstateType=APT&tradeType="
    headers = get_session_headers(False)
    headers['authorization'] = f'Bearer {tk}'
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return jsonify({"complexes": resp.json().get('complexList', [])})
        return jsonify({"error": f"Naver API Error: {resp.status_code}"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/listings')
def api_get_listings():
    c_no, tk, pg = request.args.get('complexNo'), request.args.get('token'), request.args.get('page', '1')
    
    url = (f"https://new.land.naver.com/api/articles/complex/{c_no}?realEstateType=APT&tradeType=&rentPriceMin=0&rentPriceMax=900000000"
           f"&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&showArticle=false&sameAddressGroup=false&priceType=RETAIL"
           f"&page={pg}&complexNo={c_no}&type=list&order=rank")
    headers = get_session_headers(False)
    headers['authorization'] = f'Bearer {tk}'
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return jsonify({"listings": resp.json().get('articleList', [])})
        return jsonify({"error": f"Naver API Error: {resp.status_code}"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
