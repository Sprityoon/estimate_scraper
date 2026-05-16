import json
import requests
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

def handler_logic(cortarNo, token):
    # 데스크톱 버전에서 검증된 정밀 헤더 세트 적용
    headers = {
        'authority': 'new.land.naver.com',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'authorization': f'Bearer {token}',
        'referer': 'https://new.land.naver.com/',
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    url = f"https://new.land.naver.com/api/regions/complexes?cortarNo={cortarNo}&realEstateType=APT&tradeType="
    
    try:
        # 타임아웃을 8초로 늘려 안정성 확보 (Vercel 10초 제한 안쪽)
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            return resp.json().get('complexList', [])
        else:
            print(f"API Error: Status {resp.status_code}")
    except Exception as e:
        print(f"Request Exception: {e}")
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        cortarNo = query.get('cortarNo', [None])[0]
        token = query.get('token', [None])[0]

        if not cortarNo or not token:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing params"}).encode('utf-8'))
            return

        complexes = handler_logic(cortarNo, token)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if complexes is not None:
            response = {"complexes": complexes}
        else:
            response = {"error": "Fetch complexes failed (Check Server Logs)"}
            
        self.wfile.write(json.dumps(response).encode('utf-8'))
