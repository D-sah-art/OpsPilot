import React from 'react';
import { AlertTriangle, RefreshCw, Shield, Clock } from 'lucide-react';

export default function DegradedNotice({ onRetry, isRetrying, message }) {
  return (
    <div className="bg-amber-50/90 border border-amber-200/80 rounded-2xl p-5 mb-6 text-amber-900 shadow-sm animate-fade-in">
      <div className="flex items-start gap-3.5">
        <div className="p-2.5 rounded-xl bg-amber-100 text-amber-700 flex-shrink-0">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-bold text-amber-900 mb-1">
            {message || "Checkout temporarily unavailable"}
          </h4>
          <p className="text-xs text-amber-800 leading-relaxed mb-3">
            Our systems are currently experiencing upstream database latency. Your items and cart contents remain completely safe and reserved in your session.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            {onRetry && (
              <button
                onClick={onRetry}
                disabled={isRetrying}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold shadow-sm transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
                <span>{isRetrying ? 'Retrying...' : 'Retry Checkout'}</span>
              </button>
            )}
            <div className="flex items-center gap-1.5 text-[11px] text-amber-700 font-medium">
              <Shield className="w-3.5 h-3.5" />
              <span>Cart Session Preserved</span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-amber-700 font-medium">
              <Clock className="w-3.5 h-3.5" />
              <span>Auto-recovery in progress</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
