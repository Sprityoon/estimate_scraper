"use client";

// L1-10: Imports & Types
// L12-30: Utility functions (safeFetch)
// L32-150: Scraper Logic (Relative paths)
// L152-350: JSX UI Layout (Removed Backend Config)

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
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  };

  const handleSearch = () => {
    const q = searchTerm.trim().replace(/\s/g, "");
    setSearchResults(regions.filter(r => r.name.includes(q) || r.fullName.includes(q)).slice(0, 50));
  };

  const startScraping = async () => {
    if (!selectedRegion) return;
    setIsScraping(true); setProgress(0); setListings([]); setLogs([]);
    try {
      addLog("인증 진행 중...");
      let token = "";
      try {
        const res = await fetch("https://raw.githubusercontent.com/Sprityoon/estimate_scraper/main/token.json", { cache: 'no-store' });
        const data = await res.json();
        token = data.token;
      } catch {
        const data = await safeFetch("/api/token");
        token = data.token;
      }

      const { complexes } = await safeFetch(`/api/complexes?cortarNo=${selectedRegion.code}&token=${token}`);
      const results: Listing[] = [];
      for (let i = 0; i < complexes.length; i++) {
        const c = complexes[i];
        addLog(`수집 중: ${c.complexName}`);
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
      addLog("완료!");
    } catch (e: any) { addLog(`오류: ${e.message}`); }
    finally { setIsScraping(false); }
  };

  const exportExcel = () => {
    const filtered = activeTab === "전체" ? listings : listings.filter(l => l.tradeType === activeTab);
    const ws = XLSX.utils.json_to_sheet(filtered);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Results");
    XLSX.writeFile(wb, "results.xlsx");
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8 text-slate-900 font-sans">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h1 className="text-2xl font-bold text-blue-600 flex items-center gap-2"><Play size={24} /> Naver Scraper Cloud</h1>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-6">
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <h2 className="text-lg font-semibold">Search</h2>
              <div className="flex gap-2">
                <input type="text" className="flex-1 px-4 py-2 rounded-xl border border-slate-200 text-sm" value={searchTerm} onChange={e => setSearchVar(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSearch()} />
                <button onClick={handleSearch} className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm">Find</button>
              </div>
              <div className="max-h-60 overflow-y-auto divide-y">
                {searchResults.map(r => <button key={r.code} onClick={() => setSelectedRegion(r)} className={cn("w-full text-left p-3 text-sm", selectedRegion?.code === r.code ? "bg-blue-50 text-blue-700 font-bold" : "")}>{r.fullName}</button>)}
              </div>
            </section>
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <button disabled={!selectedRegion || isScraping} onClick={startScraping} className={cn("w-full py-4 rounded-xl font-bold text-white", isScraping ? "bg-slate-300" : "bg-blue-600")}>{isScraping ? "Working..." : "Start"}</button>
              {isScraping && <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden"><div className="bg-blue-500 h-full transition-all" style={{ width: `${progress}%` }} /></div>}
            </section>
          </div>

          <div className="lg:col-span-2 space-y-6">
            <section className="bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col h-[600px]">
              <div className="p-6 border-b flex items-center justify-between">
                <div className="flex gap-4">
                  {["전체", "매매", "전세", "월세"].map(t => <button key={t} onClick={() => setActiveTab(t)} className={cn("text-sm font-semibold pb-1 border-b-2", activeTab === t ? "border-blue-600 text-blue-600" : "border-transparent text-slate-400")}>{t}</button>)}
                </div>
                <button onClick={exportExcel} className="text-sm px-4 py-2 bg-emerald-50 text-emerald-700 rounded-xl font-bold">Excel</button>
              </div>
              <div className="flex-1 overflow-auto relative">
                {listings.length > 0 ? (
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 bg-slate-50 text-slate-500">
                      <tr><th className="p-4">Complex</th><th className="p-4">Type</th><th className="p-4">Price</th></tr>
                    </thead>
                    <tbody className="divide-y">
                      {listings.filter(l => activeTab === "전체" || l.tradeType === activeTab).map((l, i) => (
                        <tr key={i} className="hover:bg-slate-50">
                          <td className="p-4 font-medium">{l.complexName}</td>
                          <td className="p-4">{l.tradeType}</td>
                          <td className="p-4 font-bold">{l.price}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : <div className="h-full flex items-center justify-center text-slate-300"><Info size={48} /></div>}
              </div>
              <div className="bg-slate-900 text-slate-300 p-4 font-mono text-[10px] h-32 overflow-y-auto rounded-b-2xl">
                {logs.map((l, i) => <div key={i} className="mb-1 border-l border-slate-700 pl-2">{l}</div>)}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
