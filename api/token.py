import re
import json
import requests
from http.server import BaseHTTPRequestHandler

def get_token():
    # 토큰 획득 확률이 가장 높은 URL 하나로 단축
    url = "https://new.land.naver.com/complexes"
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'referer': 'https://new.land.naver.com/'
    }
    
    try:
        # 타임아웃을 짧게 잡아 10초 이내 응답 보장
        resp = requests.get(url, headers=headers, timeout=4)
        html = resp.text
        if not html: return None
        
        # 1. window.App 파싱
        match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
        if match:
            try:
                app_state = json.loads(match.group(1).strip())
                token = app_state.get("state", {}).get("token", {}).get("token") or app_state.get("config", {}).get("token")
                if token: return token
            except: pass

        # 2. __NEXT_DATA__ 파싱 (백업)
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                next_data = json.loads(match.group(1))
                return next_data.get("props", {}).get("pageProps", {}).get("token")
            except: pass
    except Exception as e:
        print(f"Token acquisition failed: {e}")
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        token = get_token()
        
        self.send_response(200 if token else 500)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {"token": token} if token else {"error": "Failed to acquire token"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
