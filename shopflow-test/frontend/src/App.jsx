import React, { useState, useEffect } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import CartDrawer from './components/CartDrawer';
import ProductDetailModal from './components/ProductDetailModal';

// Pages
import HomePage from './pages/HomePage';
import ProductsPage from './pages/ProductsPage';
import CheckoutPage from './pages/CheckoutPage';
import OrdersPage from './pages/OrdersPage';
import StatusPage from './pages/StatusPage';
import ChaosLabPage from './pages/ChaosLabPage';

function ToastContainer() {
  const { toast } = useApp();
  if (!toast) return null;

  const bgColors = {
    success: 'bg-emerald-600 text-white',
    error: 'bg-rose-600 text-white',
    warning: 'bg-amber-600 text-white',
    info: 'bg-slate-900 text-white'
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-fade-in pointer-events-none">
      <div className={`px-4 py-3 rounded-2xl shadow-2xl text-xs font-bold flex items-center gap-2 ${bgColors[toast.type] || bgColors.info}`}>
        <span>{toast.message}</span>
      </div>
    </div>
  );
}

function MainContent() {
  const [activePage, setActivePage] = useState(() => {
    const path = window.location.pathname.replace('/', '') || window.location.hash.replace('#', '');
    if (['home', 'products', 'checkout', 'orders', 'status', 'chaos'].includes(path)) {
      return path;
    }
    return 'home';
  });

  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname.replace('/', '') || window.location.hash.replace('#', '');
      if (['home', 'products', 'checkout', 'orders', 'status', 'chaos'].includes(path)) {
        setActivePage(path);
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleNavigate = (page) => {
    setActivePage(page);
    window.history.pushState({}, '', `/${page === 'home' ? '' : page}`);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen flex flex-col justify-between">
      <Navbar
        activePage={activePage}
        setActivePage={handleNavigate}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
      />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        {activePage === 'home' && (
          <HomePage
            setActivePage={handleNavigate}
            setSelectedCategory={setSelectedCategory}
          />
        )}
        {activePage === 'products' && (
          <ProductsPage
            selectedCategory={selectedCategory}
            setSelectedCategory={setSelectedCategory}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
          />
        )}
        {activePage === 'checkout' && (
          <CheckoutPage setActivePage={handleNavigate} />
        )}
        {activePage === 'orders' && (
          <OrdersPage setActivePage={handleNavigate} />
        )}
        {activePage === 'status' && (
          <StatusPage setActivePage={handleNavigate} />
        )}
        {activePage === 'chaos' && (
          <ChaosLabPage setActivePage={handleNavigate} />
        )}
      </main>

      <Footer setActivePage={handleNavigate} />
      <CartDrawer setActivePage={handleNavigate} />
      <ProductDetailModal />
      <ToastContainer />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <MainContent />
    </AppProvider>
  );
}
