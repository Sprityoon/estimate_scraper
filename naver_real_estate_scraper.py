import csv
import os
import sys
from datetime import datetime
import json
import time
import re
import random
import logging
import threading
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext
import urllib.request
from scrapling.fetchers import FetcherSession
import pandas as pd
import zipfile
import io

# 버전 정보 및 디버그 메시지
VERSION = "v2.5_FINAL_FIXED"
print(f"DEBUG: naver_real_estate_scraper.py {VERSION} 로드됨")

def get_page_text(page) -> str:
    """안전하게 Scrapling Response/Selector 객체에서 전체 소스(HTML/JSON)를 추출합니다."""
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
    if hasattr(page, "text") and isinstance(page.text, str):
        return page.text
    return ""

def safe_request(session, url, headers, max_retries=5):
    """429 에러 대응 및 브라우저 위장을 포함한 안전한 요청 함수"""
    local_headers = headers.copy()
    if 'User-Agent' not in local_headers and 'user-agent' not in [k.lower() for k in local_headers]:
        local_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    
    for attempt in range(max_retries):
        try:
            wait_time = random.uniform(2.0, 4.0) * (1.5 ** attempt)
            if attempt > 0: print(f"  (재시도 {attempt}/{max_retries}) {wait_time:.1f}초 대기 중...")
            time.sleep(wait_time)
            
            page = session.get(url, headers=local_headers)
            status = getattr(page, 'status', 200)
            print(f"    [DEBUG] HTTP {status} | {url[:80]}...")
            
            if status == 429:
                if attempt < max_retries - 1: continue
                else: print("너무 많은 요청이 발생했습니다 (429). 잠시 후 다시 실행해 주세요."); return None
            elif status != 200: return None
            return page
        except Exception as e:
            print(f"    [DEBUG] 요청 오류: {e}")
            if attempt < max_retries - 1: continue
            return None
    return None

def get_token(session, headers):
    """네이버 부동산에서 인증 토큰을 추출합니다."""
    urls = ["https://new.land.naver.com/", "https://new.land.naver.com/complexes"]
    for url in urls:
        try:
            print(f"  -> 접속 시도: {url}")
            page = safe_request(session, url, headers)
            if not page: continue
            html = get_page_text(page)
            if not html: continue
            
            match = re.search(r'window\.App\s*=\s*({.*?});?\s*(?:</script>|$)', html, re.DOTALL)
            if match:
                try:
                    app_json = match.group(1).strip()
                    if app_json.endswith('}'):
                        app_state = json.loads(app_json)
                        token = app_state.get("state", {}).get("token", {}).get("token")
                        if not token: token = app_state.get("config", {}).get("token")
                        if token: 
                            print(f"  -> 토큰 획득 성공! ({token[:15]}...)")
                            return token
                except: pass

            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
            if match:
                try:
                    next_data = json.loads(match.group(1))
                    paths = [
                        ["props", "pageProps", "token"],
                        ["props", "pageProps", "initialState", "app", "token"],
                        ["props", "pageProps", "initialState", "token", "token"]
                    ]
                    for path in paths:
                        val = next_data
                        for key in path:
                            val = val.get(key, {}) if isinstance(val, dict) else None
                            if val is None: break
                        if isinstance(val, str) and val:
                            print(f"  -> 토큰 획득 성공 (NEXT)! ({val[:15]}...)")
                            return val
                except: pass
        except Exception as e:
            print(f"    [!] 토큰 추출 중 예외 발생: {e}")
    return None

def _get_naver_region_list(session, headers, cortar_code):
    url = f"https://new.land.naver.com/api/regions/list?cortarNo={cortar_code}"
    api_headers = headers.copy()
    api_headers['accept'] = 'application/json, text/plain, */*'
    
    page = safe_request(session, url, api_headers)
    if not page: return []
    try:
        text = get_page_text(page)
        if not text or not text.strip(): return []
        data = json.loads(text)
        return data.get('regionList', [])
    except Exception as e:
        print(f"    [!] JSON 파싱 실패: {e}")
        return []

def get_naver_cortar_no(session, headers, sido_name, sigungu_name, emd_name):
    print(f"\n[지역 매칭] {sido_name} {sigungu_name} {emd_name}")
    sidos = _get_naver_region_list(session, headers, "0000000000")
    if not sidos: return None

    sido_match = next((s for s in sidos if s['cortarName'] == sido_name), None)
    if not sido_match: sido_match = next((s for s in sidos if s['cortarName'][:2] == sido_name[:2]), None)
    if not sido_match: sido_match = next((s for s in sidos if sido_name in s['cortarName'] or s['cortarName'] in sido_name), None)
    
    if not sido_match: return None
    current_code = sido_match['cortarNo']
    print(f"  -> 시/도 확인: {sido_match['cortarName']} ({current_code})")

    search_parts = sigungu_name.split()
    for part in search_parts:
        subs = _get_naver_region_list(session, headers, current_code)
        if not subs: break
        match = next((s for s in subs if s['cortarName'] == part), None)
        if not match: match = next((s for s in subs if part in s['cortarName'] or s['cortarName'] in part), None)
        if match:
            current_code = match['cortarNo']
            print(f"  -> 계층 이동: {match['cortarName']} ({current_code})")
        else: break

    subs = _get_naver_region_list(session, headers, current_code)
    if subs:
        dong_match = next((s for s in subs if s['cortarName'] == emd_name), None)
        if not dong_match: dong_match = next((s for s in subs if emd_name in s['cortarName'] or s['cortarName'] in emd_name), None)
        if dong_match:
            print(f"  -> 최종 목적지 '{dong_match['cortarName']}' 매칭 성공! ({dong_match['cortarNo']})")
            return dong_match['cortarNo']
    return current_code

def fetch_apartments(session, headers, cortar_code):
    url = f"https://new.land.naver.com/api/regions/complexes?cortarNo={cortar_code}&realEstateType=APT&tradeType="
    api_headers = headers.copy()
    api_headers['accept'] = 'application/json, text/plain, */*'
    try:
        page = safe_request(session, url, api_headers)
        if not page: return []
        text = get_page_text(page)
        if not text: return []
        data = json.loads(text)
        return data.get('complexList', [])
    except: return []

def fetch_listings_for_complex(session, headers, complex_no):
    listings = []
    api_headers = headers.copy()
    api_headers['accept'] = 'application/json, text/plain, */*'
    for page in range(1, 4):
        url = (f"https://new.land.naver.com/api/articles/complex/{complex_no}"
               f"?realEstateType=APT&tradeType=&rentPriceMin=0&rentPriceMax=900000000"
               f"&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000"
               f"&showArticle=false&sameAddressGroup=false&priceType=RETAIL"
               f"&page={page}&complexNo={complex_no}&type=list&order=rank")
        try:
            resp = safe_request(session, url, api_headers)
            if not resp: break
            text = get_page_text(resp)
            if not text: break
            data = json.loads(text)
            articles = data.get('articleList', [])
            if not articles: break
            listings.extend(articles)
        except: break
    return listings

def sanitize_filename(filename): return re.sub(r'[\\/*?:"<>|]', "", str(filename)).strip()

def save_to_csv(data_list, filename):
    if not data_list: return
    headers = ["단지번호", "아파트명", "법정동주소", "거래방식", "공급/전용면적", "가격(보증금/월세)", "층수", "매물특징"]
    keys = ["complexNo", "complexName", "address", "tradeType", "area", "price", "floor", "feature"]
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for item in data_list: writer.writerow([item.get(k, '') for k in keys])

class ThreadSafeConsole:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.update_me()
    def write(self, text): self.queue.put(text)
    def flush(self): pass
    def update_me(self):
        text_chunk = ""
        try:
            while True: text_chunk += self.queue.get_nowait()
        except queue.Empty: pass
        if text_chunk:
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, text_chunk)
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.text_widget.after(100, self.update_me)

class LegalDongScraper:
    DATA_URL = "https://www.code.go.kr/stdcode/regCodeFileDown.do?cPage=1&pageSize=100000&chkHigh=0&chkLow=0&disuseAt=ALL"
    @staticmethod
    def fetch_latest_data():
        print("공식 소스에서 최신 법정동 데이터 수집 중 (XLSX)...")
        try:
            req = urllib.request.Request(LegalDongScraper.DATA_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as response: zip_data = response.read()
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
        print(f"  -> 파싱 완료: {len(results)}개 지역 추출됨.")
        return results

class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"네이버 부동산 매물 수집기 ({VERSION})")
        self.root.geometry("700x750")
        
        # 데이터 관리 변수
        self.legal_dong_list = []
        self.hierarchical_data = {}
        self.search_results = []
        
        # 기본 헤더 설정 (브라우저 위장)
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'referer': 'https://new.land.naver.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }

        self._setup_gui()
        
        # 콘솔 리다이렉션 및 데이터 초기화 시작
        sys.stdout = sys.stderr = ThreadSafeConsole(self.text_output)
        threading.Thread(target=self.init_data, daemon=True).start()

    def _setup_gui(self):
        """GUI 컴포넌트 구성"""
        # 1. 지역 검색 섹션
        f_search = ttk.LabelFrame(self.root, text=" 지역 검색 ", padding=10)
        f_search.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(f_search, text="동/읍/리/단지명:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        entry = ttk.Entry(f_search, textvariable=self.search_var, width=30)
        entry.pack(side=tk.LEFT, padx=5)
        entry.bind("<Return>", lambda e: self.search_region())
        ttk.Button(f_search, text="검색", command=self.search_region).pack(side=tk.LEFT, padx=5)

        # 2. 결과 선택 섹션
        f_sel = ttk.LabelFrame(self.root, text=" 검색 결과 선택 ", padding=10)
        f_sel.pack(fill=tk.X, padx=10, pady=5)
        
        self.result_var = tk.StringVar()
        self.result_cb = ttk.Combobox(f_sel, textvariable=self.result_var, width=60, state="readonly")
        self.result_cb.pack(pady=5)
        self.result_cb.bind("<<ComboboxSelected>>", self.on_result_selected)

        # 3. 수동 선택 (계층형) 섹션
        f_man = ttk.Frame(f_sel)
        f_man.pack(fill=tk.X)
        
        self.sido_var, self.sigungu_var, self.dong_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.sido_cb = ttk.Combobox(f_man, textvariable=self.sido_var, state="readonly")
        self.sigungu_cb = ttk.Combobox(f_man, textvariable=self.sigungu_var, state="readonly")
        self.dong_cb = ttk.Combobox(f_man, textvariable=self.dong_var, state="readonly")
        
        for cb in [self.sido_cb, self.sigungu_cb, self.dong_cb]:
            cb.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
            
        self.sido_cb.bind("<<ComboboxSelected>>", self.on_sido_selected)
        self.sigungu_cb.bind("<<ComboboxSelected>>", self.on_sigungu_selected)

        # 4. 실행 및 출력 섹션
        self.btn_start = ttk.Button(self.root, text="데이터 수집 시작", command=self.start_scraping, padding=10)
        self.btn_start.pack(pady=10)

        self.text_output = scrolledtext.ScrolledText(self.root, state='disabled', wrap=tk.WORD, height=20)
        self.text_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def parse_region(self, item):
        """데이터에서 시/도, 시/군/구, 동/면/읍을 정규화하여 분리"""
        si = item.get('siName', '').strip()
        gu = item.get('guName', '').strip()
        emd = item.get('name', '').strip()
        
        if not gu:
            parts = item.get('fullName', '').split()
            if len(parts) >= 2:
                gu = parts[1]
                if len(parts) >= 3 and parts[2].endswith('구'):
                    gu = f"{parts[1]} {parts[2]}"
        return si, gu, emd

    def init_data(self):
        """데이터 로드 및 자동 업데이트 로직"""
        file_path = "legal_dong_data_full.json"
        try:
            # 업데이트 조건 체크 (30일 경과 또는 데이터 부실)
            should_fetch = not os.path.exists(file_path)
            if not should_fetch:
                age_days = (time.time() - os.path.getmtime(file_path)) / (24 * 3600)
                if age_days > 30:
                    should_fetch = True
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if len(json.load(f)) < 10000: should_fetch = True
            
            if should_fetch:
                data = LegalDongScraper.fetch_latest_data()
                if data:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=1)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                self.legal_dong_list = json.load(f)
            
            # 계층형 트리 구축
            self.hierarchical_data = {}
            for item in self.legal_dong_list:
                si, gu, emd = self.parse_region(item)
                if not si: continue
                self.hierarchical_data.setdefault(si, {}).setdefault(gu, set()).add(emd)
            
            # 메인 스레드에서 UI 업데이트
            sidos = sorted(self.hierarchical_data.keys())
            self.root.after(0, lambda: self.sido_cb.config(values=sidos))
            print(f"준비 완료. 전국 {len(self.legal_dong_list)}개 지역 로드됨.")
        except Exception as e:
            print(f"초기화 오류: {e}")

    def search_region(self):
        """지역 및 단지명 통합 검색"""
        q = self.search_var.get().strip().replace(" ", "")
        if not q: return
        
        print(f"'{q}' 검색 중...")
        results, seen = [], set()
        
        for item in self.legal_dong_list:
            full, name = item.get('fullName', '').replace(" ", ""), item.get('name', '').replace(" ", "")
            if q in name or q in full:
                si, gu, emd = self.parse_region(item)
                display = f"{si} {gu} {emd}".strip()
                if display not in seen:
                    results.append({"display": display, "si": si, "gu": gu, "emd": emd})
                    seen.add(display)
            if len(results) >= 200: break
            
        self.search_results = results
        self.result_cb.config(values=[r['display'] for r in results])
        self.result_var.set(f"{len(results)}개의 결과가 검색되었습니다.")
        if results: self.result_cb.event_generate("<<ComboboxSelected>>")

    def on_result_selected(self, e):
        """검색 결과 선택 시 콤보박스 연동"""
        idx = self.result_cb.current()
        if idx < 0: return
        
        res = self.search_results[idx]
        self.sido_var.set(res['si'])
        self.on_sido_selected(None)
        self.sigungu_var.set(res['gu'])
        self.on_sigungu_selected(None)
        self.dong_var.set(res['emd'])

    def on_sido_selected(self, e):
        si = self.sido_var.get()
        if si in self.hierarchical_data:
            gus = sorted(self.hierarchical_data[si].keys())
            self.sigungu_cb.config(values=gus)
            self.sigungu_var.set(""); self.dong_var.set("")

    def on_sigungu_selected(self, e):
        si, gu = self.sido_var.get(), self.sigungu_var.get()
        if si in self.hierarchical_data and gu in self.hierarchical_data[si]:
            dongs = sorted(list(self.hierarchical_data[si][gu]))
            self.dong_cb.config(values=dongs)
            self.dong_var.set("")

    def start_scraping(self):
        si, gu, emd = self.sido_var.get(), self.sigungu_var.get(), self.dong_var.get()
        if not si or not emd: return
        self.btn_start.config(state=tk.DISABLED)
        threading.Thread(target=self.run_scraper, args=(si, gu, emd), daemon=True).start()

    def run_scraper(self, si, sigungu, emd):
        """메인 수집 프로세스"""
        try:
            print(f"\n[{si} {sigungu} {emd}] 수집 시작...")
            with FetcherSession() as session:
                token = get_token(session, self.headers)
                if not token: 
                    print("인증 토큰 획득에 실패했습니다."); return
                
                self.headers['authorization'] = f'Bearer {token}'
                code = get_naver_cortar_no(session, self.headers, si, sigungu, emd)
                if not code:
                    print("네이버 지역 코드 매칭에 실패했습니다."); return
                
                print(f"매칭된 지역 코드: {code}")
                apts = fetch_apartments(session, self.headers, code)
                if not apts:
                    print("해당 지역에 아파트 단지가 없습니다."); return
                
                all_listings = []
                for apt in apts:
                    name, c_no = apt.get('complexName'), apt.get('complexNo')
                    print(f" - '{name}' 단지 매물 수집 중...")
                    for lst in fetch_listings_for_complex(session, self.headers, c_no):
                        w, r = lst.get('dealOrWarrantPrc', ''), str(lst.get('rentPrc', '0'))
                        all_listings.append({
                            "complexNo": c_no, "complexName": name, "address": apt.get('cortarAddress', ''),
                            "tradeType": lst.get('tradeTypeName', ''), "area": f"{lst.get('area1')}/{lst.get('area2')}",
                            "price": f"{w} / {r}" if r != '0' else w, "floor": lst.get('floorInfo', ''), 
                            "feature": lst.get('articleFeatureDesc', '')
                        })
                
                if all_listings:
                    self._save_results(si, sigungu, emd, all_listings)
                else:
                    print("수집된 매물이 없습니다.")
        except Exception as e:
            print(f"수집 중 오류 발생: {e}")
        finally:
            self.root.after(0, lambda: self.btn_start.config(state=tk.NORMAL))

    def _save_results(self, si, gu, emd, listings):
        """수집 결과 저장"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = os.path.join(sanitize_filename(f"{si}_{gu}_{emd}"), ts)
        os.makedirs(folder, exist_ok=True)
        
        # 거래 방식별 분류 저장
        by_type = {}
        for l in listings:
            by_type.setdefault(l['tradeType'], []).append(l)
            
        for t, data in by_type.items():
            filename = os.path.join(folder, f"{sanitize_filename(t)}.csv")
            save_to_csv(data, filename)
            
        print(f"\n[성공] 총 {len(listings)}개 매물 수집 완료.")
        print(f"저장 경로: {os.path.abspath(folder)}")

if __name__ == "__main__":
    root = tk.Tk(); ScraperGUI(root); root.mainloop()
