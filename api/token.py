import re
import json
import requests
from http.server import BaseHTTPRequestHandler

def get_token():
    # PC 버전보다 훨씬 가볍고 응답이 빠른 모바일 페이지 타격
    url = "https://m.land.naver.com/"
    headers = {
        'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'accept-language': 'ko-KR,ko;q=0.9',
        'referer': 'https://m.land.naver.com/'
    }
    
    try:
        # 미국-한국 간 지연을 고려하되 10초를 넘지 않게 엄격히 제한 (연결 2초, 읽기 5초)
        resp = requests.get(url, headers=headers, timeout=(2.0, 5.0))
        html = resp.text
        
        # 모바일 페이지의 g_token 또는 관련 JSON 파싱
        # 보통 window.App 또는 script 태그 내에 존재
        token_match = re.search(r'token\s*:\s*["\']([^"\']+)["\']', html)
        if token_match:
            return token_match.group(1)

        # 백업: NEXT_DATA 또는 기타 구조 확인
        match = re.search(r'window\.App\s*=\s*({.*?});', html, re.DOTALL)
        if match:
            app_state = json.loads(match.group(1).strip())
            return app_state.get("state", {}).get("token", {}).get("token")
            
    except Exception as e:
        print(f"Fast token acquisition failed: {e}")
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        token = get_token()
        
        # 실패하더라도 200 응답을 보내고 에러 메시지를 담아 Vercel 강제종료 방지
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {"token": token} if token else {"error": "Token timeout"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
