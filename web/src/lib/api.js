const BASE_URL = import.meta.env.VITE_API_URL || ''

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, options)
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
  strategyLab: (asset) => request(`/api/strategy-lab/${encodeURIComponent(asset)}`),
  me: (token) =>
    request('/api/me', token ? { headers: { Authorization: `Bearer ${token}` } } : undefined),
}

export { ApiError }
