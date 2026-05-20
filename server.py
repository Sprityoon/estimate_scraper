# L1-15: Flask Setup & Static File Routing
# L17-45: API Endpoints (Token, Complexes, Listings)
# L47-60: Server Execution logic

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import json
import os
from datetime import datetime
from scrapling.fetchers import FetcherSession

app = Flask(__name__, static_folder='static')
CORS(app)

def get_page_text(page) -> str:
    if hasattr(page, "body"):
        body = page.body
        if isinstance(body, (bytes, bytearray)):
            try: return body.decode('utf-8', errors='replace')
            except: pass
    if hasattr(page, "get"):
        try: return page.get() or ""
        except: pass
    return ""

# L1: Serve Next.js Frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/token')
def api_get_token():
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    with FetcherSession() as session:
        for url in ["https://new.land.naver.com/complexes", "https://new.land.naver.com/"]:
            try:
                page = session.get(url, headers=headers)
                html = get_page_text(page)
                match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
                if match:
                    token = json.loads(match.group(1).strip()).get("state", {}).get("token", {}).get("token")
                    if token: return jsonify({"token": token})
            except: continue
    return jsonify({"error": "No token"}), 500

@app.route('/api/complexes')
def api_get_complexes():
    c_no, tk = request.args.get('cortarNo'), request.args.get('token')
    headers = {'authorization': f'Bearer {tk}', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    with FetcherSession() as session:
        try:
            p = session.get(f"https://new.land.naver.com/api/regions/complexes?cortarNo={c_no}&realEstateType=APT", headers=headers)
            return jsonify({"complexes": json.loads(get_page_text(p)).get('complexList', [])})
        except: return jsonify({"error": "failed"}), 500

@app.route('/api/listings')
def api_get_listings():
    c_no, tk, pg = request.args.get('complexNo'), request.args.get('token'), request.args.get('page', '1')
    headers = {'authorization': f'Bearer {tk}', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    url = f"https://new.land.naver.com/api/articles/complex/{c_no}?realEstateType=APT&page={pg}&type=list&order=rank"
    with FetcherSession() as session:
        try:
            p = session.get(url, headers=headers)
            return jsonify({"listings": json.loads(get_page_text(p)).get('articleList', [])})
        except: return jsonify({"error": "failed"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
