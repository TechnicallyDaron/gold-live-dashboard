import { authGateEnabled, supabase } from './supabase.js'

const BASE_URL = import.meta.env.VITE_API_URL || ''

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

// Pulled fresh on every request rather than cached from auth state, so a
// token that expired between renders is refreshed (getSession refreshes
// internally when needed) instead of sending a stale bearer that 401s.
// Stays absent in file-mode (no auth gate configured), matching prior
// behavior with no per-call duplication at the watchlist/position/journal
// call sites below.
async function authHeaders() {
  if (!authGateEnabled) return {}
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request(path, options = {}) {
  const headers = { ...(await authHeaders()), ...(options.headers || {}) }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // ignore
    }
    throw new ApiError(detail, res.status)
  }
  return res.json()
}

function postJSON(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

function del(path) {
  return request(path, { method: 'DELETE' })
}

export const api = {
  health: () => request('/api/health'),
  watchlist: () => request('/api/watchlist'),
  positions: () => request('/api/positions'),
  quote: (asset) => request(`/api/quote/${encodeURIComponent(asset)}`),
  bias: (asset) => request(`/api/bias/${encodeURIComponent(asset)}`),
  backtest: (asset, strategy) =>
    request(`/api/backtest/${encodeURIComponent(asset)}?strategy=${strategy}`),
  macro: () => request('/api/macro'),
  news: (asset) => request(`/api/news/${encodeURIComponent(asset)}`),
  tape: () => request('/api/tape'),
  history: (asset, days) => request(`/api/history/${encodeURIComponent(asset)}?days=${days}`),
  ask: (asset, question) => postJSON('/api/ask', { asset, question }),
  sentiment: (asset) => request(`/api/sentiment/${encodeURIComponent(asset)}`),
  macroRadar: () => request('/api/macro-radar'),
  notifications: (since = 0) => request(`/api/notifications?since=${since}`),
  pushSubscribe: (subscription) => postJSON('/api/push/subscribe', subscription),
  shield: () => request('/api/shield'),
  addPosition: (body) => postJSON('/api/positions', body),
  addWatchlist: (body) => postJSON('/api/watchlist', body),
  removeWatchlist: (name) => del(`/api/watchlist/${encodeURIComponent(name)}`),
  closePosition: (id, body) => postJSON(`/api/positions/${encodeURIComponent(id)}/close`, body),
  journal: () => request('/api/journal'),
  candidates: () => request('/api/candidates'),
  screener: () => request('/api/screener'),
  strategyLab: (asset) => request(`/api/strategy-lab/${encodeURIComponent(asset)}`),
  optimizedEdge: (asset) => request(`/api/optimized-edge/${encodeURIComponent(asset)}`),
  me: () => request('/api/me'),
}

export { ApiError }
