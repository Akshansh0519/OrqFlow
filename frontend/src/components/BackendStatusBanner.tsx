import { useState, useEffect } from "react";
import { Loader2, X } from "lucide-react";

type ServiceStatus = "CHECKING" | "WAKING_UP" | "ALL_ONLINE" | "DISMISSED";

const CONFIGURED_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function getApiBase() {
  if (CONFIGURED_API_BASE_URL) return CONFIGURED_API_BASE_URL;
  if (window.location.port === "5173") return `http://${window.location.hostname}:8000`;
  return "";
}

export function BackendStatusBanner() {
  const [overallStatus, setOverallStatus] = useState<ServiceStatus>("CHECKING");
  const [attemptCount, setAttemptCount] = useState(0);

  useEffect(() => {
    let isMounted = true;
    let timer: ReturnType<typeof setTimeout>;

    const checkHealth = async () => {
      if (!isMounted) return;
      const apiBase = getApiBase();

      try {
        const res = await fetch(`${apiBase}/api/health`);
        if (res.ok) {
          if (!isMounted) return;
          setOverallStatus("ALL_ONLINE");
        } else {
          throw new Error("Backend not OK");
        }
      } catch (err) {
        if (!isMounted) return;
        setOverallStatus("WAKING_UP");
        setAttemptCount((prev) => prev + 1);
        timer = setTimeout(checkHealth, 3000); // Check every 3 seconds
      }
    };

    checkHealth();

    return () => {
      isMounted = false;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (overallStatus === "DISMISSED") return null;

  return (
    <div className="fixed bottom-6 right-6 z-[100] max-w-sm w-full mx-4 transition-all duration-500 ease-in-out font-mono">
      {/* 1. Checking / Waking Up Caution Card */}
      {(overallStatus === "CHECKING" || overallStatus === "WAKING_UP") && (
        <div className="bg-[#121820]/95 backdrop-blur-xl border border-amber-500/40 rounded-2xl p-5 shadow-2xl shadow-amber-950/30 text-white relative overflow-hidden animate-in fade-in slide-in-from-bottom-5 duration-300">
          <div className="absolute top-0 left-0 h-1 bg-gradient-to-r from-amber-500 via-orange-500 to-amber-300 animate-pulse w-full" />
          
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
              </span>
              <h4 className="font-bold text-sm tracking-tight text-amber-300 flex items-center gap-1.5 font-sans">
                Render Free Tier Notice
              </h4>
            </div>
            <span className="text-[10px] font-mono bg-amber-500/10 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/20">
              Attempt #{attemptCount || 1}
            </span>
          </div>

          <p className="text-xs text-gray-300 leading-relaxed mb-4 font-sans">
            Caution: The API runs on <strong className="text-white">Render Free Tier</strong>. If inactive, the OrqFlow API and its 3 MCP servers take <span className="text-amber-400 font-semibold">~50 seconds to warm up</span>.
            <br />
            <span className="text-gray-400 block mt-1.5 italic">We are waking up the multi-agent backend right now...</span>
          </p>

          <div className="flex items-center justify-between text-[10px] text-gray-400 border-t border-white/5 pt-2">
            <span className="flex items-center gap-1"><Loader2 size={10} className="animate-spin" /> Checking every 3s</span>
            <button
              onClick={() => setOverallStatus("DISMISSED")}
              className="text-gray-400 hover:text-white underline transition-colors"
            >
              Hide Warning
            </button>
          </div>
        </div>
      )}

      {/* 2. All Online Success Card */}
      {overallStatus === "ALL_ONLINE" && (
        <div className="bg-[#101915]/95 backdrop-blur-xl border border-emerald-500/50 rounded-2xl p-5 shadow-2xl shadow-emerald-950/40 text-white relative overflow-hidden animate-in fade-in zoom-in-95 duration-300">
          <div className="absolute top-0 left-0 h-1 bg-gradient-to-r from-emerald-400 via-teal-400 to-emerald-500 w-full" />
          
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              <h4 className="font-bold text-sm tracking-tight text-emerald-300 font-sans">
                Backend is Online!
              </h4>
            </div>
            <button
              onClick={() => setOverallStatus("DISMISSED")}
              className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X size={14} />
            </button>
          </div>

          <p className="text-xs text-gray-300 leading-relaxed mb-4 font-sans">
            The OrqFlow API returned <strong className="text-emerald-400">200 OK</strong>. The multi-agent LangGraph system is fully online.
          </p>

          <button
            onClick={() => setOverallStatus("DISMISSED")}
            className="w-full py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-lg text-[11px] font-bold tracking-wide text-white shadow-lg shadow-emerald-600/30 transition-all font-sans"
          >
            Got It, Continue to OrqFlow
          </button>
        </div>
      )}
    </div>
  );
}
