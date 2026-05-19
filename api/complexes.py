import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from scrapling.fetchers import FetcherSession

def handler_logic(cortarNo, token):
    # 해외 거주자 위장 헤더 (미국 거주 교포 스타일)
    headers = {
        'authority': 'new.land.naver.com',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9', 
        'authorization': f'Bearer {token}',
        'referer': 'https://new.land.naver.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
    }
    url = f"https://new.land.naver.com/api/regions/complexes?cortarNo={cortarNo}&realEstateType=APT&tradeType="
    
    with FetcherSession() as session:
        try:
            # Vercel 10초 타임아웃 이내에 끝내기 위해 8초 설정
            page = session.get(url, headers=headers, timeout=8)
            if page.status == 200:
                content = page.body
                if isinstance(content, (bytes, bytearray)):
                    content = content.decode('utf-8')
                return json.loads(content).get('complexList', [])
        except: pass
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
        response = {"complexes": complexes} if complexes is not None else {"error": "Fetch complexes failed (Impersonation Failed)"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
