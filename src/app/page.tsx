# L1-10: Line Range Index & Specification
# L12-40: Imports (React, Lucide, XLSX) and Type Definitions
# L42-55: Utility functions (cn, safeFetch)
# L57-100: ScraperPage component & State management
# L102-120: Lifecycle (useEffect) and Logging
# L122-135: Search functionality
# L137-200: Scraping Logic (Token -> Complexes -> Listings)
# L202-230: Data Export (XLSX)
# L232-400: UI Layout & Components (Tailwind CSS)

"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Search, Download, Play, CheckCircle, Loader2, Info } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import * as XLSX from "xlsx";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface Region {
  code: string;
  siName: string;
  guName: string;
  name: string;
  fullName: string;
}

interface Listing {
  complexNo: string;
  complexName: string;
  address: string;
  tradeType: string;
  area: string;
  price: string;
  floor: string;
  feature: string;
}

const VERSION = "v3.1.0-cloudtype";

export default function ScraperPage() {
  const [backendUrl, setBackendUrl] = useState("");
  const [regions, setRegions] = useState<Region[]>([]);
  const [searchTerm, setSearchVar] = useState("");
  const [searchResults, setSearchResults] = useState<Region[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [isScraping, setIsScraping] = useState(false);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [activeTab, setActiveTab] = useState("전체");

  useEffect(() => {
    fetch("https://raw.githubusercontent.com/Sprityoon/estimate_scraper/main/dong.json")
      .then((res) => res.json())
      .then((data) => setRegions(data))
      .catch(() => addLog("데이터 로드 실패"));
  }, []);

  const addLog = useCallback((msg: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  const safeFetch = async (url: string) => {
    const res = await fetch(url);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Error (${res.status}): ${text.slice(0, 30)}`);
    }
    return res.json();
  };

  const handleSearch = () => {
    if (!searchTerm.trim()) return;
    const q = searchTerm.trim().replace(/\s/g, "");
    const filtered = regions
      .filter((r) => r.name.replace(/\s/g, "").includes(q) || r.fullName.replace(/\s/g, "").includes(q))
      .slice(0, 50);
    setSearchResults(filtered);
  };

  const startScraping = async () => {
    if (!selectedRegion || !backendUrl) return;
    setIsScraping(true);
    setProgress(0);
    setListings([]);
    setLogs([]);
    
    try {
      let token = "";
      try {
        const githubTokenRes = await fetch("https://raw.githubusercontent.com/Sprityoon/estimate_scraper/main/token.json");
        const tokenData = await githubTokenRes.json();
        token = tokenData.token;
        addLog(`Token loaded (${new Date(tokenData.updated_at).toLocaleTimeString()})`);
      } catch (e) {
        const apiBase = backendUrl.replace(/\/$/, "");
        const tokenData = await safeFetch(`${apiBase}/api/token`);
        token = tokenData.token;
      }

      if (!token) throw new Error("No token");

      const apiBase = backendUrl.replace(/\/$/, "");
      const { complexes, error: compError } = await safeFetch(`${apiBase}/api/complexes?cortarNo=${selectedRegion.code}&token=${token}`);
      if (compError) throw new Error(compError);
      
      const allResults: Listing[] = [];
      for (let i = 0; i < complexes.length; i++) {
        const comp = complexes[i];
        const { listings: complexListings } = await safeFetch(`${apiBase}/api/listings?complexNo=${comp.complexNo}&token=${token}&page=1`);
        
        if (complexListings) {
          complexListings.forEach((l: any) => {
            allResults.push({
              complexNo: comp.complexNo,
              complexName: comp.complexName,
              address: comp.cortarAddress || selectedRegion.fullName,
              tradeType: l.tradeTypeName,
              area: `${l.area1}/${l.area2}`,
              price: l.rentPrc !== 0 ? `${l.dealOrWarrantPrc} / ${l.rentPrc}` : l.dealOrWarrantPrc,
              floor: l.floorInfo,
              feature: l.articleFeatureDesc
            });
          });
        }
        setProgress(Math.round(((i + 1) / complexes.length) * 100));
        setListings([...allResults]);
      }
    } catch (err: any) {
      addLog(`Error: ${err.message}`);
    } finally {
      setIsScraping(false);
    }
  };

  const exportExcel = () => {
    if (listings.length === 0) return;
    const filtered = activeTab === "전체" ? listings : listings.filter(l => l.tradeType === activeTab);
    const worksheet = XLSX.utils.json_to_sheet(filtered.map(l => ({
      "단지번호": l.complexNo, "아파트명": l.complexName, "주소": l.address,
      "거래방식": l.tradeType, "면적": l.area, "가격": l.price, "층수": l.floor, "특징": l.feature
    })));
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, activeTab);
    XLSX.writeFile(workbook, `${selectedRegion?.fullName}_${activeTab}.xlsx`);
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8 text-slate-900">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div>
            <h1 className="text-2xl font-bold text-blue-600 flex items-center gap-2"><Play className="fill-current" size={24} /> Naver Scraper Cloud</h1>
          </div>
          <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">{VERSION}</span>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-6">
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2"><Info size={20} className="text-blue-500" /> Backend Config</h2>
              <input
                type="text" placeholder="https://..."
                className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm font-mono"
                value={backendUrl} onChange={(e) => setBackendUrl(e.target.value)}
              />
            </section>

            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2"><Search size={20} /> Search</h2>
              <div className="flex gap-2">
                <input
                  type="text" className="flex-1 px-4 py-2 rounded-xl border border-slate-200 text-sm"
                  value={searchTerm} onChange={(e) => setSearchVar(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
                <button onClick={handleSearch} className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium">Find</button>
              </div>
              {searchResults.length > 0 && (
                <div className="max-h-48 overflow-y-auto border border-slate-100 rounded-xl divide-y">
                  {searchResults.map((r) => (
                    <button key={r.code} onClick={() => setSelectedRegion(r)} className={cn("w-full text-left px-4 py-3 text-sm", selectedRegion?.code === r.code ? "bg-blue-50 text-blue-700 font-bold" : "text-slate-600")}>
                      {r.fullName}
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <button disabled={!selectedRegion || isScraping} onClick={startScraping} className={cn("w-full py-4 rounded-xl flex items-center justify-center gap-2 font-bold transition-all", isScraping ? "bg-slate-100 text-slate-400" : "bg-blue-600 text-white")}>
                {isScraping ? <><Loader2 size={20} className="animate-spin" /> Working...</> : "Start Scraping"}
              </button>
              {isScraping && (
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div className="bg-blue-500 h-full transition-all" style={{ width: `${progress}%` }} />
                </div>
              )}
            </section>
          </div>

          <div className="lg:col-span-2 space-y-6">
            <section className="bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col h-[600px]">
              <div className="p-6 border-b flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {["전체", "매매", "전세", "월세"].map(tab => (
                    <button key={tab} onClick={() => setActiveTab(tab)} className={cn("text-sm font-semibold pb-1 border-b-2", activeTab === tab ? "border-blue-600 text-blue-600" : "border-transparent text-slate-400")}>{tab}</button>
                  ))}
                </div>
                <button disabled={listings.length === 0} onClick={exportExcel} className="text-sm flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-xl font-bold">Excel</button>
              </div>
              <div className="flex-1 overflow-auto">
                {listings.length > 0 ? (
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 bg-slate-50 text-slate-500">
                      <tr><th className="px-4 py-3">Complex</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Price</th><th className="px-4 py-3">Area</th></tr>
                    </thead>
                    <tbody className="divide-y">
                      {listings.filter(l => activeTab === "전체" || l.tradeType === activeTab).map((l, i) => (
                        <tr key={i} className="hover:bg-slate-50/50">
                          <td className="px-4 py-3 font-medium">{l.complexName}</td>
                          <td className="px-4 py-3"><span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100">{l.tradeType}</span></td>
                          <td className="px-4 py-3 font-bold">{l.price}</td>
                          <td className="px-4 py-3 text-slate-500">{l.area}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : <div className="h-full flex items-center justify-center text-slate-300"><Info size={48} /></div>}
              </div>
              <div className="bg-slate-900 text-slate-300 p-4 font-mono text-[10px] h-32 overflow-y-auto rounded-b-2xl">
                {logs.map((log, i) => <div key={i} className="mb-1 border-l border-slate-700 pl-2">{log}</div>)}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
