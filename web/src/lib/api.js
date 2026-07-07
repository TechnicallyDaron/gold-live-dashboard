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
  ask: (asset, question) =>
    request('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ asset, question }),
    }),
  sentiment: (asset) => request(`/api/sentiment/${encodeURIComponent(asset)}`),
}

export { ApiError }
