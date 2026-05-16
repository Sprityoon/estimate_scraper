import json
import requests
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

def handler_logic(complexNo, token, page=1):
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'authorization': f'Bearer {token}',
        'accept': 'application/json, text/plain, */*',
        'referer': 'https://new.land.naver.com/'
    }
    url = (f"https://new.land.naver.com/api/articles/complex/{complexNo}"
           f"?realEstateType=APT&tradeType=&rentPriceMin=0&rentPriceMax=900000000"
           f"&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000"
           f"&showArticle=false&sameAddressGroup=false&priceType=RETAIL"
           f"&page={page}&complexNo={complexNo}&type=list&order=rank")
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json().get('articleList', [])
    except: pass
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        complexNo = query.get('complexNo', [None])[0]
        token = query.get('token', [None])[0]
        page = query.get('page', ['1'])[0]

        if not complexNo or not token:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Missing complexNo or token"}')
            return

        listings = handler_logic(complexNo, token, page)
        
        self.send_response(200 if listings is not None else 500)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {"listings": listings} if listings is not None else {"error": "Failed to fetch listings"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
