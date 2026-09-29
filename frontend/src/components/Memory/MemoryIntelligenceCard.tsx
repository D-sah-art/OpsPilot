import React, { useState } from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import { Brain, CheckCircle2, History, Trash2, Sparkles, Database, Layers } from "lucide-react";
import { apiClient } from "../../api/client";
import type { HindsightMemoryItem } from "../../api/types";

export const MemoryIntelligenceCard: React.FC = () => {
  const { rca, refreshAll } = useOpsPilot();
  const [isClearing, setIsClearing] = useState(false);
  const [clearMessage, setClearMessage] = useState<string | null>(null);

  const recalled: HindsightMemoryItem[] = rca?.recalled_memories || [];
  const memoryCount = rca?.memories_recalled ?? recalled.length;

  const handleClearBank = async () => {
    try {
      setIsClearing(true);
      const res = await apiClient.clearMemoryBank();
      setClearMessage(res.message || "Bank cleared successfully");
      setTimeout(() => setClearMessage(null), 4000);
      await refreshAll();
    } catch (err: any) {
      setClearMessage(err?.message || "Failed to clear bank");
    } finally {
      setIsClearing(false);
    }

  };

  const connectionStatus = rca?.connection_status || "CONNECTED_TO_HINDSIGHT";
  const memorySource = rca?.memory_source || "Vectorize Hindsight Engine";

  const isConnected = connectionStatus === "CONNECTED_TO_HINDSIGHT";
  const isFallback = connectionStatus === "LOCAL_FALLBACK" || connectionStatus === "HINDSIGHT_UNAVAILABLE";

  return (
    <div className="bg-dark-900/90 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col justify-between">
      <div>
        {/* Header Bar */}
        <div className="flex items-center justify-between pb-3 border-b border-dark-800 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
                  Hindsight Vector Memory Intelligence
                </h3>
                {isConnected ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    Connected to Hindsight
                  </span>
                ) : isFallback ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                    Hindsight Unavailable — Local Fallback Active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    Hindsight Disabled
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Vectorize Hindsight Persistent Memory System • Multi-Strategy Incident Recall
              </p>
            </div>
          </div>


          <button
            onClick={handleClearBank}
            disabled={isClearing}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-dark-800 hover:bg-dark-700 text-slate-400 hover:text-slate-200 border border-slate-700 text-xs font-mono transition-colors disabled:opacity-50"
            title="Reset Hindsight demo memory bank for first-run vs second-run demonstration"
          >
            <Trash2 className="w-3.5 h-3.5 text-rose-400" />
            <span>{isClearing ? "Clearing..." : "Reset Memory Bank"}</span>
          </button>
        </div>

        {clearMessage && (
          <div className="mb-3 px-3 py-1.5 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs font-mono flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>{clearMessage}</span>
          </div>
        )}

        {/* Status KPI Grid */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="bg-dark-950/70 border border-slate-800/80 rounded-lg p-3">
            <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5 mb-1">
              <Database className="w-3.5 h-3.5 text-indigo-400" />
              <span>Target Bank</span>
            </div>
            <div className="text-xs font-mono font-bold text-slate-200 truncate">
              opspilot-incidents-bank
            </div>
          </div>

          <div className="bg-dark-950/70 border border-slate-800/80 rounded-lg p-3">
            <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5 mb-1">
              <History className="w-3.5 h-3.5 text-sky-400" />
              <span>Memories Recalled</span>
            </div>
            <div className="text-sm font-mono font-bold text-sky-300">
              {memoryCount} {memoryCount === 1 ? "Incident" : "Incidents"}
            </div>
          </div>

          <div className="bg-dark-950/70 border border-slate-800/80 rounded-lg p-3">
            <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5 mb-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>RCA Context</span>
            </div>
            <div className="text-xs font-mono font-bold text-amber-300">
              {memoryCount > 0 ? "Memory-Augmented" : "Stateless Baseline"}
            </div>
          </div>
        </div>

        {/* Recalled Memories List */}
        {recalled.length > 0 ? (
          <div className="space-y-3">
            <div className="text-xs font-mono font-semibold text-slate-300 flex items-center justify-between">
              <span>RECALLED HISTORICAL EXPERIENCES</span>
              <span className="text-[11px] text-slate-500 font-normal">
                Supplied as context to Root Cause Analysis
              </span>
            </div>

            {recalled.map((mem: HindsightMemoryItem, idx: number) => (
              <div
                key={mem.id || idx}
                className="bg-dark-950/80 border border-indigo-900/40 hover:border-indigo-500/50 rounded-lg p-3 text-xs space-y-2 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center font-mono font-bold text-[10px]">
                      #{idx + 1}
                    </span>
                    <span className="font-mono font-bold text-slate-200">
                      {mem.title}
                    </span>
                  </div>
                  {mem.recovery_verified && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-400 border border-emerald-800">
                      Verified 200 OK
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400 bg-dark-900/50 p-2 rounded">
                  <div>
                    <span className="text-slate-500">Root Cause:</span>{" "}
                    <span className="text-rose-400 font-bold">
                      {mem.root_cause_service || "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">Action:</span>{" "}
                    <span className="text-cyan-300">
                      {mem.remediation_action || "N/A"}
                    </span>
                  </div>
                </div>

                <p className="text-slate-300 text-[11px] leading-relaxed italic border-l-2 border-indigo-500/50 pl-2">
                  "{mem.content}"
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-dark-950/40 border border-dashed border-slate-800 rounded-lg p-4 text-center">
            <Layers className="w-6 h-6 text-slate-600 mx-auto mb-2" />
            <p className="text-xs font-mono text-slate-400">
              No historical memories recalled for this incident yet.
            </p>
            <p className="text-[11px] text-slate-500 mt-1 max-w-md mx-auto">
              Run 1: OpsPilot will resolve and retain the incident in Hindsight.
              Run 2: Subsequent similar incidents will recall this experience automatically!
            </p>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="mt-4 pt-3 border-t border-dark-800 text-[11px] font-mono text-slate-500 flex items-center justify-between">
        <span>Source: {memorySource}</span>
        <span>Vectorize Multi-Arm Recall (Semantic + Keyword + Graph)</span>
      </div>

    </div>
  );
};
