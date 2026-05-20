"use client";

// L1-10: Imports & Types
// L12-25: Utility functions
// L27-130: Scraper Logic (Mandatory fresh token acquisition)
// L132-330: UI Layout

import React, { useState, useEffect, useCallback } from "react";
import { Search, Download, Play, Loader2, Info } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import * as XLSX from "xlsx";

function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

interface Region { code: string; fullName: string; name: string; }
interface Listing { complexNo: string; complexName: string; address: string; tradeType: string; area: string; price: string; floor: string; feature: string; }

export default function ScraperPage() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [searchTerm, setSearchVar] = useState("");
  const [searchResults, setSearchResults] = useState<Region[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [isScraping, setIsScraping] = useState(false);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [activeTab, setActiveTab] = useState("전체");

  const addLog = useCallback((msg: string) => { setLogs(v => [...v, `[${new Date().toLocaleTimeString()}] ${msg}`]); }, []);

  useEffect(() => {
    fetch("https://raw.githubusercontent.com/Sprityoon/estimate_scraper/main/dong.json")
      .then(res => res.json()).then(setRegions).catch(() => addLog("데이터 로드 실패"));
  }, [addLog]);

  const safeFetch = async (url: string) => {
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  };

  const handleSearch = () => {
    const q = searchTerm.trim().replace(/\s/g, "");
    if (!q) return;
    setSearchResults(regions.filter(r => r.name.includes(q) || r.fullName.includes(q)).slice(0, 50));
  };

  const startScraping = async () => {
    if (!selectedRegion) return;
    setIsScraping(true); setProgress(0); setListings([]); setLogs([]);
    try {
      addLog("실시간 인증 토큰 획득 중...");
      const { token } = await safeFetch("/api/token");
      addLog("인증 성공. 단지 목록 조회 중...");

      const { complexes } = await safeFetch(`/api/complexes?cortarNo=${selectedRegion.code}&token=${token}`);
      if (!complexes || complexes.length === 0) throw new Error("단지가 없습니다.");
      
      addLog(`${complexes.length}개 단지 발견. 매물 수집 시작...`);
      const results: Listing[] = [];
      
      for (let i = 0; i < complexes.length; i++) {
        const c = complexes[i];
        const { listings: lList } = await safeFetch(`/api/listings?complexNo=${c.complexNo}&token=${token}`);
        if (lList) {
          lList.forEach((l: any) => results.push({
            complexNo: String(c.complexNo), complexName: c.complexName, address: c.cortarAddress || selectedRegion.fullName,
            tradeType: l.tradeTypeName, area: `${l.area1}/${l.area2}`, price: l.rentPrc !== 0 ? `${l.dealOrWarrantPrc}/${l.rentPrc}` : String(l.dealOrWarrantPrc),
            floor: l.floorInfo, feature: l.articleFeatureDesc
          }));
        }
        setProgress(Math.round(((i + 1) / complexes.length) * 100));
        setListings([...results]);
      }
      addLog("모든 수집이 완료되었습니다!");
    } catch (e: any) { 
      addLog(`오류: ${e.message}`); 
    } finally { 
      setIsScraping(false); 
    }
  };

  const exportExcel = () => {
    if (listings.length === 0) return;
    const filtered = activeTab === "전체" ? listings : listings.filter(l => l.tradeType === activeTab);
    const ws = XLSX.utils.json_to_sheet(filtered);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Results");
    XLSX.writeFile(wb, `${selectedRegion?.name}_${activeTab}.xlsx`);
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8 text-slate-900 font-sans">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h1 className="text-2xl font-bold text-blue-600 flex items-center gap-2"><Play size={24} /> Naver Scraper Cloud</h1>
          <div className="flex items-center gap-2">
            <CheckCircle className="text-emerald-500" size={16} />
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Seoul Node Active</span>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-6">
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2"><Search size={20} /> 지역 검색</h2>
              <div className="flex gap-2">
                <input type="text" className="flex-1 px-4 py-2 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none transition-all" placeholder="거여, 괴안 등 입력" value={searchTerm} onChange={e => setSearchVar(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSearch()} />
                <button onClick={handleSearch} className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">검색</button>
              </div>
              <div className="max-h-60 overflow-y-auto divide-y border border-slate-100 rounded-xl">
                {searchResults.map(r => <button key={r.code} onClick={() => setSelectedRegion(r)} className={cn("w-full text-left p-3 text-sm transition-colors hover:bg-slate-50", selectedRegion?.code === r.code ? "bg-blue-50 text-blue-700 font-bold" : "")}>{r.fullName}</button>)}
              </div>
            </section>
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <div className="p-4 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center">
                {selectedRegion ? <div className="space-y-1"><p className="text-xs text-slate-400 font-bold uppercase">Target</p><p className="text-sm font-medium text-slate-700">{selectedRegion.fullName}</p></div> : <p className="text-sm text-slate-400">지역을 선택해주세요</p>}
              </div>
              <button disabled={!selectedRegion || isScraping} onClick={startScraping} className={cn("w-full py-4 rounded-xl font-bold text-white shadow-lg transition-all active:scale-95", isScraping ? "bg-slate-300 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700")}>
                {isScraping ? <><Loader2 size={20} className="animate-spin inline mr-2" /> 수집 중...</> : "수집 시작하기"}
              </button>
              {isScraping && <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden"><div className="bg-blue-500 h-full transition-all duration-500" style={{ width: `${progress}%` }} /></div>}
            </section>
          </div>

          <div className="lg:col-span-2 space-y-6">
            <section className="bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col h-[600px] overflow-hidden">
              <div className="p-6 border-b flex items-center justify-between bg-white z-20">
                <div className="flex gap-4">
                  {["전체", "매매", "전세", "월세"].map(t => <button key={t} onClick={() => setActiveTab(t)} className={cn("text-sm font-semibold pb-1 border-b-2 transition-all", activeTab === t ? "border-blue-600 text-blue-600" : "border-transparent text-slate-400 hover:text-slate-600")}>{t}</button>)}
                </div>
                <button disabled={listings.length === 0} onClick={exportExcel} className="text-sm px-4 py-2 bg-emerald-50 text-emerald-700 rounded-xl font-bold hover:bg-emerald-100 transition-colors disabled:opacity-50">Excel 내보내기</button>
              </div>
              <div className="flex-1 overflow-auto relative bg-white">
                {listings.length > 0 ? (
                  <table className="w-full text-left text-sm border-collapse">
                    <thead className="sticky top-0 bg-slate-50 text-slate-500 z-10">
                      <tr><th className="p-4 font-bold border-b text-xs uppercase tracking-wider">단지명</th><th className="p-4 font-bold border-b text-xs uppercase tracking-wider">유형</th><th className="p-4 font-bold border-b text-xs uppercase tracking-wider">가격</th></tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {listings.filter(l => activeTab === "전체" || l.tradeType === activeTab).map((l, i) => (
                        <tr key={i} className="hover:bg-slate-50 transition-colors">
                          <td className="p-4 font-medium text-slate-700">{l.complexName}</td>
                          <td className="p-4"><span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600">{l.tradeType}</span></td>
                          <td className="p-4 font-bold text-slate-900">{l.price}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : <div className="h-full flex flex-col items-center justify-center text-slate-300 gap-4"><Info size={48} strokeWidth={1} /><p className="font-medium">수집된 데이터가 표시됩니다</p></div>}
              </div>
              <div className="bg-slate-900 text-slate-400 p-4 font-mono text-[10px] h-32 overflow-y-auto border-t border-slate-800">
                <div className="text-slate-600 font-bold mb-2 uppercase tracking-tighter flex items-center gap-1"><Loader2 size={10} /> Live System Log</div>
                {logs.map((l, i) => <div key={i} className="mb-1 border-l border-slate-700 pl-2 ml-1">{l}</div>)}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

import { CheckCircle } from "lucide-react";
