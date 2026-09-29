import React, { useState } from 'react';
import { ShieldCheck, Lock, CreditCard, CheckCircle2, ArrowRight, ShoppingBag, Truck, AlertCircle } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { submitCheckout } from '../services/api';
import DegradedNotice from '../components/DegradedNotice';

export default function CheckoutPage({ setActivePage }) {
  const { cart, cartSubtotal, clearCart, currentUser, showToast } = useApp();

  const [shippingAddress, setShippingAddress] = useState({
    street: currentUser.address?.street || '742 Evergreen Terrace',
    city: currentUser.address?.city || 'Springfield',
    state: currentUser.address?.state || 'OR',
    zip: currentUser.address?.zip || '97477',
    country: currentUser.address?.country || 'USA'
  });

  const [paymentMethod, setPaymentMethod] = useState('Credit Card (Simulated)');
  const [couponCode, setCouponCode] = useState('');
  const [discountApplied, setDiscountApplied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [degradedError, setDegradedError] = useState(null);
  const [completedOrder, setCompletedOrder] = useState(null);

  const discount = discountApplied ? cartSubtotal * 0.20 : 0;
  const subtotalAfterDiscount = cartSubtotal - discount;
  const tax = subtotalAfterDiscount * 0.08;
  const shipping = subtotalAfterDiscount > 50.0 || cartSubtotal === 0 ? 0.00 : 9.99;
  const finalTotal = subtotalAfterDiscount + tax + shipping;

  const handleApplyCoupon = (e) => {
    e.preventDefault();
    if (couponCode.trim().toUpperCase() === 'HACKATHON20') {
      setDiscountApplied(true);
      showToast('Coupon HACKATHON20 applied (20% off)!', 'success');
    } else {
      showToast('Invalid promo code. Use HACKATHON20', 'error');
    }
  };

  const handlePlaceOrder = async (e) => {
    if (e) e.preventDefault();
    if (cart.length === 0) {
      showToast('Your cart is empty', 'error');
      return;
    }

    setLoading(true);
    setDegradedError(null);

    const payload = {
      user_id: currentUser.id,
      user_email: currentUser.email,
      items: cart.map(i => ({
        product_id: i.product_id,
        product_title: i.title,
        price: i.price,
        quantity: i.quantity,
        image_url: i.image_url
      })),
      shipping_address: shippingAddress,
      payment_method: paymentMethod,
      coupon_code: discountApplied ? 'HACKATHON20' : null
    };

    try {
      const response = await submitCheckout(payload);
      setCompletedOrder(response.order);
      clearCart();
      showToast('Order successfully placed!', 'success');
    } catch (err) {
      // Graceful degradation handling
      console.warn('Checkout failure intercepted:', err);
      setDegradedError(err.detail || "Checkout temporarily unavailable. Your cart is safe. Please try again in a moment.");
    } finally {
      setLoading(false);
    }
  };

  // SUCCESS CONFIRMATION VIEW
  if (completedOrder) {
    return (
      <div className="max-w-2xl mx-auto py-8 animate-fade-in text-center">
        <div className="bg-white rounded-3xl p-8 md:p-12 border border-slate-200/80 shadow-xl space-y-6">
          <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-inner">
            <CheckCircle2 className="w-10 h-10" />
          </div>

          <div>
            <span className="text-xs font-bold text-emerald-600 uppercase tracking-wider">Order Confirmed</span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-1">Thank you for your order!</h1>
            <p className="text-xs text-slate-500 mt-2 font-mono">
              Confirmation ID: <strong className="text-slate-800">{completedOrder.id}</strong>
            </p>
          </div>

          <div className="bg-slate-50 rounded-2xl p-5 border border-slate-100 text-left space-y-3">
            <div className="flex items-center justify-between text-xs pb-3 border-b border-slate-200">
              <span className="text-slate-500">Recipient</span>
              <span className="font-semibold text-slate-800">{completedOrder.user_email}</span>
            </div>
            <div className="flex items-center justify-between text-xs pb-3 border-b border-slate-200">
              <span className="text-slate-500">Shipping To</span>
              <span className="font-semibold text-slate-800">{shippingAddress.street}, {shippingAddress.city}, {shippingAddress.state}</span>
            </div>
            <div className="flex items-center justify-between text-xs pb-3 border-b border-slate-200">
              <span className="text-slate-500">Payment</span>
              <span className="font-semibold text-slate-800">{completedOrder.payment_method}</span>
            </div>
            <div className="flex items-center justify-between text-sm font-bold pt-1">
              <span>Total Paid</span>
              <span className="text-brand-600">${completedOrder.total?.toFixed(2)}</span>
            </div>
          </div>

          {/* Items Preview */}
          <div className="space-y-2 text-left">
            <div className="text-xs font-bold text-slate-900 uppercase tracking-wider">Items in Order</div>
            {completedOrder.items?.map((item) => (
              <div key={item.id || item.product_id} className="flex justify-between items-center text-xs py-1.5 border-b border-slate-100">
                <span className="text-slate-700 font-medium truncate max-w-xs">
                  {item.quantity}x {item.product_title}
                </span>
                <span className="font-bold text-slate-900">${(item.price * item.quantity).toFixed(2)}</span>
              </div>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <button
              onClick={() => setActivePage('orders')}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow transition-colors"
            >
              View Order History
            </button>
            <button
              onClick={() => setActivePage('products')}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-colors"
            >
              Continue Shopping
            </button>
          </div>
        </div>
      </div>
    );
  }

  // EMPTY CART CHECK
  if (cart.length === 0) {
    return (
      <div className="max-w-md mx-auto py-16 text-center animate-fade-in">
        <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm space-y-4">
          <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
            <ShoppingBag className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">Your Cart is Empty</h2>
          <p className="text-xs text-slate-500">Please add items to your cart before proceeding to checkout.</p>
          <button
            onClick={() => setActivePage('products')}
            className="px-5 py-2.5 rounded-xl bg-brand-600 text-white text-xs font-bold hover:bg-brand-700 transition-colors shadow"
          >
            Explore Catalog
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
      
      {/* Title */}
      <div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Checkout</h1>
        <p className="text-xs text-slate-500 mt-1">Review your order and complete simulated transaction</p>
      </div>

      {/* Graceful Degradation Notice during active incident */}
      {degradedError && (
        <DegradedNotice
          message={degradedError}
          onRetry={handlePlaceOrder}
          isRetrying={loading}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Form Column (Shipping & Payment) */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Shipping Address */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900 pb-3 border-b border-slate-100">
              <Truck className="w-4 h-4 text-brand-600" />
              <span>1. Shipping Information</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="sm:col-span-2">
                <label className="block font-semibold text-slate-700 mb-1">Street Address</label>
                <input
                  type="text"
                  value={shippingAddress.street}
                  onChange={(e) => setShippingAddress({ ...shippingAddress, street: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">City</label>
                <input
                  type="text"
                  value={shippingAddress.city}
                  onChange={(e) => setShippingAddress({ ...shippingAddress, city: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">State / Province</label>
                <input
                  type="text"
                  value={shippingAddress.state}
                  onChange={(e) => setShippingAddress({ ...shippingAddress, state: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">ZIP / Postal Code</label>
                <input
                  type="text"
                  value={shippingAddress.zip}
                  onChange={(e) => setShippingAddress({ ...shippingAddress, zip: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Country</label>
                <input
                  type="text"
                  value={shippingAddress.country}
                  onChange={(e) => setShippingAddress({ ...shippingAddress, country: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-1 focus:ring-brand-500"
                />
              </div>
            </div>
          </div>

          {/* Payment Method */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900 pb-3 border-b border-slate-100">
              <CreditCard className="w-4 h-4 text-brand-600" />
              <span>2. Simulated Payment Method</span>
            </div>

            <div className="space-y-2.5">
              {[
                { id: 'Credit Card (Simulated)', label: 'Credit Card (Simulated Auth)', detail: 'Visa ending in 4242' },
                { id: 'Apple Pay (Simulated)', label: 'Apple Pay (Mock Token)', detail: 'One-click bio simulated token' },
                { id: 'Corporate Invoice (Simulated)', label: 'Net 30 Invoice', detail: 'Authorized demo invoice' }
              ].map((p) => (
                <label
                  key={p.id}
                  className={`flex items-center justify-between p-3.5 rounded-xl border cursor-pointer transition-colors ${
                    paymentMethod === p.id
                      ? 'border-brand-600 bg-brand-50/50'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="radio"
                      name="payment"
                      checked={paymentMethod === p.id}
                      onChange={() => setPaymentMethod(p.id)}
                      className="text-brand-600 focus:ring-brand-500"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-900">{p.label}</div>
                      <div className="text-[11px] text-slate-500">{p.detail}</div>
                    </div>
                  </div>
                  <Lock className="w-3.5 h-3.5 text-slate-400" />
                </label>
              ))}
            </div>
          </div>

        </div>

        {/* Right Order Summary Column */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-5">
            <h3 className="text-sm font-bold text-slate-900 pb-3 border-b border-slate-100">
              Order Summary ({cart.length} items)
            </h3>

            {/* Items summary */}
            <div className="space-y-3 max-h-52 overflow-y-auto pr-1">
              {cart.map((item) => (
                <div key={item.product_id} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <img src={item.image_url} alt="" className="w-8 h-8 rounded-lg object-cover border border-slate-100" />
                    <span className="truncate max-w-[160px] font-medium text-slate-700">
                      {item.quantity}x {item.title}
                    </span>
                  </div>
                  <span className="font-bold text-slate-900">${(item.price * item.quantity).toFixed(2)}</span>
                </div>
              ))}
            </div>

            {/* Promo Code Input */}
            <form onSubmit={handleApplyCoupon} className="flex gap-2 pt-2 border-t border-slate-100">
              <input
                type="text"
                placeholder="Promo Code (HACKATHON20)"
                value={couponCode}
                onChange={(e) => setCouponCode(e.target.value)}
                className="flex-1 px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-mono uppercase"
              />
              <button
                type="submit"
                className="px-3 py-1.5 rounded-xl bg-slate-800 text-white text-xs font-bold hover:bg-slate-900"
              >
                Apply
              </button>
            </form>

            {/* Total Math */}
            <div className="space-y-2 text-xs text-slate-600 pt-3 border-t border-slate-100">
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span className="font-semibold text-slate-900">${cartSubtotal.toFixed(2)}</span>
              </div>
              {discount > 0 && (
                <div className="flex justify-between text-emerald-600 font-medium">
                  <span>Discount (20%)</span>
                  <span>-${discount.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>Estimated Tax (8%)</span>
                <span>${tax.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Shipping</span>
                <span>{shipping === 0 ? <strong className="text-emerald-600">FREE</strong> : `$${shipping.toFixed(2)}`}</span>
              </div>
              <div className="flex justify-between text-base font-extrabold text-slate-900 pt-3 border-t border-slate-200">
                <span>Total Due</span>
                <span className="text-brand-600">${finalTotal.toFixed(2)}</span>
              </div>
            </div>

            {/* Submit Action */}
            <button
              onClick={handlePlaceOrder}
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-extrabold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <span>Processing Order...</span>
              ) : (
                <>
                  <span>Place Simulated Order — ${finalTotal.toFixed(2)}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-400">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              <span>Tested on local microservices testbed</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
