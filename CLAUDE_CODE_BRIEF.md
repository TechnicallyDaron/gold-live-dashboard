# N-CORE MOBILE PWA — BUILD BRIEF (for Claude Code)

## Mission
Robinhood-feel mobile app for "Nyarko's Trade Manager". The backend already
exists (FastAPI at `api/main.py`, engine in `quant_core.py` + `signal_engine.py`)
— DO NOT modify their math or response shapes. Build the frontend only.

## Stack
- Vite + React (JS is fine), react-router-dom for CLIENT-SIDE routing
  (tab taps must be instant — no page reloads, ever)
- PWA: manifest.json (display: "standalone", theme #0B0E14) + service worker
  (vite-plugin-pwa), viewport meta MUST include `viewport-fit=cover`,
  safe-area handled with env(safe-area-inset-*)
- New folder `web/` in this repo; deploys as its own Railway service
  (root dir `web/`, build `npm run build`, serve `dist/` — or Vercel)

## API contract (base URL via VITE_API_URL env)
- GET /api/health → {status, time_utc, watchlist_assets, telegram_configured}
- GET /api/watchlist → {name: {ticker, name, unit}}
- GET /api/positions → {id: {asset, strike, type, expiration, premium_stop, time_stop, ...}}
- GET /api/quote/{asset} → {asset, ticker, unit, price, change, pct}   (502 = feed down)
- GET /api/bias/{asset} → {state, headline, color, price, z, baseline, macro, trend,
    upper, lower, arm_level, invalidation, target, dist_to_arm_pct,
    dist_to_target_pct, direction, asset, ticker, unit}
- GET /api/backtest/{asset}?strategy=meanrev|breakout|rsi →
    {asset, strategy, strategy_meta, viability{verdict,class,profit_factor,expectancy_pct},
     stats{strategy_return, buy_hold_return, max_drawdown, all/long/short{n,win_rate,avg_win,avg_loss}},
     trades[last 40]}
- GET /api/macro → [{time_et, currency, event, forecast, previous, upcoming}]
- GET /api/news/{asset} → [{title, link, published}]
`{asset}` accepts watchlist display names (case-insensitive) or raw tickers.

## Screens (v1 = exactly three; bottom tab bar, 3 tabs)
1. **Briefing** — watchlist cards (name, price, %, bias state chip; tap → Bias),
   next upcoming macro event banner, health dot from /api/health
2. **Bias** — asset switcher; verdict banner colored by `color`
   (green/red/orange/gray); metrics 2-up grid: Spot, Z, 20EMA, Trend, Bands;
   Action levels: Arm / Invalidation / Target; backtest viability strip (3 strategies)
3. **Positions** — cards from /api/positions showing stop, time stop, invalidation

## Design tokens (match the terminal)
ink #0B0E14 · panel #151B29→#10141F gradient · bullion #E8B54A · volt #00E5FF ·
long #2FBF71 · short #E4574C · watch #E2A93B · text #E8ECF3 · muted #97A1B3 ·
font: Space Grotesk (Google Fonts) · radius 12-14px · tabular-nums for prices

## Non-negotiables
- Tab bar: fixed bottom, 3 tabs, min 52px targets,
  padding-bottom: max(env(safe-area-inset-bottom), 12px), active tab bullion
- Loading = skeleton shimmer on cards, never a blocking spinner page
- Feed failures render an explicit "FEED DOWN" card state (red edge) — never $0.00
- Poll quotes every 60s with visibilitychange pause; no websockets in v1
