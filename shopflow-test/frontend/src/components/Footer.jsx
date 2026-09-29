import React from 'react';
import { ShoppingBag, ShieldCheck, Zap, RefreshCw, Server } from 'lucide-react';

export default function Footer({ setActivePage }) {
  return (
    <footer className="bg-slate-900 text-slate-400 text-xs border-t border-slate-800 mt-20">
      {/* Top Value Banner */}
      <div className="border-b border-slate-800/80 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-slate-800 text-brand-400 flex items-center justify-center">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <div className="text-white font-semibold text-sm">Ultra-Fast Delivery</div>
              <div className="text-slate-400 text-xs">Free shipping on $50+</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-slate-800 text-emerald-400 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-white font-semibold text-sm">Simulated Security</div>
              <div className="text-slate-400 text-xs">Production microservices</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-slate-800 text-indigo-400 flex items-center justify-center">
              <RefreshCw className="w-5 h-5" />
            </div>
            <div>
              <div className="text-white font-semibold text-sm">30-Day Guarantees</div>
              <div className="text-slate-400 text-xs">Instant mock returns</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-slate-800 text-amber-400 flex items-center justify-center">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <div className="text-white font-semibold text-sm">AIOps Testbed</div>
              <div className="text-slate-400 text-xs">Real telemetry signals</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-xs">
              <ShoppingBag className="w-3.5 h-3.5" />
            </div>
            <span className="text-white font-bold text-sm">ShopFlow Microservices</span>
            <span className="text-slate-500 text-xs">| AIOps Production Target Subject</span>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs">
            <button onClick={() => setActivePage('home')} className="hover:text-white transition-colors">Storefront</button>
            <button onClick={() => setActivePage('products')} className="hover:text-white transition-colors">Catalog</button>
            <button onClick={() => setActivePage('orders')} className="hover:text-white transition-colors">Orders</button>
            <button onClick={() => setActivePage('status')} className="hover:text-emerald-400 transition-colors">System Status (/status)</button>
            <button onClick={() => setActivePage('chaos')} className="hover:text-amber-400 transition-colors font-medium">Chaos Lab (/chaos)</button>
          </div>

          <div className="text-slate-500 text-xs">
            © 2026 ShopFlow Inc. Built for OpsPilot AIOps Challenge.
          </div>
        </div>
      </div>
    </footer>
  );
}
