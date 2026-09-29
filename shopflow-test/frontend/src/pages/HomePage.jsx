import React, { useState, useEffect } from 'react';
import { ArrowRight, Sparkles, TrendingUp, Layers, Award, ChevronRight } from 'lucide-react';
import ProductCard from '../components/ProductCard';
import { fetchProducts } from '../services/api';

export default function HomePage({ setActivePage, setSelectedCategory }) {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts()
      .then((data) => {
        setFeaturedProducts(data.slice(0, 4));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const categories = [
    { name: 'Electronics', count: '4 Items', icon: '🎧', bg: 'bg-blue-50 text-blue-700' },
    { name: 'Apparel', count: '2 Items', icon: '🧥', bg: 'bg-emerald-50 text-emerald-700' },
    { name: 'Home & Living', count: '3 Items', icon: '☕', bg: 'bg-amber-50 text-amber-700' },
    { name: 'Accessories', count: '2 Items', icon: '💼', bg: 'bg-purple-50 text-purple-700' },
  ];

  return (
    <div className="space-y-16 animate-fade-in">
      
      {/* Hero Section */}
      <section className="relative rounded-3xl bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white p-8 md:p-14 overflow-hidden shadow-2xl border border-slate-800">
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 rounded-full bg-brand-500/20 blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-1/3 -mb-20 w-80 h-80 rounded-full bg-purple-500/15 blur-3xl pointer-events-none"></div>

        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/10 text-xs font-semibold text-brand-300 mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Next-Gen Local Microservices E-Commerce</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.1] mb-6">
            Engineered for speed, designed for <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-300 to-indigo-200">realism.</span>
          </h1>

          <p className="text-base sm:text-lg text-slate-300 mb-8 leading-relaxed font-normal">
            Browse high-fidelity seeded products, test instant checkouts, and simulate production incidents on a live 7-service architecture with 30+ telemetry signals.
          </p>

          <div className="flex flex-wrap items-center gap-4">
            <button
              onClick={() => setActivePage('products')}
              className="px-6 py-3.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-bold text-sm shadow-lg shadow-brand-600/30 hover:scale-105 transition-all flex items-center gap-2"
            >
              <span>Explore All Products</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={() => setActivePage('status')}
              className="px-6 py-3.5 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 text-white font-semibold text-sm backdrop-blur-sm transition-colors flex items-center gap-2"
            >
              <span>System Topology</span>
            </button>
          </div>
        </div>
      </section>

      {/* Featured Categories */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Browse by Category</h2>
            <p className="text-xs text-slate-500">Discover handpicked items across all microservices catalog routes</p>
          </div>
          <button
            onClick={() => setActivePage('products')}
            className="text-xs font-bold text-brand-600 hover:text-brand-700 flex items-center gap-1"
          >
            <span>View all</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {categories.map((cat) => (
            <button
              key={cat.name}
              onClick={() => {
                setSelectedCategory(cat.name);
                setActivePage('products');
              }}
              className="p-5 rounded-2xl bg-white border border-slate-200/80 hover:border-brand-500 hover:shadow-md transition-all text-left group"
            >
              <div className="text-3xl mb-3 group-hover:scale-110 transition-transform duration-300">{cat.icon}</div>
              <h3 className="font-bold text-slate-900 text-sm group-hover:text-brand-600 transition-colors">{cat.name}</h3>
              <p className="text-xs text-slate-400 mt-0.5">{cat.count}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Featured Products */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-brand-600" />
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Trending & Bestsellers</h2>
          </div>
          <button
            onClick={() => setActivePage('products')}
            className="text-xs font-bold text-brand-600 hover:text-brand-700 flex items-center gap-1"
          >
            <span>Browse Full Catalog ({featuredProducts.length}+)</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map(n => (
              <div key={n} className="bg-white rounded-2xl p-4 border border-slate-200 h-80 animate-pulse"></div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {featuredProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </section>

      {/* Promotional Callout */}
      <section className="bg-slate-100 rounded-3xl p-8 border border-slate-200 flex flex-col md:flex-row items-center justify-between gap-6">
        <div>
          <div className="text-xs font-bold text-brand-600 uppercase tracking-wider mb-1">AIOps Hackathon Promo</div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Save 20% on any simulated order today</h3>
          <p className="text-xs text-slate-600 max-w-xl">
            Use promo code <code className="px-2 py-0.5 rounded bg-white font-mono text-brand-600 font-bold border border-slate-200">HACKATHON20</code> during checkout to test price calculation workflows and simulated inventory reservation.
          </p>
        </div>
        <button
          onClick={() => setActivePage('products')}
          className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold whitespace-nowrap shadow transition-colors"
        >
          Shop Now
        </button>
      </section>

    </div>
  );
}
