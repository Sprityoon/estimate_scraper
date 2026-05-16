import urllib.request
import zipfile
import io
import json
import os
import pandas as pd

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
                gu, emd = f"{parts[1]} {parts[2]}", " ".join(parts[3:]) if len(parts) > 3 else parts[2]
            else:
                gu, emd = name_parts[1], " ".join(name_parts[2:]) if len(name_parts) > 2 else name_parts[1]
            
            if not emd: emd = gu
            results.append({'code': code, 'siName': si, 'guName': gu, 'name': emd, 'fullName': full_name})
        
        return results

if __name__ == "__main__":
    data = LegalDongScraper.fetch_latest_data()
    if data:
        with open("dong.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"성공: {len(data)}개 지역 데이터가 dong.json으로 저장되었습니다.")
    else:
        print("실패: 데이터를 수집하지 못했습니다.")
        exit(1)
