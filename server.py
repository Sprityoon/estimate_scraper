# L1-15: Flask App Config and Static Path Setup
# L17-35: Frontend Routing (Serving Next.js index.html and assets)
# L37-45: Health Check and Diagnostic Endpoints
# L47-110: Scraping API Endpoints (Token, Complexes, Listings)
# L112-120: Main Execution (Cloudtype PORT compatible)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import json
import os
import sys
from scrapling.fetchers import FetcherSession

# Cloudtype 환경에서는 /app 이 작업 디렉토리입니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)

# 1. Frontend Static Routing
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # static 폴더 내에 실제 파일이 존재하는지 확인
    full_path = os.path.join(app.static_folder, path)
    if path != "" and os.path.exists(full_path):
        return send_from_directory(app.static_folder, path)
    else:
        # 파일이 없으면 index.html 반환 (Next.js CSR 지원)
        return send_from_directory(app.static_folder, 'index.html')

# 2. Health Check (Diagnostic)
@app.route('/api/health')
def health():
    return jsonify({
        "status": "healthy",
        "static_dir_exists": os.path.exists(STATIC_DIR),
        "index_html_exists": os.path.exists(os.path.join(STATIC_DIR, 'index.html'))
    })

# 3. Scraping API - Token
@app.route('/api/token')
def api_get_token():
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    with FetcherSession() as session:
        for url in ["https://new.land.naver.com/complexes", "https://new.land.naver.com/"]:
            try:
                page = session.get(url, headers=headers)
                html = page.body.decode('utf-8') if hasattr(page, 'body') else ""
                match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
                if match:
                    token = json.loads(match.group(1).strip()).get("state", {}).get("token", {}).get("token")
                    if token: return jsonify({"token": token})
            except: continue
    return jsonify({"error": "Token not found"}), 500

# 4. Scraping API - Complexes
@app.route('/api/complexes')
def api_get_complexes():
    c_no = request.args.get('cortarNo')
    tk = request.args.get('token')
    headers = {'authorization': f'Bearer {tk}', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    with FetcherSession() as session:
        try:
            p = session.get(f"https://new.land.naver.com/api/regions/complexes?cortarNo={c_no}&realEstateType=APT", headers=headers)
            content = p.body.decode('utf-8') if hasattr(p, 'body') else "{}"
            return jsonify({"complexes": json.loads(content).get('complexList', [])})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# 5. Scraping API - Listings
@app.route('/api/listings')
def api_get_listings():
    c_no = request.args.get('complexNo')
    tk = request.args.get('token')
    pg = request.args.get('page', '1')
    headers = {'authorization': f'Bearer {tk}', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    url = f"https://new.land.naver.com/api/articles/complex/{c_no}?realEstateType=APT&page={pg}&type=list&order=rank"
    with FetcherSession() as session:
        try:
            p = session.get(url, headers=headers)
            content = p.body.decode('utf-8') if hasattr(p, 'body') else "{}"
            return jsonify({"listings": json.loads(content).get('articleList', [])})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Server is starting on 0.0.0.0:{port}...")
    app.run(host='0.0.0.0', port=port)
