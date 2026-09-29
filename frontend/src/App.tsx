import React, { useState } from "react";
import { OpsPilotProvider, useOpsPilot } from "./context/OpsPilotContext";
import { TopNavbar } from "./components/Header/TopNavbar";
import { HeroIncidentBanner } from "./components/Header/HeroIncidentBanner";
import { KpiSummaryBar } from "./components/Header/KpiSummaryBar";
import { TopologyGraph } from "./components/Topology/TopologyGraph";
import { IncidentList } from "./components/Incidents/IncidentList";
import { CorrelationEvidence } from "./components/Correlation/CorrelationEvidence";
import { RootCauseCard } from "./components/RootCause/RootCauseCard";
import { RemediationControl } from "./components/Remediation/RemediationControl";
import { MemoryIntelligenceCard } from "./components/Memory/MemoryIntelligenceCard";
import { RecoveryBanner } from "./components/Recovery/RecoveryBanner";

import { AuditTimeline } from "./components/Audit/AuditTimeline";
import { AlertFeed } from "./components/Alerts/AlertFeed";
import { BenchmarkModal } from "./components/Correlation/BenchmarkModal";
import { AlertCircle, X } from "lucide-react";

const MainDashboard: React.FC = () => {
  const { error, clearError, isLoading } = useOpsPilot();
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState<boolean>(false);

  return (
    <div className="min-h-screen bg-surface-bg text-slate-100 flex flex-col selection:bg-accent-sky selection:text-slate-950">
      {/* Top Navbar */}
      <TopNavbar onOpenBenchmark={() => setIsBenchmarkOpen(true)} />

      {/* Global Error Banner */}
      {error && (
        <div className="bg-rose-950/80 border-b border-rose-800 text-rose-200 px-4 py-2.5 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>{error}</span>
          </div>
          <button
            onClick={clearError}
            className="p-1 rounded hover:bg-rose-900/50 text-rose-400 hover:text-rose-200"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-[1920px] w-full mx-auto px-4 sm:px-6 py-4 space-y-4">
        {/* Hero Active Incident Banner */}
        <HeroIncidentBanner />

        {/* KPI Summary Bar */}
        <KpiSummaryBar />

        {/* Row 1: Topology Graph & Incident Correlation */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-7 flex flex-col">
            <TopologyGraph />
          </div>

          <div className="lg:col-span-5 flex flex-col space-y-4">
            <IncidentList />
            <CorrelationEvidence />
          </div>
        </div>

        {/* Row 2: Hindsight Memory Intelligence & Root Cause Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MemoryIntelligenceCard />
          <RootCauseCard />
        </div>

        {/* Row 3: Safety-Gated Remediation & Recovery Verification */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RemediationControl />
          <RecoveryBanner />
        </div>

        {/* Row 4: Immutable Audit Trail */}
        <div className="grid grid-cols-1 gap-6">
          <AuditTimeline />
        </div>


        {/* Row 4: Raw Telemetry Stream */}
        <AlertFeed />
      </main>

      {/* Benchmark Comparison Modal */}
      <BenchmarkModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
      />

      {/* Footer */}
      <footer className="border-t border-dark-800 bg-dark-950 px-6 py-4 text-center text-xs font-mono text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
          <span>OpsPilot v1.0 • Autonomous SRE Incident Response Command Center</span>
        </div>
        <div>
          <span>Architecture: Frontend (5173) → OpsPilot (8080) → ShopFlow (8000)</span>
        </div>
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <OpsPilotProvider>
      <MainDashboard />
    </OpsPilotProvider>
  );
}
