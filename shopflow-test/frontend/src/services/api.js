const API_BASE = '';

export async function fetchProducts(category, query) {
  const params = new URLSearchParams();
  if (category && category !== 'all') params.append('category', category);
  if (query) params.append('q', query);
  const res = await fetch(`${API_BASE}/api/products?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch products');
  return res.json();
}

export async function fetchProductById(id) {
  const res = await fetch(`${API_BASE}/api/products/${id}`);
  if (!res.ok) throw new Error('Product not found');
  return res.json();
}

export async function fetchCategories() {
  const res = await fetch(`${API_BASE}/api/categories`);
  if (!res.ok) return ['Electronics', 'Apparel', 'Home & Living', 'Accessories'];
  return res.json();
}

export async function loginUser(email, password = 'demo123') {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  if (!res.ok) throw new Error('Invalid credentials');
  return res.json();
}

export async function fetchDemoUsers() {
  const res = await fetch(`${API_BASE}/api/auth/users`);
  if (!res.ok) return [];
  return res.json();
}

export async function submitCheckout(payload) {
  const res = await fetch(`${API_BASE}/api/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(data.detail || 'Checkout transaction failed');
    error.status = res.status;
    error.detail = data.detail;
    throw error;
  }
  return data;
}

export async function fetchOrders(userId) {
  const url = userId ? `${API_BASE}/api/orders?user_id=${userId}` : `${API_BASE}/api/orders`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch orders');
  return res.json();
}

export async function fetchTopology() {
  const res = await fetch(`${API_BASE}/api/topology`);
  if (!res.ok) throw new Error('Failed to fetch topology');
  return res.json();
}

export async function fetchHealthSummary() {
  const res = await fetch(`${API_BASE}/api/health-summary`);
  if (!res.ok) throw new Error('Failed to fetch health summary');
  return res.json();
}

export async function fetchSystemStatus() {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error('Failed to fetch system status');
  return res.json();
}

export async function fetchTelemetryMetrics() {
  const res = await fetch(`${API_BASE}/telemetry/metrics`);
  if (!res.ok) throw new Error('Failed to fetch telemetry metrics');
  return res.json();
}

export async function fetchTelemetryLogs(limit = 100, service = null) {
  const params = new URLSearchParams({ limit });
  if (service) params.append('service', service);
  const res = await fetch(`${API_BASE}/telemetry/logs?${params.toString()}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchTelemetryAlerts(limit = 100) {
  const res = await fetch(`${API_BASE}/telemetry/alerts?limit=${limit}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchChaosStatus() {
  const res = await fetch(`${API_BASE}/api/chaos/status`);
  if (!res.ok) throw new Error('Failed to fetch chaos status');
  return res.json();
}

export async function fetchChaosScenarios() {
  const res = await fetch(`${API_BASE}/api/chaos/scenarios`);
  if (!res.ok) return [];
  return res.json();
}

export async function triggerChaosScenario(scenarioId) {
  const res = await fetch(`${API_BASE}/api/chaos/scenario/${scenarioId}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to trigger scenario');
  return res.json();
}

export async function resetChaos() {
  const res = await fetch(`${API_BASE}/api/chaos/reset`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to reset chaos');
  return res.json();
}
