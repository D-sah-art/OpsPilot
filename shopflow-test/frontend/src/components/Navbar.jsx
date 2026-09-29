import React, { useState } from 'react';
import { ShoppingBag, Search, User, Activity, Flame, ChevronDown, Check } from 'lucide-react';
import { useApp, DEMO_USERS } from '../context/AppContext';

export default function Navbar({ activePage, setActivePage, searchQuery, setSearchQuery }) {
  const { cartCount, setIsCartOpen, currentUser, switchUser, systemHealth, chaosState } = useApp();
  const [userDropdown, setUserDropdown] = useState(false);

  const getStatusBadge = () => {
    const status = systemHealth.status;
    if (status === 'Operational') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Operational
        </span>
      );
    } else if (status === 'Degraded') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
          <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
          Degraded ({systemHealth.active_alerts_total} alerts)
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
          {status} ({systemHealth.active_alerts_total} alerts)
        </span>
      );
    }
  };

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
      {/* Top Banner if Chaos is active */}
      {chaosState.state === 'RUNNING' && (
        <div className="bg-gradient-to-r from-rose-600 via-amber-600 to-rose-600 text-white text-xs py-1.5 px-4 text-center font-medium tracking-wide flex items-center justify-center gap-2">
          <Flame className="w-4 h-4 animate-bounce" />
          <span>CHAOS LAB SCENARIO ACTIVE: <strong>{chaosState.scenario_name}</strong> — Stage {chaosState.current_stage}/{chaosState.total_stages}</span>
          <button
            onClick={() => setActivePage('chaos')}
            className="underline ml-2 hover:text-white/80 font-bold"
          >
            Open Chaos Lab →
          </button>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          
          {/* Logo */}
          <div className="flex items-center gap-6">
            <button
              onClick={() => setActivePage('home')}
              className="flex items-center gap-2.5 text-left group"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20 group-hover:scale-105 transition-transform">
                <ShoppingBag className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-1">
                  Shop<span className="text-brand-600">Flow</span>
                </span>
                <span className="text-[10px] block font-mono text-slate-400 -mt-1 uppercase tracking-wider">
                  Test Subject v1.0
                </span>
              </div>
            </button>

            {/* Navigation Links */}
            <nav className="hidden md:flex items-center gap-1">
              <button
                onClick={() => setActivePage('home')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activePage === 'home'
                    ? 'text-brand-600 bg-brand-50'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                Storefront
              </button>
              <button
                onClick={() => setActivePage('products')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activePage === 'products'
                    ? 'text-brand-600 bg-brand-50'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                All Products
              </button>
              <button
                onClick={() => setActivePage('orders')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activePage === 'orders'
                    ? 'text-brand-600 bg-brand-50'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                My Orders
              </button>
            </nav>
          </div>

          {/* Search Bar */}
          <div className="flex-1 max-w-md hidden sm:block">
            <div className="relative">
              <input
                type="text"
                placeholder="Search products, gear, electronics..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  if (activePage !== 'products') setActivePage('products');
                }}
                className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-100 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white transition-all text-slate-800 placeholder-slate-400"
              />
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            </div>
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-3">
            
            {/* Status Link */}
            <button
              onClick={() => setActivePage('status')}
              className="flex items-center gap-1.5"
              title="View Live Topology and Microservices Health"
            >
              {getStatusBadge()}
            </button>

            {/* Chaos Lab Link */}
            <button
              onClick={() => setActivePage('chaos')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activePage === 'chaos'
                  ? 'bg-rose-600 text-white shadow-md shadow-rose-600/30'
                  : 'bg-slate-900 text-amber-400 hover:bg-slate-800 hover:text-amber-300'
              }`}
            >
              <Flame className="w-3.5 h-3.5 text-amber-400" />
              <span>Chaos Lab</span>
            </button>

            {/* Demo User Switcher */}
            <div className="relative">
              <button
                onClick={() => setUserDropdown(!userDropdown)}
                className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-100 border border-slate-200 transition-colors text-xs text-slate-700 font-medium"
              >
                <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center font-bold text-[10px]">
                  {currentUser.full_name.split(' ').map(n => n[0]).join('')}
                </div>
                <span className="hidden lg:inline">{currentUser.full_name.split(' ')[0]}</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {userDropdown && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-200 py-1.5 z-50 animate-fade-in">
                  <div className="px-3 py-2 border-b border-slate-100">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Switch Demo Account</p>
                  </div>
                  {DEMO_USERS.map((u) => (
                    <button
                      key={u.id}
                      onClick={() => {
                        switchUser(u);
                        setUserDropdown(false);
                      }}
                      className="w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-slate-50 text-slate-700"
                    >
                      <div>
                        <div className="font-semibold">{u.full_name}</div>
                        <div className="text-[11px] text-slate-400">{u.email}</div>
                      </div>
                      {currentUser.id === u.id && (
                        <Check className="w-4 h-4 text-brand-600" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Cart Button */}
            <button
              onClick={() => setIsCartOpen(true)}
              className="relative p-2.5 rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-sm"
              aria-label="View Cart"
            >
              <ShoppingBag className="w-5 h-5" />
              {cartCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 bg-brand-600 text-white text-[11px] font-bold rounded-full w-5 h-5 flex items-center justify-center shadow-md">
                  {cartCount}
                </span>
              )}
            </button>
          </div>

        </div>
      </div>
    </header>
  );
}
