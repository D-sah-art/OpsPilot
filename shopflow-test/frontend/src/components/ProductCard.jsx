import React from 'react';
import { Star, ShoppingBag, Eye, Check } from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function ProductCard({ product }) {
  const { addToCart, setSelectedProduct } = useApp();

  return (
    <div className="group bg-white rounded-2xl border border-slate-200/80 hover:border-slate-300 hover:shadow-lg transition-all duration-300 flex flex-col overflow-hidden relative">
      {/* Badge */}
      {product.badge && (
        <span className="absolute top-3 left-3 z-10 px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-wide bg-slate-900/90 backdrop-blur-sm text-white shadow-sm">
          {product.badge}
        </span>
      )}

      {/* Image with hover actions */}
      <div className="relative aspect-square w-full bg-slate-100 overflow-hidden cursor-pointer" onClick={() => setSelectedProduct(product)}>
        <img
          src={product.image_url}
          alt={product.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-slate-900/10 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setSelectedProduct(product);
            }}
            className="p-2.5 rounded-full bg-white text-slate-800 shadow-md hover:bg-slate-50 transition-colors"
            title="Quick View"
          >
            <Eye className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Product Content */}
      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-medium text-brand-600 uppercase tracking-wider text-[10px]">{product.category}</span>
            <div className="flex items-center gap-1 text-amber-500 font-semibold">
              <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
              <span>{product.rating}</span>
              <span className="text-slate-400 font-normal">({product.review_count})</span>
            </div>
          </div>

          <h3
            onClick={() => setSelectedProduct(product)}
            className="font-semibold text-slate-900 text-sm leading-snug line-clamp-2 hover:text-brand-600 transition-colors cursor-pointer mb-2"
          >
            {product.title}
          </h3>
        </div>

        <div className="pt-3 border-t border-slate-100 flex items-center justify-between mt-auto">
          <div>
            <div className="text-[10px] text-slate-400 font-medium">Price</div>
            <div className="text-lg font-bold text-slate-900">${product.price.toFixed(2)}</div>
          </div>

          <button
            onClick={() => addToCart(product, 1)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold shadow-sm hover:shadow transition-all active:scale-95"
          >
            <ShoppingBag className="w-3.5 h-3.5" />
            <span>Add</span>
          </button>
        </div>
      </div>
    </div>
  );
}
