import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from scrapling.fetchers import FetcherSession

def handler_logic(cortarNo, token):
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'authorization': f'Bearer {token}',
        'accept': 'application/json, text/plain, */*'
    }
    url = f"https://new.land.naver.com/api/regions/complexes?cortarNo={cortarNo}&realEstateType=APT&tradeType="
    
    with FetcherSession() as session:
        try:
            page = session.get(url, headers=headers)
            # Scrapling response to string/json
            if hasattr(page, "body"):
                data = json.loads(page.body.decode('utf-8'))
                return data.get('complexList', [])
        except: pass
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        cortarNo = query.get('cortarNo', [None])[0]
        token = query.get('token', [None])[0]

        if not cortarNo or not token:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Missing cortarNo or token"}')
            return

        complexes = handler_logic(cortarNo, token)
        
        self.send_response(200 if complexes is not None else 500)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {"complexes": complexes} if complexes is not None else {"error": "Failed to fetch complexes"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
