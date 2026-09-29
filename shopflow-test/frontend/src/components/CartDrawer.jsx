import React, { useState } from 'react';
import { X, Trash2, ShoppingBag, ArrowRight, Tag, ShieldCheck } from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function CartDrawer({ setActivePage }) {
  const { isCartOpen, setIsCartOpen, cart, updateQuantity, removeFromCart, cartSubtotal, cartCount } = useApp();
  const [coupon, setCoupon] = useState('');
  const [appliedCoupon, setAppliedCoupon] = useState(null);

  if (!isCartOpen) return null;

  const handleApplyCoupon = (e) => {
    e.preventDefault();
    if (coupon.trim().toUpperCase() === 'HACKATHON20') {
      setAppliedCoupon('HACKATHON20');
    } else {
      alert('Invalid coupon code. Try HACKATHON20 for 20% off!');
    }
  };

  const discount = appliedCoupon === 'HACKATHON20' ? cartSubtotal * 0.20 : 0;
  const subtotalAfterDiscount = cartSubtotal - discount;
  const tax = subtotalAfterDiscount * 0.08;
  const shipping = subtotalAfterDiscount > 50.0 || cartSubtotal === 0 ? 0.00 : 9.99;
  const finalTotal = subtotalAfterDiscount + tax + shipping;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden animate-fade-in">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity"
        onClick={() => setIsCartOpen(false)}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white shadow-2xl flex flex-col justify-between">
          
          {/* Header */}
          <div className="p-5 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-brand-600" />
              <h2 className="text-lg font-bold text-slate-900">Your Cart</h2>
              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-600">
                {cartCount} {cartCount === 1 ? 'item' : 'items'}
              </span>
            </div>
            <button
              onClick={() => setIsCartOpen(false)}
              className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Cart Items List */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {cart.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
                <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4 text-slate-300">
                  <ShoppingBag className="w-8 h-8" />
                </div>
                <p className="font-semibold text-slate-700 text-base mb-1">Your cart is empty</p>
                <p className="text-xs text-slate-400 mb-6">Explore our curated catalog and add items.</p>
                <button
                  onClick={() => {
                    setIsCartOpen(false);
                    setActivePage('products');
                  }}
                  className="px-4 py-2 rounded-xl bg-brand-600 text-white text-xs font-semibold hover:bg-brand-700 transition-colors"
                >
                  Browse Products
                </button>
              </div>
            ) : (
              cart.map((item) => (
                <div
                  key={item.product_id}
                  className="flex items-center gap-4 p-3 rounded-2xl bg-slate-50 border border-slate-200/60"
                >
                  <img
                    src={item.image_url}
                    alt={item.title}
                    className="w-16 h-16 rounded-xl object-cover bg-white border border-slate-200"
                  />
                  <div className="flex-1 min-w-0">
                    <h4 className="text-xs font-semibold text-slate-900 truncate mb-1">
                      {item.title}
                    </h4>
                    <div className="text-xs font-bold text-slate-900">
                      ${item.price.toFixed(2)}
                    </div>
                    <div className="flex items-center gap-3 mt-2">
                      <div className="flex items-center border border-slate-300 rounded-lg bg-white overflow-hidden text-xs">
                        <button
                          onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                          className="px-2 py-0.5 hover:bg-slate-100 text-slate-600 font-bold"
                        >
                          -
                        </button>
                        <span className="px-2 py-0.5 font-semibold text-slate-800">{item.quantity}</span>
                        <button
                          onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                          className="px-2 py-0.5 hover:bg-slate-100 text-slate-600 font-bold"
                        >
                          +
                        </button>
                      </div>
                      <button
                        onClick={() => removeFromCart(item.product_id)}
                        className="text-slate-400 hover:text-rose-500 p-1 transition-colors"
                        title="Remove item"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="text-right font-bold text-xs text-slate-900">
                    ${(item.price * item.quantity).toFixed(2)}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer with Calculations */}
          {cart.length > 0 && (
            <div className="p-5 border-t border-slate-200 bg-slate-50/50 space-y-4">
              {/* Coupon Form */}
              <form onSubmit={handleApplyCoupon} className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type="text"
                    placeholder="Coupon code (e.g. HACKATHON20)"
                    value={coupon}
                    onChange={(e) => setCoupon(e.target.value)}
                    className="w-full pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs focus:ring-1 focus:ring-brand-500 uppercase font-mono"
                  />
                  <Tag className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                </div>
                <button
                  type="submit"
                  className="px-3 py-1.5 rounded-xl bg-slate-800 text-white text-xs font-semibold hover:bg-slate-900 transition-colors"
                >
                  Apply
                </button>
              </form>

              {appliedCoupon && (
                <div className="text-xs text-emerald-600 font-medium flex items-center justify-between">
                  <span>Coupon &lsquo;{appliedCoupon}&rsquo; applied (-20%)</span>
                  <button onClick={() => setAppliedCoupon(null)} className="underline text-slate-400 hover:text-slate-600">Remove</button>
                </div>
              )}

              {/* Cost breakdown */}
              <div className="space-y-1.5 text-xs text-slate-600 border-t border-slate-200/60 pt-3">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span className="font-semibold text-slate-800">${cartSubtotal.toFixed(2)}</span>
                </div>
                {discount > 0 && (
                  <div className="flex justify-between text-emerald-600">
                    <span>Discount</span>
                    <span>-${discount.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Est. Tax (8%)</span>
                  <span>${tax.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Shipping</span>
                  <span>{shipping === 0 ? <strong className="text-emerald-600 font-semibold">FREE</strong> : `$${shipping.toFixed(2)}`}</span>
                </div>
                <div className="flex justify-between text-sm font-bold text-slate-900 pt-2 border-t border-slate-200">
                  <span>Total</span>
                  <span className="text-brand-600">${finalTotal.toFixed(2)}</span>
                </div>
              </div>

              {/* Checkout Action */}
              <button
                onClick={() => {
                  setIsCartOpen(false);
                  setActivePage('checkout');
                }}
                className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-bold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2"
              >
                <span>Proceed to Checkout</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="flex items-center justify-center gap-1 text-[11px] text-slate-400 text-center">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                <span>Simulated Secure Production Checkout</span>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
