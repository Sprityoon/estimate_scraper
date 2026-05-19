import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from scrapling.fetchers import FetcherSession

def handler_logic(complexNo, token, page=1):
    # 해외 거주자 위장 헤더
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
    url = (f"https://new.land.naver.com/api/articles/complex/{complexNo}"
           f"?realEstateType=APT&tradeType=&rentPriceMin=0&rentPriceMax=900000000"
           f"&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000"
           f"&showArticle=false&sameAddressGroup=false&priceType=RETAIL"
           f"&page={page}&complexNo={complexNo}&type=list&order=rank")
    
    with FetcherSession() as session:
        try:
            resp = session.get(url, headers=headers, timeout=8)
            if resp.status == 200:
                content = resp.body
                if isinstance(content, (bytes, bytearray)):
                    content = content.decode('utf-8')
                return json.loads(content).get('articleList', [])
        except: pass
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        complexNo = query.get('complexNo', [None])[0]
        token = query.get('token', [None])[0]
        page = query.get('page', ['1'])[0]

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not complexNo or not token:
            self.wfile.write(json.dumps({"error": "Missing params"}).encode('utf-8'))
            return

        listings = handler_logic(complexNo, token, page)
        response = {"listings": listings} if listings is not None else {"error": "Fetch listings failed (Impersonation Failed)"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
