import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchHealthSummary, fetchChaosStatus } from '../services/api';

const AppContext = createContext();

export const DEMO_USERS = [
  {
    id: 'usr_alex_01',
    email: 'alex@shopflow.dev',
    full_name: 'Alex Rivera',
    role: 'customer',
    address: {
      street: '742 Evergreen Terrace',
      city: 'Springfield',
      state: 'OR',
      zip: '97477',
      country: 'USA'
    }
  },
  {
    id: 'usr_sarah_02',
    email: 'sarah@shopflow.dev',
    full_name: 'Sarah Chen',
    role: 'customer',
    address: {
      street: '456 Innovation Way',
      city: 'Seattle',
      state: 'WA',
      zip: '98101',
      country: 'USA'
    }
  }
];

export function AppProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem('shopflow_user');
    return saved ? JSON.parse(saved) : DEMO_USERS[0];
  });

  const [cart, setCart] = useState(() => {
    const saved = localStorage.getItem('shopflow_cart');
    return saved ? JSON.parse(saved) : [
      {
        product_id: 'prod_01',
        title: 'ProFlow Noise-Canceling Headphones',
        price: 299.99,
        quantity: 1,
        image_url: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80'
      }
    ];
  });

  const [isCartOpen, setIsCartOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [toast, setToast] = useState(null);
  const [systemHealth, setSystemHealth] = useState({ status: 'Operational', active_alerts_total: 0 });
  const [chaosState, setChaosState] = useState({ state: 'IDLE', active_scenario: null });

  // Save cart to local storage
  useEffect(() => {
    localStorage.setItem('shopflow_cart', JSON.stringify(cart));
  }, [cart]);

  // Save user to local storage
  useEffect(() => {
    localStorage.setItem('shopflow_user', JSON.stringify(currentUser));
  }, [currentUser]);

  // Toast timeout
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Background health polling
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const [health, chaos] = await Promise.all([
          fetchHealthSummary().catch(() => ({ status: 'Unknown', active_alerts_total: 0 })),
          fetchChaosStatus().catch(() => ({ state: 'IDLE', active_scenario: null }))
        ]);
        setSystemHealth(health);
        setChaosState(chaos);
      } catch (e) {
        // silent
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 3000);
    return () => clearInterval(interval);
  }, []);

  const showToast = (message, type = 'info') => {
    setToast({ message, type, id: Date.now() });
  };

  const addToCart = (product, quantity = 1) => {
    setCart(prev => {
      const existing = prev.find(item => item.product_id === product.id);
      if (existing) {
        return prev.map(item =>
          item.product_id === product.id
            ? { ...item, quantity: item.quantity + quantity }
            : item
        );
      }
      return [
        ...prev,
        {
          product_id: product.id,
          title: product.title,
          price: product.price,
          quantity: quantity,
          image_url: product.image_url
        }
      ];
    });
    showToast(`Added ${quantity}x "${product.title}" to cart`, 'success');
  };

  const updateQuantity = (productId, newQuantity) => {
    if (newQuantity <= 0) {
      removeFromCart(productId);
      return;
    }
    setCart(prev =>
      prev.map(item =>
        item.product_id === productId ? { ...item, quantity: newQuantity } : item
      )
    );
  };

  const removeFromCart = (productId) => {
    setCart(prev => prev.filter(item => item.product_id !== productId));
    showToast('Item removed from cart', 'info');
  };

  const clearCart = () => {
    setCart([]);
  };

  const switchUser = (user) => {
    setCurrentUser(user);
    showToast(`Switched user to ${user.full_name}`, 'info');
  };

  const cartCount = cart.reduce((total, item) => total + item.quantity, 0);
  const cartSubtotal = cart.reduce((total, item) => total + (item.price * item.quantity), 0);

  return (
    <AppContext.Provider
      value={{
        currentUser,
        switchUser,
        cart,
        addToCart,
        updateQuantity,
        removeFromCart,
        clearCart,
        cartCount,
        cartSubtotal,
        isCartOpen,
        setIsCartOpen,
        selectedProduct,
        setSelectedProduct,
        toast,
        showToast,
        systemHealth,
        chaosState
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within an AppProvider');
  return context;
}
