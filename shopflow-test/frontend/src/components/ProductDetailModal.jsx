import React, { useState } from 'react';
import { X, Star, ShoppingBag, ShieldCheck, Truck, RotateCcw, Check } from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function ProductDetailModal() {
  const { selectedProduct, setSelectedProduct, addToCart } = useApp();
  const [quantity, setQuantity] = useState(1);

  if (!selectedProduct) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div
        className="bg-white rounded-3xl shadow-2xl max-w-2xl w-full overflow-hidden border border-slate-200 relative flex flex-col md:flex-row max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={() => setSelectedProduct(null)}
          className="absolute top-4 right-4 z-10 p-2 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Product Image */}
        <div className="w-full md:w-1/2 bg-slate-100 relative min-h-[260px] md:min-h-full">
          <img
            src={selectedProduct.image_url}
            alt={selectedProduct.title}
            className="w-full h-full object-cover"
          />
          {selectedProduct.badge && (
            <span className="absolute top-4 left-4 px-3 py-1 rounded-full text-xs font-bold bg-slate-900 text-white shadow-sm">
              {selectedProduct.badge}
            </span>
          )}
        </div>

        {/* Details Content */}
        <div className="w-full md:w-1/2 p-6 overflow-y-auto flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span className="font-bold text-brand-600 uppercase tracking-wider">{selectedProduct.category}</span>
              <div className="flex items-center gap-1 text-amber-500 font-semibold">
                <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                <span>{selectedProduct.rating}</span>
                <span className="text-slate-400 font-normal">({selectedProduct.review_count} reviews)</span>
              </div>
            </div>

            <h2 className="text-xl font-bold text-slate-900 mb-2 leading-tight">
              {selectedProduct.title}
            </h2>

            <div className="text-2xl font-extrabold text-slate-900 mb-4">
              ${selectedProduct.price.toFixed(2)}
            </div>

            <p className="text-sm text-slate-600 leading-relaxed mb-6">
              {selectedProduct.description}
            </p>

            {/* Specifications */}
            {selectedProduct.specs && Object.keys(selectedProduct.specs).length > 0 && (
              <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100 mb-6">
                <div className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">Specifications</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(selectedProduct.specs).map(([key, val]) => (
                    <div key={key}>
                      <span className="text-slate-400">{key}: </span>
                      <span className="font-semibold text-slate-800">{String(val)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Stock status */}
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-600 mb-6">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>In Stock ({selectedProduct.stock} units available)</span>
            </div>
          </div>

          {/* Action Row */}
          <div className="pt-4 border-t border-slate-100">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-xs font-semibold text-slate-600">Quantity:</span>
              <div className="flex items-center border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="px-3 py-1.5 hover:bg-slate-100 text-slate-600 font-bold"
                >
                  -
                </button>
                <span className="px-3 py-1.5 text-xs font-bold text-slate-800">{quantity}</span>
                <button
                  onClick={() => setQuantity(Math.min(selectedProduct.stock, quantity + 1))}
                  className="px-3 py-1.5 hover:bg-slate-100 text-slate-600 font-bold"
                >
                  +
                </button>
              </div>
            </div>

            <button
              onClick={() => {
                addToCart(selectedProduct, quantity);
                setSelectedProduct(null);
              }}
              className="w-full py-3 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-bold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2"
            >
              <ShoppingBag className="w-4 h-4" />
              <span>Add to Cart — ${(selectedProduct.price * quantity).toFixed(2)}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
