"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Search, Download, Play, CheckCircle, Loader2, Info } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

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

import * as XLSX from "xlsx";

const VERSION = "v3.0.0-web";

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

  // Load regions from GitHub or Local
  useEffect(() => {
    // In a real app, this would be your GitHub Raw URL
    // For now, we assume it's served from the same domain or public
    fetch("/dong.json")
      .then((res) => res.json())
      .then((data) => setRegions(data))
      .catch(() => addLog("법정동 데이터를 불러오는데 실패했습니다. public/dong.json 확인 필요."));
  }, []);

  const addLog = useCallback((msg: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  const handleSearch = () => {
    if (!searchTerm.trim()) return;
    const q = searchTerm.trim().replace(/\s/g, "");
    const filtered = regions
      .filter((r) => r.name.replace(/\s/g, "").includes(q) || r.fullName.replace(/\s/g, "").includes(q))
      .slice(0, 50);
    setSearchResults(filtered);
    addLog(`'${searchTerm}' 검색 완료. ${filtered.length}개 결과 발견.`);
  };

  const startScraping = async () => {
    if (!selectedRegion) return;
    setIsScraping(true);
    setProgress(0);
    setListings([]);
    setLogs([]);
    addLog(`${selectedRegion.fullName} 수집 시작...`);

    try {
      // 1. Get Token
      addLog("인증 토큰 획득 중...");
      const tokenRes = await fetch("/api/token");
      const { token, error: tokenError } = await tokenRes.json();
      if (tokenError) throw new Error(tokenError);
      addLog("토큰 획득 성공.");

      // 2. Get Complexes
      addLog("단지 목록 조회 중...");
      const compRes = await fetch(`/api/complexes?cortarNo=${selectedRegion.code}&token=${token}`);
      const { complexes, error: compError } = await compRes.json();
      if (compError) throw new Error(compError);
      addLog(`${complexes.length}개 단지 발견.`);

      // 3. Get Listings for each complex
      const allResults: Listing[] = [];
      for (let i = 0; i < complexes.length; i++) {
        const comp = complexes[i];
        addLog(`'${comp.complexName}' 매물 수집 중... (${i + 1}/${complexes.length})`);
        
        // Simplified: Fetch page 1 only for web demo (to avoid long waits/timeouts)
        const listRes = await fetch(`/api/listings?complexNo=${comp.complexNo}&token=${token}&page=1`);
        const { listings: complexListings } = await listRes.json();
        
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
        setListings([...allResults]); // Live update
      }

      addLog(`수집 완료! 총 ${allResults.length}개 매물을 가져왔습니다.`);
    } catch (err: any) {
      addLog(`오류 발생: ${err.message}`);
    } finally {
      setIsScraping(false);
    }
  };

  const exportExcel = () => {
    if (listings.length === 0) return;
    const filtered = activeTab === "전체" ? listings : listings.filter(l => l.tradeType === activeTab);
    
    // 엑셀 시트 데이터 생성
    const worksheet = XLSX.utils.json_to_sheet(filtered.map(l => ({
      "단지번호": l.complexNo,
      "아파트명": l.complexName,
      "주소": l.address,
      "거래방식": l.tradeType,
      "공급/전용면적": l.area,
      "가격(보증금/월세)": l.price,
      "층수": l.floor,
      "매물특징": l.feature
    })));
    
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, activeTab);
    
    // 파일 다운로드
    XLSX.writeFile(workbook, `${selectedRegion?.fullName}_${activeTab}_${new Date().getTime()}.xlsx`);
    addLog(`${activeTab} 데이터를 엑셀로 내보냈습니다.`);
  };

  const tabs = ["전체", "매매", "전세", "월세"];

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8 font-sans text-slate-900">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <header className="flex items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div>
            <h1 className="text-2xl font-bold text-blue-600 flex items-center gap-2">
              <Play className="fill-current" size={24} /> 네이버 부동산 수집기 Web
            </h1>
            <p className="text-slate-500 text-sm mt-1">Vercel Serverless 기반 실시간 매물 수집</p>
          </div>
          <div className="hidden md:block">
            <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium border border-blue-100">
              {VERSION}
            </span>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar: Search & Selection */}
          <div className="space-y-6">
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Search size={20} className="text-slate-400" /> 지역 검색
              </h2>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="동/읍/리 입력 (예: 거여, 괴안)"
                  className="flex-1 px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-sm"
                  value={searchTerm}
                  onChange={(e) => setSearchVar(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
                <button
                  onClick={handleSearch}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl transition-colors font-medium text-sm"
                >
                  검색
                </button>
              </div>

              {searchResults.length > 0 && (
                <div className="max-h-48 overflow-y-auto border border-slate-100 rounded-xl divide-y divide-slate-50">
                  {searchResults.map((r) => (
                    <button
                      key={r.code}
                      onClick={() => setSelectedRegion(r)}
                      className={cn(
                        "w-full text-left px-4 py-3 text-sm transition-colors hover:bg-blue-50/50",
                        selectedRegion?.code === r.code ? "bg-blue-50 text-blue-700 font-semibold" : "text-slate-600"
                      )}
                    >
                      {r.fullName}
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Play size={20} className="text-slate-400" /> 수집 실행
              </h2>
              <div className="p-4 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center">
                {selectedRegion ? (
                  <div className="space-y-1">
                    <p className="text-xs text-slate-400 uppercase tracking-wider font-bold">선택된 지역</p>
                    <p className="text-sm font-medium text-slate-700">{selectedRegion.fullName}</p>
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">지역을 먼저 검색하고 선택해주세요</p>
                )}
              </div>
              <button
                disabled={!selectedRegion || isScraping}
                onClick={startScraping}
                className={cn(
                  "w-full py-4 rounded-xl flex items-center justify-center gap-2 font-bold transition-all shadow-md active:scale-[0.98]",
                  isScraping 
                    ? "bg-slate-100 text-slate-400 cursor-not-allowed" 
                    : "bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20"
                )}
              >
                {isScraping ? (
                  <>
                    <Loader2 size={20} className="animate-spin" /> 수집 진행 중...
                  </>
                ) : (
                  <>수집 시작하기</>
                )}
              </button>

              {isScraping && (
                <div className="space-y-2 pt-2">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-blue-600">{progress}% 진행됨</span>
                    <span className="text-slate-400">{listings.length}개 발견</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-blue-500 h-full transition-all duration-500" 
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}
            </section>
          </div>

          {/* Main: Logs & Results */}
          <div className="lg:col-span-2 space-y-6">
            <section className="bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col h-[600px]">
              <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {tabs.map(tab => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={cn(
                        "text-sm font-semibold pb-1 border-b-2 transition-all",
                        activeTab === tab ? "border-blue-600 text-blue-600" : "border-transparent text-slate-400 hover:text-slate-600"
                      )}
                    >
                      {tab}
                    </button>
                  ))}
                </div>
                <button
                  disabled={listings.length === 0}
                  onClick={exportExcel}
                  className="text-sm flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-xl transition-colors font-bold disabled:opacity-50"
                >
                  <Download size={16} /> 엑셀 다운로드
                </button>
              </div>

              <div className="flex-1 overflow-auto p-0 relative">
                {listings.length > 0 ? (
                  <table className="w-full text-left text-sm border-collapse">
                    <thead className="sticky top-0 bg-slate-50 text-slate-500 font-medium">
                      <tr>
                        <th className="px-4 py-3 border-b">단지명</th>
                        <th className="px-4 py-3 border-b">거래</th>
                        <th className="px-4 py-3 border-b">가격</th>
                        <th className="px-4 py-3 border-b">면적</th>
                        <th className="px-4 py-3 border-b">층</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {listings
                        .filter(l => activeTab === "전체" || l.tradeType === activeTab)
                        .map((l, i) => (
                          <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                            <td className="px-4 py-3 font-medium text-slate-800">{l.complexName}</td>
                            <td className="px-4 py-3">
                              <span className={cn(
                                "px-2 py-0.5 rounded text-[10px] font-bold",
                                l.tradeType === "매매" ? "bg-red-50 text-red-600" : 
                                l.tradeType === "전세" ? "bg-blue-50 text-blue-600" : "bg-orange-50 text-orange-600"
                              )}>
                                {l.tradeType}
                              </span>
                            </td>
                            <td className="px-4 py-3 font-bold text-slate-900">{l.price}</td>
                            <td className="px-4 py-3 text-slate-500">{l.area}</td>
                            <td className="px-4 py-3 text-slate-500">{l.floor}</td>
                          </tr>
                        ))
                      }
                    </tbody>
                  </table>
                ) : (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-300">
                    <Info size={48} strokeWidth={1.5} />
                    <p className="mt-4 font-medium">수집된 데이터가 여기에 표시됩니다</p>
                  </div>
                )}
              </div>

              {/* Real-time Logs Console */}
              <div className="bg-slate-900 text-slate-300 p-4 font-mono text-[10px] h-32 overflow-y-auto rounded-b-2xl border-t border-slate-800">
                <div className="flex items-center gap-2 mb-2 text-slate-500 font-bold uppercase tracking-widest text-[9px]">
                  <CheckCircle size={10} /> Live Output
                </div>
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
