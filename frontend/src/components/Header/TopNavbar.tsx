import React from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import {
  Activity,
  RefreshCw,
  Zap,
  BarChart3,
  Radio,
  ShieldCheck,
  RotateCcw,
} from "lucide-react";

interface TopNavbarProps {
  onOpenBenchmark: () => void;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({ onOpenBenchmark }) => {
  const {
    health,
    isActionLoading,
    isPolling,
    triggerSync,
    triggerCorrelation,
    triggerReset,
    togglePolling,
  } = useOpsPilot();

  const isShopFlowConnected = health?.shopflow === "connected";

  return (
    <header className="bg-surface-panel/95 backdrop-blur-md border-b border-surface-border sticky top-0 z-50 px-4 sm:px-6 py-2.5">
      <div className="max-w-[1920px] mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        {/* LEFT: Brand Identity */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-cyan/10 border border-accent-cyan/30 flex items-center justify-center text-accent-sky shadow-sm">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight text-white font-sans">
                Ops<span className="text-accent-sky">Pilot</span>
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-elevated text-slate-400 border border-surface-border font-mono">
                v1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-normal leading-none mt-0.5">
              Live Incident Command Center
            </p>
          </div>
        </div>

        {/* CENTER: System Status Strip */}
        <div className="flex items-center gap-2.5 bg-surface-bg/80 px-3 py-1.5 rounded-lg border border-surface-border text-xs font-mono">
          {/* Backend Health */}
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50"></span>
            <span className="text-slate-400 text-[11px]">Backend</span>
            <span className="text-slate-200 text-[11px] font-semibold">:8080</span>
            <span className="text-emerald-400 text-[10px] font-bold">HEALTHY</span>
          </div>

          <span className="text-surface-border font-light">|</span>

          {/* ShopFlow Testbed */}
          <div className="flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isShopFlowConnected ? "bg-emerald-400" : "bg-rose-400 animate-ping"
              }`}
            ></span>
            <span className="text-slate-400 text-[11px]">ShopFlow</span>
            <span className="text-slate-200 text-[11px] font-semibold">:8000</span>
            <span
              className={`text-[10px] font-bold ${
                isShopFlowConnected ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {isShopFlowConnected ? "LIVE" : "OFF"}
            </span>
          </div>

          <span className="text-surface-border font-light">|</span>

          {/* Safety Gate Mode */}
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3 h-3 text-accent-sky" />
            <span className="text-slate-400 text-[11px]">Safety</span>
            <span className="text-accent-sky text-[10px] font-bold">SIMULATION</span>
          </div>
        </div>

        {/* RIGHT: Compact Action Buttons */}
        <div className="flex items-center gap-2">
          {/* Sync Button */}
          <button
            onClick={() => triggerSync()}
            disabled={isActionLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-surface-elevated hover:bg-surface-border text-slate-300 border border-surface-border hover:border-slate-600 transition-all disabled:opacity-50"
            title="Ingest latest telemetry from ShopFlow"
          >
            <RefreshCw className={`w-3 h-3 ${isActionLoading ? "animate-spin text-accent-sky" : "text-slate-400"}`} />
            <span>Sync</span>
          </button>

          {/* Correlate Button (Primary Action) */}
          <button
            onClick={() => triggerCorrelation("dependency_aware")}
            disabled={isActionLoading}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-accent-blue hover:bg-blue-500 text-white shadow-sm transition-all disabled:opacity-50"
            title="Execute Dependency-Aware Correlation"
          >
            <Zap className="w-3 h-3 fill-yellow-300 text-yellow-300" />
            <span>Correlate</span>
          </button>

          {/* Benchmark Button */}
          <button
            onClick={onOpenBenchmark}
            disabled={isActionLoading}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-surface-elevated hover:bg-surface-border text-slate-300 border border-surface-border transition-all"
            title="Compare Time-Only vs Dependency-Aware"
          >
            <BarChart3 className="w-3 h-3 text-accent-purple" />
            <span className="hidden sm:inline">Benchmark</span>
          </button>

          {/* Reset Demo State Button */}
          <button
            onClick={() => triggerReset()}
            disabled={isActionLoading}
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-surface-elevated hover:bg-rose-950/40 text-slate-300 hover:text-rose-300 border border-surface-border hover:border-rose-800/50 transition-all disabled:opacity-50"
            title="Reset OpsPilot and ShopFlow to clean baseline state for demo"
          >
            <RotateCcw className={`w-3 h-3 ${isActionLoading ? "animate-spin" : "text-slate-400"}`} />
            <span className="hidden md:inline">Reset</span>
          </button>

          {/* Polling Indicator */}
          <button
            onClick={togglePolling}
            className={`flex items-center gap-1 px-2.5 py-1.5 text-xs font-mono rounded-lg border transition-all ${
              isPolling
                ? "bg-emerald-950/30 text-emerald-300 border-emerald-800/40"
                : "bg-surface-elevated text-slate-400 border-surface-border"
            }`}
            title={isPolling ? "Auto-refreshing (Click to pause)" : "Paused (Click to resume)"}
          >
            <Radio className={`w-2.5 h-2.5 ${isPolling ? "animate-pulse text-emerald-400" : "text-slate-500"}`} />
            <span className="text-[10px]">{isPolling ? "LIVE" : "PAUSED"}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
