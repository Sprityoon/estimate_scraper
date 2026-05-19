import urllib.request
import zipfile
import io
import json
import os
import re
import pandas as pd
from datetime import datetime
from scrapling.fetchers import FetcherSession
import time
import random

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
    return ""

def get_naver_token():
    """네이버 부동산에서 인증 토큰을 추출합니다 (해외 거주 유저 위장 전략)."""
    # 미국/글로벌 유저 스타일의 헤더 설정
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9', # 영어 우선 (해외 거주자 위장)
        'referer': 'https://www.google.com/', # 구글 검색을 통해 들어온 것으로 위장
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'cross-site',
    }
    
    # 지리적 지연을 고려해 가장 응답이 빠른 모바일 기반 엔드포인트 우선 타격
    urls = ["https://m.land.naver.com/", "https://new.land.naver.com/complexes"]
    
    # scrapling 엔진에 미국(US) 기반 지문 생성을 유도
    with FetcherSession() as session:
        for url in urls:
            print(f"해외 유저 위장 토큰 추출 시도 중... ({url})")
            try:
                # 60초의 넉넉한 타임아웃 유지
                page = session.get(url, headers=headers, timeout=60)
                html = get_page_text(page)
                if not html: continue
                
                # 정규표현식 매칭 (모바일/PC 공통)
                token_match = re.search(r'token\s*:\s*["\']([^"\']+)["\']', html)
                if token_match: return token_match.group(1)
                
                match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
                if match:
                    try:
                        app_state = json.loads(match.group(1).strip())
                        token = app_state.get("state", {}).get("token", {}).get("token") or app_state.get("config", {}).get("token")
                        if token: return token
                    except: pass
                
                # __NEXT_DATA__
                match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
                if match:
                    try:
                        next_data = json.loads(match.group(1))
                        token = next_data.get("props", {}).get("pageProps", {}).get("token")
                        if token: return token
                    except: pass
                    
            except Exception as e:
                print(f"해외 위장 요청 실패 ({url}): {e}")
                time.sleep(random.uniform(2, 5))
                continue
                
    return None

class LegalDongScraper:
    # (XLSX 파싱 로직은 동일하므로 생략하지 않고 전체 포함하여 작성)
    DATA_URL = "https://www.code.go.kr/stdcode/regCodeFileDown.do?cPage=1&pageSize=100000&chkHigh=0&chkLow=0&disuseAt=ALL"
    @staticmethod
    def fetch_latest_data():
        print("공식 소스에서 최신 법정동 데이터 수집 중 (XLSX)...")
        try:
            req = urllib.request.Request(LegalDongScraper.DATA_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                zip_data = response.read()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                with z.open(z.namelist()[0]) as f:
                    df = pd.read_excel(f)
                    return LegalDongScraper._parse_df(df)
        except Exception as e:
            print(f"데이터 수집 실패: {e}")
            return None
    @staticmethod
    def _parse_df(df):
        results = []
        df_active = df[df['폐지구분'] == '현존']
        for _, row in df_active.iterrows():
            code, full_name = str(row['법정동코드']).strip(), str(row['법정동명']).strip()
            parts = full_name.split()
            if len(parts) <= 1: continue
            si = parts[0]
            if len(parts) >= 3 and (parts[1].endswith('시') or parts[1].endswith('군')) and parts[2].endswith('구'):
                gu, emd = f"{parts[1]} {parts[2]}", " ".join(parts[3:]) if len(parts) > 3 else parts[2]
            else:
                gu, emd = parts[1], " ".join(parts[2:]) if len(parts) > 2 else parts[1]
            if not emd: emd = gu
            results.append({'code': code, 'siName': si, 'guName': gu, 'name': emd, 'fullName': full_name})
        return results

if __name__ == "__main__":
    data = LegalDongScraper.fetch_latest_data()
    if data:
        with open("dong.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"성공: {len(data)}개 지역 데이터 저장 완료.")
    
    token = get_naver_token()
    if token:
        with open("token.json", "w", encoding="utf-8") as f:
            json.dump({"token": token, "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=1)
        print(f"성공: 해외 위장 토큰 획득 완료 ({token[:15]}...)")
    else:
        if os.path.exists("dong.json"): exit(0)
        else: exit(1)
