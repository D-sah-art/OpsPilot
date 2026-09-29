import React, { useState, useEffect } from 'react';
import { Activity, Server, Database, Layers, CheckCircle2, AlertTriangle, XCircle, RefreshCw, Cpu, HardDrive, ArrowRight, ShieldCheck } from 'lucide-react';
import { fetchTopology, fetchTelemetryMetrics, fetchHealthSummary } from '../services/api';

export default function StatusPage({ setActivePage }) {
  const [topology, setTopology] = useState({ nodes: [], edges: [] });
  const [metrics, setMetrics] = useState({ services: {} });
  const [healthSummary, setHealthSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const loadStatusData = async () => {
    try {
      const [topoData, metricsData, healthData] = await Promise.all([
        fetchTopology(),
        fetchTelemetryMetrics(),
        fetchHealthSummary()
      ]);
      setTopology(topoData);
      setMetrics(metricsData);
      setHealthSummary(healthData);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      console.error('Status fetch error:', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatusData();
    if (!autoRefresh) return;
    const interval = setInterval(loadStatusData, 2500);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const getStatusDisplay = (status) => {
    switch (status) {
      case 'Operational':
        return {
          label: 'Operational',
          badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          dotClass: 'bg-emerald-500',
          icon: CheckCircle2,
          borderClass: 'border-emerald-200/80 hover:border-emerald-300'
        };
      case 'Degraded':
        return {
          label: 'Degraded Performance',
          badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
          dotClass: 'bg-amber-500 animate-ping',
          icon: AlertTriangle,
          borderClass: 'border-amber-300 bg-amber-50/20'
        };
      case 'Major Outage':
        return {
          label: 'Major Outage',
          badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
          dotClass: 'bg-rose-500 animate-ping',
          icon: XCircle,
          borderClass: 'border-rose-400 bg-rose-50/30'
        };
      case 'Recovering':
        return {
          label: 'Recovering',
          badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
          dotClass: 'bg-blue-500 animate-pulse',
          icon: RefreshCw,
          borderClass: 'border-blue-300 bg-blue-50/20'
        };
      default:
        return {
          label: status || 'Unknown',
          badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
          dotClass: 'bg-slate-400',
          icon: Activity,
          borderClass: 'border-slate-200'
        };
    }
  };

  const servicesList = [
    { id: 'api-gateway', name: 'API Gateway', tier: 'Edge Router', icon: Layers },
    { id: 'product-api', name: 'Product API', tier: 'Core Service', icon: Server },
    { id: 'order-api', name: 'Order API', tier: 'Core Service', icon: Server },
    { id: 'checkout-api', name: 'Checkout API', tier: 'Core Service', icon: Server },
    { id: 'auth-service', name: 'Auth Service', tier: 'Core Service', icon: ShieldCheck },
    { id: 'postgresql', name: 'PostgreSQL Primary DB', tier: 'Data Tier', icon: Database },
    { id: 'redis', name: 'Redis Cache Cluster', tier: 'Cache Tier', icon: Database },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-10 animate-fade-in pb-12">
      
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-brand-600"></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">Live Health & Telemetry</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">System Status</h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time status of all 7 ShopFlow microservices and datastores
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs font-medium text-slate-600 bg-white px-3 py-2 rounded-xl border border-slate-200 shadow-sm cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded text-brand-600 focus:ring-brand-500 w-4 h-4 cursor-pointer"
            />
            <span>Auto-refresh (2.5s)</span>
          </label>

          <button
            onClick={loadStatusData}
            className="p-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 shadow-sm transition-colors"
            title="Refresh now"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setActivePage('chaos')}
            className="px-4 py-2 rounded-xl bg-slate-900 text-amber-400 hover:bg-slate-800 text-xs font-bold transition-all shadow-sm"
          >
            Launch Chaos Lab →
          </button>
        </div>
      </div>

      {/* Global Health Summary Bar */}
      {healthSummary && (
        <div className={`p-6 rounded-3xl border shadow-sm flex flex-col md:flex-row items-center justify-between gap-6 ${
          healthSummary.status === 'Operational'
            ? 'bg-emerald-500/10 border-emerald-200 text-emerald-900'
            : (healthSummary.status === 'Degraded' ? 'bg-amber-500/10 border-amber-300 text-amber-900' : 'bg-rose-500/10 border-rose-300 text-rose-900')
        }`}>
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-md ${
              healthSummary.status === 'Operational' ? 'bg-emerald-600' : (healthSummary.status === 'Degraded' ? 'bg-amber-600' : 'bg-rose-600')
            }`}>
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider opacity-80">Overall System Health</div>
              <div className="text-2xl font-black">{healthSummary.status}</div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs font-semibold">
            <div className="bg-white/80 backdrop-blur-sm px-4 py-2 rounded-xl border border-black/5">
              <span className="text-slate-500 block text-[10px]">OPERATIONAL</span>
              <span className="text-sm font-bold text-slate-900">{healthSummary.healthy_services}/{healthSummary.total_services} Services</span>
            </div>

            <div className="bg-white/80 backdrop-blur-sm px-4 py-2 rounded-xl border border-black/5">
              <span className="text-slate-500 block text-[10px]">ACTIVE ALERTS</span>
              <span className="text-sm font-bold text-slate-900">{healthSummary.active_alerts_total} Total</span>
            </div>

            <div className="bg-white/80 backdrop-blur-sm px-4 py-2 rounded-xl border border-black/5">
              <span className="text-slate-500 block text-[10px]">CRITICAL</span>
              <span className="text-sm font-bold text-rose-600">{healthSummary.critical_alerts} Breaches</span>
            </div>
          </div>
        </div>
      )}

      {/* Microservices Status Grid */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Server className="w-4 h-4 text-brand-600" />
          <span>Microservices Telemetry Breakdown</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {servicesList.map((svc) => {
            const svcMetrics = metrics.services?.[svc.id] || {};
            const statusConfig = getStatusDisplay(svcMetrics.status || 'Operational');
            const Icon = svc.icon;

            return (
              <div
                key={svc.id}
                className={`bg-white rounded-2xl p-5 border shadow-sm transition-all duration-200 ${statusConfig.borderClass}`}
              >
                {/* Top Row: Service Name + Status Pill */}
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900">{svc.name}</h3>
                      <span className="text-[10px] text-slate-400 font-mono">{svc.tier}</span>
                    </div>
                  </div>

                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${statusConfig.badgeClass}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${statusConfig.dotClass}`}></span>
                    <span>{statusConfig.label}</span>
                  </span>
                </div>

                {/* Metrics Breakdown */}
                <div className="grid grid-cols-2 gap-2 text-xs pt-3 border-t border-slate-100">
                  <div className="bg-slate-50 rounded-xl p-2.5">
                    <span className="text-slate-400 block text-[10px]">p50 Latency</span>
                    <span className="font-bold text-slate-800">
                      {svcMetrics.latency_p50_ms ? `${svcMetrics.latency_p50_ms.toFixed(1)}ms` : '—'}
                    </span>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-2.5">
                    <span className="text-slate-400 block text-[10px]">Error Rate</span>
                    <span className={`font-bold ${svcMetrics.error_rate_pct > 5 ? 'text-rose-600' : 'text-slate-800'}`}>
                      {svcMetrics.error_rate_pct !== undefined ? `${svcMetrics.error_rate_pct.toFixed(1)}%` : '0.0%'}
                    </span>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-2.5">
                    <span className="text-slate-400 block text-[10px]">CPU Load</span>
                    <span className="font-bold text-slate-800">
                      {svcMetrics.cpu_pct ? `${svcMetrics.cpu_pct.toFixed(1)}%` : '12.0%'}
                    </span>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-2.5">
                    <span className="text-slate-400 block text-[10px]">Availability</span>
                    <span className="font-bold text-emerald-600">
                      {svcMetrics.availability_pct !== undefined ? `${svcMetrics.availability_pct.toFixed(1)}%` : '100%'}
                    </span>
                  </div>
                </div>

                {/* Service-specific extra telemetry info */}
                {svc.id === 'postgresql' && (
                  <div className="mt-3 text-[11px] text-slate-500 bg-slate-50 rounded-xl p-2 flex justify-between">
                    <span>Pool Active: <strong>{svcMetrics.db_connections_active || 4}/{svcMetrics.db_connections_max || 20}</strong></span>
                    <span>DB Latency: <strong>{svcMetrics.db_latency_ms?.toFixed(1) || 4.2}ms</strong></span>
                  </div>
                )}
                {svc.id === 'redis' && (
                  <div className="mt-3 text-[11px] text-slate-500 bg-slate-50 rounded-xl p-2 flex justify-between">
                    <span>Hits: <strong>{svcMetrics.redis_hits || 850}</strong></span>
                    <span>Misses: <strong>{svcMetrics.redis_misses || 24}</strong></span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Architecture Topology Graph Schema */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Logical Dependency Topology (`GET /api/topology`)</h3>
            <p className="text-xs text-slate-400">Machine-readable dependency graph for external AIOps correlation</p>
          </div>
          <span className="text-xs font-mono bg-slate-100 text-slate-700 px-2.5 py-1 rounded-lg">
            {topology.nodes?.length || 8} Nodes · {topology.edges?.length || 10} Edges
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="bg-slate-900 text-slate-300 rounded-2xl p-4 overflow-x-auto max-h-52">
            <div className="text-emerald-400 font-bold mb-2">// Active Dependencies Graph (Edges)</div>
            {topology.edges?.map((edge, idx) => (
              <div key={idx} className="py-0.5">
                <span className="text-indigo-400">{edge.source}</span>
                <span className="text-slate-500"> ──[{edge.protocol}]──&gt; </span>
                <span className="text-amber-300">{edge.target}</span>
              </div>
            ))}
          </div>

          <div className="bg-slate-900 text-slate-300 rounded-2xl p-4 overflow-x-auto max-h-52">
            <div className="text-emerald-400 font-bold mb-2">// Live Node Metadata</div>
            <pre className="text-[11px] leading-relaxed">
              {JSON.stringify(
                topology.nodes?.map(n => ({
                  id: n.id,
                  type: n.type,
                  status: n.live_status || 'Operational',
                  criticality: n.criticality
                })),
                null,
                2
              )}
            </pre>
          </div>
        </div>
      </div>

    </div>
  );
}
