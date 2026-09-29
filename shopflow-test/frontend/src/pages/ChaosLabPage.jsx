import React, { useState, useEffect } from 'react';
import { Flame, RotateCcw, AlertOctagon, Terminal, Activity, ShieldAlert, CheckCircle, Database, Server, RefreshCw, Zap, ArrowRight, Radio } from 'lucide-react';
import { fetchChaosStatus, fetchChaosScenarios, triggerChaosScenario, resetChaos, fetchTelemetryAlerts, fetchTelemetryLogs, fetchTelemetryMetrics } from '../services/api';
import { useApp } from '../context/AppContext';

export default function ChaosLabPage({ setActivePage }) {
  const { showToast } = useApp();
  const [status, setStatus] = useState({ state: 'IDLE' });
  const [scenarios, setScenarios] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [loadingAction, setLoadingAction] = useState(false);

  const refreshChaosData = async () => {
    try {
      const [st, sc, al, lg, mt] = await Promise.all([
        fetchChaosStatus(),
        fetchChaosScenarios(),
        fetchTelemetryAlerts(40),
        fetchTelemetryLogs(20),
        fetchTelemetryMetrics()
      ]);
      setStatus(st);
      setScenarios(sc);
      setAlerts(al);
      setLogs(lg);
      setMetrics(mt);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    refreshChaosData();
    const interval = setInterval(refreshChaosData, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleTrigger = async (scenarioId) => {
    setLoadingAction(true);
    try {
      await triggerChaosScenario(scenarioId);
      showToast(`Chaos scenario '${scenarioId}' activated!`, 'warning');
      await refreshChaosData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleReset = async () => {
    setLoadingAction(true);
    try {
      await resetChaos();
      showToast('All chaos simulations cleared. System healthy.', 'success');
      await refreshChaosData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingAction(false);
    }
  };

  const stagesForDatabaseCascade = [
    { num: 1, title: 'DB Query Degradation', svc: 'PostgreSQL', desc: 'Slow query lock contention' },
    { num: 2, title: 'Pool Exhaustion', svc: 'PostgreSQL', desc: '19/20 connections locked' },
    { num: 3, title: 'Order API Timeout', svc: 'Order API', desc: 'Query pool timeout exceptions' },
    { num: 4, title: 'Checkout Failure', svc: 'Checkout API', desc: 'Downstream timeout & retries' },
    { num: 5, title: 'Gateway 502/504', svc: 'API Gateway', desc: '504 Gateway Timeout surge' },
    { num: 6, title: 'Customer Degradation', svc: 'ShopFlow Frontend', desc: 'Graceful degradation active' },
  ];

  return (
    <div className="bg-slate-950 text-slate-100 rounded-3xl p-6 sm:p-10 border border-slate-800 shadow-2xl space-y-10 animate-fade-in font-sans">
      
      {/* Top Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 border-b border-slate-800 pb-8">
        <div>
          <div className="flex items-center gap-2 text-rose-500 text-xs font-mono font-bold uppercase tracking-wider mb-2">
            <Radio className="w-4 h-4 animate-pulse" />
            <span>Developer Fault Injection & Telemetry Generator</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white flex items-center gap-3">
            <span>Chaos Lab</span>
            <span className="text-xs px-3 py-1 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 font-mono">
              Safe In-Memory Simulation
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Trigger deterministic, controlled microservice failure scenarios to generate rich multi-layer telemetry signals (~28–30 causally ordered alerts) for external OpsPilot correlation.
          </p>
        </div>

        {/* Global Reset Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            disabled={loadingAction}
            className="px-5 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg shadow-emerald-900/30 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset Everything (Clean Baseline)</span>
          </button>
        </div>
      </div>

      {/* Active Scenario Banner */}
      <div className={`p-6 rounded-2xl border flex flex-col md:flex-row items-center justify-between gap-6 ${
        status.state === 'RUNNING'
          ? 'bg-rose-950/40 border-rose-800 text-rose-200'
          : 'bg-slate-900/80 border-slate-800 text-slate-300'
      }`}>
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-white ${
            status.state === 'RUNNING' ? 'bg-rose-600 animate-pulse' : 'bg-slate-800'
          }`}>
            <Flame className="w-6 h-6" />
          </div>
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Simulation Status</div>
            <div className="text-xl font-bold text-white flex items-center gap-2">
              <span>{status.scenario_name || 'Idle / Operational Baseline'}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                status.state === 'RUNNING' ? 'bg-rose-500 text-white' : 'bg-slate-800 text-slate-400'
              }`}>
                {status.state}
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
          <div className="bg-slate-900 px-3.5 py-2 rounded-xl border border-slate-800">
            <span className="text-slate-500 block text-[10px]">CURRENT STAGE</span>
            <span className="font-bold text-amber-400">{status.current_stage || 0} / {status.total_stages || 0}</span>
          </div>

          <div className="bg-slate-900 px-3.5 py-2 rounded-xl border border-slate-800">
            <span className="text-slate-500 block text-[10px]">TOTAL ALERTS</span>
            <span className="font-bold text-rose-400">{status.alert_count || 0} Generated</span>
          </div>

          <div className="bg-slate-900 px-3.5 py-2 rounded-xl border border-slate-800">
            <span className="text-slate-500 block text-[10px]">AFFECTED TARGETS</span>
            <span className="font-bold text-slate-200">
              {status.affected_services?.length > 0 ? status.affected_services.join(', ') : 'None (Healthy)'}
            </span>
          </div>
        </div>
      </div>

      {/* Causal Scenario Timeline Visualizer (for database_cascade) */}
      <div className="bg-slate-900/60 rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Primary Scenario Causal Progression: Database Cascade
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-400">Deterministic Causal Chain</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          {stagesForDatabaseCascade.map((stg) => {
            const isPassed = status.active_scenario === 'database_cascade' && status.current_stage >= stg.num;
            const isCurrent = status.active_scenario === 'database_cascade' && status.current_stage === stg.num;

            return (
              <div
                key={stg.num}
                className={`p-4 rounded-xl border transition-all ${
                  isCurrent
                    ? 'bg-rose-950/60 border-rose-500 shadow-lg shadow-rose-950/50 scale-105'
                    : (isPassed
                      ? 'bg-amber-950/30 border-amber-800/80 text-amber-200'
                      : 'bg-slate-900 border-slate-800/80 text-slate-500')
                }`}
              >
                <div className="flex items-center justify-between text-[11px] font-mono mb-2">
                  <span className="font-bold">Stage {stg.num}</span>
                  <span className="px-1.5 py-0.5 rounded bg-black/40 text-[9px]">{stg.svc}</span>
                </div>
                <div className="text-xs font-bold text-white mb-1">{stg.title}</div>
                <div className="text-[10px] text-slate-400 leading-tight">{stg.desc}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Scenario Trigger Deck */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <Flame className="w-4 h-4 text-amber-400" />
          <span>Available Chaos Scenarios</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          
          {/* 1. Database Cascade (Primary Highlight) */}
          <div className="bg-gradient-to-b from-rose-950/50 to-slate-900 rounded-2xl p-5 border-2 border-rose-600/80 shadow-xl space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500 text-white">
                  PRIMARY DEMO
                </span>
                <span className="text-xs font-mono text-rose-400 font-bold">~28–30 ALERTS</span>
              </div>
              <h4 className="text-base font-black text-white">Database Cascade Outage</h4>
              <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                Simulates PostgreSQL query lock contention escalating to connection pool exhaustion, Order API timeout, Checkout API failure, Gateway 504 errors, and customer degradation.
              </p>
            </div>
            <button
              onClick={() => handleTrigger('database_cascade')}
              disabled={loadingAction}
              className="w-full py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2"
            >
              <Flame className="w-4 h-4" />
              <span>Trigger Database Cascade</span>
            </button>
          </div>

          {/* 2. Redis Failure */}
          <div className="bg-slate-900 rounded-2xl p-5 border border-slate-800 space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  HIGH SEVERITY
                </span>
                <span className="text-xs font-mono text-slate-400">REDIS</span>
              </div>
              <h4 className="text-sm font-bold text-white">Redis Cache Outage</h4>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Simulates Redis cluster downtime triggering cache miss storm and high latency across catalog queries.
              </p>
            </div>
            <button
              onClick={() => handleTrigger('redis_failure')}
              disabled={loadingAction}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-400 font-bold text-xs transition-colors"
            >
              Trigger Redis Failure
            </button>
          </div>

          {/* 3. Checkout Failure */}
          <div className="bg-slate-900 rounded-2xl p-5 border border-slate-800 space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                  CRITICAL
                </span>
                <span className="text-xs font-mono text-slate-400">CHECKOUT-API</span>
              </div>
              <h4 className="text-sm font-bold text-white">Payment Simulator Outage</h4>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Simulates payment gateway rejection causing isolated checkout transaction failures.
              </p>
            </div>
            <button
              onClick={() => handleTrigger('checkout_failure')}
              disabled={loadingAction}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-rose-400 font-bold text-xs transition-colors"
            >
              Trigger Checkout Failure
            </button>
          </div>

          {/* 4. High Memory */}
          <div className="bg-slate-900 rounded-2xl p-5 border border-slate-800 space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                  MEDIUM
                </span>
                <span className="text-xs font-mono text-slate-400">MEMORY</span>
              </div>
              <h4 className="text-sm font-bold text-white">Checkout API Memory Leak</h4>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Simulates memory accumulation and GC pauses on the checkout-api node.
              </p>
            </div>
            <button
              onClick={() => handleTrigger('high_memory')}
              disabled={loadingAction}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-yellow-400 font-bold text-xs transition-colors"
            >
              Trigger High Memory
            </button>
          </div>

          {/* 5. High Latency */}
          <div className="bg-slate-900 rounded-2xl p-5 border border-slate-800 space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                  MEDIUM
                </span>
                <span className="text-xs font-mono text-slate-400">NETWORK</span>
              </div>
              <h4 className="text-sm font-bold text-white">Inter-Service Latency</h4>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Injects simulated 1800ms packet latency across edge-to-core routes.
              </p>
            </div>
            <button
              onClick={() => handleTrigger('high_latency')}
              disabled={loadingAction}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-indigo-400 font-bold text-xs transition-colors"
            >
              Trigger High Latency
            </button>
          </div>

          {/* 6. Traffic Spike */}
          <div className="bg-slate-900 rounded-2xl p-5 border border-slate-800 space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  TRAFFIC
                </span>
                <span className="text-xs font-mono text-slate-400">GATEWAY</span>
              </div>
              <h4 className="text-sm font-bold text-white">Flash Sale Surge</h4>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Simulates a 10x traffic spike with 720 RPS and queue build-up.
              </p>
            </div>
            <button
              onClick={() => handleTrigger('traffic_spike')}
              disabled={loadingAction}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-blue-400 font-bold text-xs transition-colors"
            >
              Trigger Traffic Spike
            </button>
          </div>

        </div>
      </div>

      {/* Telemetry Stream: Live Alerts & Structured Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Alerts Stream */}
        <div className="bg-slate-900 rounded-2xl p-5 border border-slate-800 space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                Live Alert Feed (`GET /telemetry/alerts`)
              </h4>
            </div>
            <span className="text-[11px] font-mono text-slate-400">{alerts.length} Records</span>
          </div>

          <div className="space-y-2.5 overflow-y-auto max-h-80 pr-1 text-xs font-mono">
            {alerts.length === 0 ? (
              <div className="text-center py-12 text-slate-600">
                No active alerts. System healthy.
              </div>
            ) : (
              alerts.map((alt) => (
                <div
                  key={alt.id}
                  className={`p-3 rounded-xl border ${
                    alt.severity === 'CRITICAL'
                      ? 'bg-rose-950/40 border-rose-900/80 text-rose-200'
                      : (alt.severity === 'WARNING' ? 'bg-amber-950/40 border-amber-900/80 text-amber-200' : 'bg-slate-800/50 border-slate-700 text-slate-300')
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-[11px]">{alt.alert_type}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      alt.severity === 'CRITICAL' ? 'bg-rose-500 text-white' : 'bg-amber-500 text-slate-950'
                    }`}>
                      {alt.severity}
                    </span>
                  </div>
                  <p className="text-[11px] opacity-90 leading-tight mb-1.5">{alt.message}</p>
                  <div className="flex items-center justify-between text-[10px] opacity-60">
                    <span>Service: <strong>{alt.service}</strong> {alt.dependency && `→ ${alt.dependency}`}</span>
                    <span>{new Date(alt.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Logs Stream */}
        <div className="bg-slate-900 rounded-2xl p-5 border border-slate-800 space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                Structured JSON Logs (`GET /telemetry/logs`)
              </h4>
            </div>
            <span className="text-[11px] font-mono text-slate-400">{logs.length} Log Entries</span>
          </div>

          <div className="space-y-2 overflow-y-auto max-h-80 pr-1 font-mono text-[11px]">
            {logs.length === 0 ? (
              <div className="text-center py-12 text-slate-600">
                Awaiting log stream...
              </div>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-slate-300 flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-brand-400 font-bold">[{log.service}]</span>
                    <span className={`text-[10px] font-bold ${
                      log.level === 'ERROR' ? 'text-rose-400' : (log.level === 'WARN' ? 'text-amber-400' : 'text-emerald-400')
                    }`}>
                      {log.level} · {log.event}
                    </span>
                  </div>
                  <div className="text-slate-200">{log.message}</div>
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>{log.latency_ms ? `latency: ${log.latency_ms}ms` : ''}</span>
                    <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
