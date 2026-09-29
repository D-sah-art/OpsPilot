import React, { useState, useEffect } from 'react';
import { Package, Clock, CheckCircle2, Truck, ChevronRight, ShoppingBag } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { fetchOrders } from '../services/api';

export default function OrdersPage({ setActivePage }) {
  const { currentUser } = useApp();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchOrders(currentUser.id)
      .then((data) => {
        setOrders(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [currentUser.id]);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'DELIVERED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            <span>Delivered</span>
          </span>
        );
      case 'SHIPPED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
            <Truck className="w-3.5 h-3.5 text-blue-500" />
            <span>In Transit</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-50 text-purple-700 border border-purple-200">
            <Clock className="w-3.5 h-3.5 text-purple-500" />
            <span>Confirmed</span>
          </span>
        );
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      
      {/* Title */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Order History</h1>
          <p className="text-xs text-slate-500 mt-1">
            Tracking orders for account: <strong className="text-slate-800">{currentUser.email}</strong>
          </p>
        </div>
        <button
          onClick={() => setActivePage('products')}
          className="px-4 py-2 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 transition-colors"
        >
          Shop More
        </button>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map((n) => (
            <div key={n} className="bg-white rounded-2xl p-6 border border-slate-200 h-40 animate-pulse"></div>
          ))}
        </div>
      ) : orders.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center text-slate-400">
          <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4 text-slate-400">
            <Package className="w-8 h-8" />
          </div>
          <h3 className="text-base font-bold text-slate-800 mb-1">No orders found</h3>
          <p className="text-xs text-slate-400 mb-6">You haven&apos;t placed any orders with this account yet.</p>
          <button
            onClick={() => setActivePage('products')}
            className="px-5 py-2.5 rounded-xl bg-brand-600 text-white text-xs font-bold hover:bg-brand-700 transition-colors"
          >
            Start Shopping
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {orders.map((order) => (
            <div
              key={order.id}
              className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden"
            >
              {/* Card Header */}
              <div className="p-5 bg-slate-50/80 border-b border-slate-100 flex flex-wrap items-center justify-between gap-4 text-xs">
                <div className="flex flex-wrap items-center gap-6">
                  <div>
                    <span className="text-slate-400 block text-[11px] font-medium">Order Placed</span>
                    <span className="font-semibold text-slate-800">
                      {new Date(order.created_at).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      })}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px] font-medium">Total Amount</span>
                    <span className="font-bold text-slate-900">${order.total.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px] font-medium">Order Number</span>
                    <span className="font-mono text-slate-700 font-semibold">{order.id}</span>
                  </div>
                </div>

                <div>
                  {getStatusBadge(order.status)}
                </div>
              </div>

              {/* Items List */}
              <div className="p-5 space-y-3">
                {order.items?.map((item) => (
                  <div key={item.id || item.product_id} className="flex items-center justify-between text-xs py-2 border-b border-slate-100 last:border-0">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-slate-500 text-xs">
                        {item.quantity}x
                      </div>
                      <div>
                        <div className="font-bold text-slate-900">{item.product_title}</div>
                        <div className="text-[11px] text-slate-400">Unit Price: ${item.price?.toFixed(2)}</div>
                      </div>
                    </div>

                    <div className="font-bold text-slate-900 text-xs">
                      ${(item.price * item.quantity).toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>

              {/* Card Footer */}
              <div className="px-5 py-3 bg-slate-50/40 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>Payment: {order.payment_method}</span>
                <span>Shipping Address: {order.shipping_address?.city}, {order.shipping_address?.state}</span>
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}
