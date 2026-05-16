import urllib.request
import zipfile
import io
import json
import os
import re
import pandas as pd
from datetime import datetime
import requests

def get_naver_token():
    """네이버 부동산에서 인증 토큰을 추출합니다. (다중 엔드포인트 시도)"""
    # 1순위: 모바일 페이지 (가장 가벼움)
    # 2순위: PC 단지 페이지 (가장 확실함)
    targets = [
        {
            "url": "https://m.land.naver.com/",
            "headers": {
                'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
            }
        },
        {
            "url": "https://new.land.naver.com/complexes",
            "headers": {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'referer': 'https://www.naver.com/'
            }
        }
    ]

    for target in targets:
        url = target["url"]
        headers = target["headers"]
        print(f"토큰 추출 시도 중... ({url})")
        
        try:
            # GitHub Actions 환경의 지연을 고려해 넉넉히 20초 설정
            resp = requests.get(url, headers=headers, timeout=20)
            html = resp.text
            
            # 정규표현식 1: token: "..." 형태 (모바일용)
            token_match = re.search(r'token\s*:\s*["\']([^"\']+)["\']', html)
            if token_match:
                return token_match.group(1)
            
            # 정규표현식 2: window.App 파싱 (PC/공통용)
            match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
            if match:
                try:
                    app_json = match.group(1).strip()
                    app_state = json.loads(app_json)
                    token = app_state.get("state", {}).get("token", {}).get("token") or app_state.get("config", {}).get("token")
                    if token: return token
                except: pass

            # 정규표현식 3: __NEXT_DATA__ 파싱 (PC용)
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
            if match:
                try:
                    next_data = json.loads(match.group(1))
                    token = next_data.get("props", {}).get("pageProps", {}).get("token")
                    if token: return token
                except: pass
                
        except Exception as e:
            print(f"해당 엔드포인트 실패 ({url}): {e}")
            continue
            
    return None

class LegalDongScraper:
    """행정안전부/법정동 코드 데이터를 직접 수집하여 가공합니다 (XLSX 기반)."""
    DATA_URL = "https://www.code.go.kr/stdcode/regCodeFileDown.do?cPage=1&pageSize=100000&chkHigh=0&chkLow=0&disuseAt=ALL"
    
    @staticmethod
    def fetch_latest_data():
        print("공식 소스에서 최신 법정동 데이터 수집 중 (XLSX)...")
        try:
            req = urllib.request.Request(LegalDongScraper.DATA_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                zip_data = response.read()
            
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                xlsx_filename = z.namelist()[0]
                with z.open(xlsx_filename) as f:
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
            code = str(row['법정동코드']).strip()
            full_name = str(row['법정동명']).strip()
            name_parts = full_name.split()
            if len(name_parts) <= 1: continue
            
            si = name_parts[0]
            if len(name_parts) >= 3 and (name_parts[1].endswith('시') or name_parts[1].endswith('군')) and name_parts[2].endswith('구'):
                gu, emd = f"{name_parts[1]} {name_parts[2]}", " ".join(name_parts[3:]) if len(name_parts) > 3 else name_parts[2]
            else:
                gu, emd = name_parts[1], " ".join(name_parts[2:]) if len(name_parts) > 2 else name_parts[1]
            
            if not emd: emd = gu
            results.append({'code': code, 'siName': si, 'guName': gu, 'name': emd, 'fullName': full_name})
        
        return results

if __name__ == "__main__":
    # 1. 법정동 데이터 수집
    data = LegalDongScraper.fetch_latest_data()
    if data:
        with open("dong.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"성공: {len(data)}개 지역 데이터가 dong.json으로 저장되었습니다.")

    # 2. 실시간 토큰 수집
    token = get_naver_token()
    if token:
        with open("token.json", "w", encoding="utf-8") as f:
            json.dump({"token": token, "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=1)
        print(f"성공: 네이버 토큰이 token.json으로 저장되었습니다. ({token[:15]}...)")
    else:
        print("실패: 모든 엔드포인트에서 토큰을 수집하지 못했습니다.")
        if not os.path.exists("dong.json"): exit(1)
