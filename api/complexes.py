import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from scrapling.fetchers import FetcherSession

def handler_logic(cortarNo, token):
    headers = {
        'authority': 'new.land.naver.com',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'authorization': f'Bearer {token}',
        'referer': 'https://new.land.naver.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    url = f"https://new.land.naver.com/api/regions/complexes?cortarNo={cortarNo}&realEstateType=APT&tradeType="
    
    # 원래 코드에서 쓰던 FetcherSession 복원
    with FetcherSession() as session:
        try:
            page = session.get(url, headers=headers)
            if page.status == 200:
                # scrapling은 .body가 바이트이므로 디코딩 필요
                content = page.body
                if isinstance(content, (bytes, bytearray)):
                    content = content.decode('utf-8')
                return json.loads(content).get('complexList', [])
        except Exception as e:
            print(f"Scrapling API Error: {e}")
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        cortarNo = query.get('cortarNo', [None])[0]
        token = query.get('token', [None])[0]

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not cortarNo or not token:
            self.wfile.write(json.dumps({"error": "Missing params"}).encode('utf-8'))
            return

        complexes = handler_logic(cortarNo, token)
        response = {"complexes": complexes} if complexes is not None else {"error": "Fetch complexes failed (Scrapling Error)"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
