import re
import json
from http.server import BaseHTTPRequestHandler
from scrapling.fetchers import FetcherSession

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
    if hasattr(page, "text") and isinstance(page.text, str):
        return page.text
    return ""

def get_token():
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    with FetcherSession() as session:
        urls = ["https://new.land.naver.com/", "https://new.land.naver.com/complexes"]
        for url in urls:
            try:
                page = session.get(url, headers=headers)
                html = get_page_text(page)
                if not html: continue
                
                match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
                if match:
                    app_state = json.loads(match.group(1).strip())
                    token = app_state.get("state", {}).get("token", {}).get("token")
                    if not token: token = app_state.get("config", {}).get("token")
                    if token: return token

                match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
                if match:
                    next_data = json.loads(match.group(1))
                    token = next_data.get("props", {}).get("pageProps", {}).get("token")
                    if token: return token
            except: continue
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
