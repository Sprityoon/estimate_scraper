"use client";

# L1-10: Imports and Type Definitions
# L12-30: Utility functions and Constants
# L32-150: ScraperPage Component Logic
# L152-300: JSX UI Layout

import React, { useState, useEffect, useCallback } from "react";
import { Search, Download, Play, CheckCircle, Loader2, Info } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import * as XLSX from "xlsx";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface Region {
  code: string; siName: string; guName: string; name: string; fullName: string;
}

interface Listing {
  complexNo: string; complexName: string; address: string; tradeType: string;
  area: string; price: string; floor: string; feature: string;
}

const VERSION = "v3.2.1-cloudtype";

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

  const addLog = useCallback((msg: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  useEffect(() => {
    fetch("https://raw.githubusercontent.com/Sprityoon/estimate_scraper/main/dong.json")
      .then((res) => res.json())
      .then((data) => setRegions(data))
      .catch(() => addLog("데이터 로드 실패"));
  }, [addLog]);

  const safeFetch = async (url: string) => {
    const res = await fetch(url);
    const contentType = res.headers.get("content-type");
    if (!res.ok || !contentType?.includes("application/json")) {
      const text = await res.text();
      if (text.includes("<!DOCTYPE") || text.includes("<html")) throw new Error("Backend URL is incorrect (HTML received)");
      throw new Error(`Error (${res.status}): ${text.slice(0, 30)}`);
    }
    return res.json();
  };

  const handleSearch = () => {
    if (!searchTerm.trim()) return;
    const q = searchTerm.trim().replace(/\s/g, "");
    setSearchResults(regions.filter((r) => r.name.replace(/\s/g, "").includes(q) || r.fullName.replace(/\s/g, "").includes(q)).slice(0, 50));
  };

  const startScraping = async () => {
    if (!selectedRegion || !backendUrl) return;
    setIsScraping(true); setProgress(0); setListings([]); setLogs([]);
    const apiBase = backendUrl.replace(/\/$/, "");
    try {
      let token = "";
      try {
        const githubTokenRes = await fetch("https://raw.githubusercontent.com/Sprityoon/estimate_scraper/main/token.json", { cache: 'no-store' });
        const tokenData = await githubTokenRes.json();
        const ageMin = (new Date().getTime() - new Date(tokenData.updated_at).getTime()) / 60000;
        if (ageMin < 60) {
          token = tokenData.token;
          addLog(`Using cached token (${Math.round(ageMin)}m old)`);
        } else {
          addLog("Token expired. Fetching fresh one...");
        }
      } catch (e) {
        addLog("Cache unavailable.");
      }

      if (!token) {
        const tokenData = await safeFetch(`${apiBase}/api/token`);
        token = tokenData.token;
        addLog("New token acquired");
      }

      if (!token) throw new Error("No token");
      const { complexes, error: compError } = await safeFetch(`${apiBase}/api/complexes?cortarNo=${selectedRegion.code}&token=${token}`);
      if (compError) throw new Error(compError);
      
      const allResults: Listing[] = [];
      for (let i = 0; i < complexes.length; i++) {
        const comp = complexes[i];
        addLog(`Fetching '${comp.complexName}'... (${i + 1}/${complexes.length})`);
        const { listings: complexListings } = await safeFetch(`${apiBase}/api/listings?complexNo=${comp.complexNo}&token=${token}&page=1`);
        if (complexListings) {
          complexListings.forEach((l: any) => {
            allResults.push({
              complexNo: String(comp.complexNo),
              complexName: comp.complexName,
              address: comp.cortarAddress || selectedRegion.fullName,
              tradeType: l.tradeTypeName,
              area: `${l.area1}/${l.area2}`,
              price: l.rentPrc !== 0 ? `${l.dealOrWarrantPrc} / ${l.rentPrc}` : String(l.dealOrWarrantPrc),
              floor: l.floorInfo,
              feature: l.articleFeatureDesc
            });
          });
        }
        setProgress(Math.round(((i + 1) / complexes.length) * 100));
        setListings([...allResults]);
      }
      addLog(`Complete! ${allResults.length} listings found.`);
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
    <div className="min-h-screen bg-slate-50 p-4 md:p-8 text-slate-900 font-sans">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h1 className="text-2xl font-bold text-blue-600 flex items-center gap-2"><Play className="fill-current" size={24} /> Naver Scraper Cloud</h1>
          <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">{VERSION}</span>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-6">
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2"><Info size={20} className="text-blue-500" /> Backend Config</h2>
              <input type="text" placeholder="https://port-0-xxx.cloudtype.app" className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm font-mono focus:ring-2 focus:ring-blue-500/20 outline-none" value={backendUrl} onChange={(e) => setBackendUrl(e.target.value)} />
              <p className="text-[10px] text-slate-400 leading-relaxed">* Cloudtype 'Python' 서비스의 접속 주소를 입력하세요.</p>
            </section>
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2"><Search size={20} /> Search</h2>
              <div className="flex gap-2">
                <input type="text" className="flex-1 px-4 py-2 rounded-xl border border-slate-200 text-sm outline-none" value={searchTerm} onChange={(e) => setSearchVar(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSearch()} />
                <button onClick={handleSearch} className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">Find</button>
              </div>
              {searchResults.length > 0 && (
                <div className="max-h-48 overflow-y-auto border border-slate-100 rounded-xl divide-y">
                  {searchResults.map((r) => (
                    <button key={r.code} onClick={() => setSelectedRegion(r)} className={cn("w-full text-left px-4 py-3 text-sm transition-colors hover:bg-slate-50", selectedRegion?.code === r.code ? "bg-blue-50 text-blue-700 font-bold" : "text-slate-600")}>
                      {r.fullName}
                    </button>
                  ))}
                </div>
              )}
            </section>
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <div className="p-4 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center">
                {selectedRegion ? (
                  <div className="space-y-1">
                    <p className="text-xs text-slate-400 font-bold">Selected Region</p>
                    <p className="text-sm font-medium text-slate-700">{selectedRegion.fullName}</p>
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">Search and select a region</p>
                )}
              </div>
              <button disabled={!selectedRegion || isScraping || !backendUrl} onClick={startScraping} className={cn("w-full py-4 rounded-xl flex items-center justify-center gap-2 font-bold transition-all", isScraping ? "bg-slate-100 text-slate-400" : "bg-blue-600 text-white hover:bg-blue-700")}>
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
            <section className="bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col h-[650px]">
              <div className="p-6 border-b flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {["전체", "매매", "전세", "월세"].map(tab => (
                    <button key={tab} onClick={() => setActiveTab(tab)} className={cn("text-sm font-semibold pb-1 border-b-2 transition-all", activeTab === tab ? "border-blue-600 text-blue-600" : "border-transparent text-slate-400 hover:text-slate-600")}>{tab}</button>
                  ))}
                </div>
                <button disabled={listings.length === 0} onClick={exportExcel} className="text-sm flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-xl font-bold hover:bg-emerald-100 transition-colors"><Download size={16} /> Excel</button>
              </div>
              <div className="flex-1 overflow-auto relative">
                {listings.length > 0 ? (
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 bg-slate-50 text-slate-500 z-10">
                      <tr>
                        <th className="px-4 py-3 border-b">Complex</th>
                        <th className="px-4 py-3 border-b">Type</th>
                        <th className="px-4 py-3 border-b">Price</th>
                        <th className="px-4 py-3 border-b">Area</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {listings.filter(l => activeTab === "전체" || l.tradeType === activeTab).map((l, i) => (
                        <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                          <td className="px-4 py-3 font-medium text-slate-800">{l.complexName}</td>
                          <td className="px-4 py-3">
                            <span className={cn(
                              "px-2 py-0.5 rounded text-[10px] font-bold",
                              l.tradeType === "매매" ? "bg-red-50 text-red-600" : l.tradeType === "전세" ? "bg-blue-50 text-blue-600" : "bg-orange-50 text-orange-600"
                            )}>
                              {l.tradeType}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-bold text-slate-900">{l.price}</td>
                          <td className="px-4 py-3 text-slate-500">{l.area}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-300">
                    <Info size={48} strokeWidth={1.5} />
                    <p className="mt-4 font-medium">Scraped data will appear here</p>
                  </div>
                )}
              </div>
              <div className="bg-slate-900 text-slate-300 p-4 font-mono text-[10px] h-32 overflow-y-auto rounded-b-2xl border-t border-slate-800">
                {logs.map((log, i) => (
                  <div key={i} className="mb-1 leading-relaxed border-l border-slate-700 pl-2 ml-1">
                    {log}
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
