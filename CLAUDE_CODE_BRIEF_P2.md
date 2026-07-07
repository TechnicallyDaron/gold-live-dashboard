# N-CORE PWA — PHASE 2: FULL FEATURE PARITY

Extend the existing `web/` app. Same rules: engine/API response shapes are
law; do not modify Python except that api/main.py has ALREADY been updated
with two new endpoints (pull latest before starting).

## New API endpoints (already live in api/main.py)
- GET /api/tape → [{symbol, ticker, quote: {price, change, pct} | null}]  (7 instruments)
- GET /api/history/{asset}?days=500 → {asset, ticker, unit,
    rows: [{date, price, baseline, upper, lower, macro}]}  (chronological)

## Tab bar → FIVE tabs
Briefing · Bias · Chart · News · Positions
(52px+ targets still; five fit at ~19% width each on 393px)

## 1. Briefing upgrades
- TOP: infinite ticker tape from /api/tape — CSS marquee (duplicate content,
  translateX(-50%) keyframe loop, pause on touch), volt ⚡ separators,
  null quotes render as dimmed "—". Refresh data every 120s.
- Below watchlist cards: MACRO WEEK horizontal scroll track from /api/macro —
  cardlets (currency badge, ET time, event, F/P, amber "Upcoming" chip),
  upcoming first. Native overflow-x scroll = free thumb swipe.

## 2. Chart screen (new tab)
- Library: `lightweight-charts` (TradingView OSS — install it; NOT plotly)
- Line series: price (bullion #E8B54A, 2.5w), baseline (signal #37B7C3 dashed),
  macro (muted #97A1B3), upper (short #E4574C dotted), lower (long #2FBF71 dotted)
- Asset switcher pills (same component as Bias), range toggle 3M/1Y/5Y
  (days=90/365/1300), chart fills viewport minus header+tabbar,
  crosshair tooltip with date+values. Refresh every 60s, pause when hidden.

## 3. News screen (new tab)
- Cards from /api/news/{asset}: title (opens link in new tab), published time,
  asset switcher pills. Same card anatomy/tokens as Briefing.
- NO AI sentiment calls in this phase (operator has not funded AI credits);
  leave a disabled "AI Macro Read — Phase 4b" pill so the slot is visible.

## 4. Bias screen upgrade
- Add "Full Backtest" expandable section (or sub-route) below the viability
  strip: per-strategy stats (return vs B&H, max DD, win rates by direction)
  and the last 15 trades as win/loss-colored rows (green/red left border,
  return badge). Data already in GET /api/backtest.

## Explicitly deferred (do NOT build)
- Watchlist add/remove (needs write API + real persistence → Supabase phase)
- Co-Pilot / AI stress test / AI sentiment (Phase 4b, credits-gated)

## Definition of done
All five tabs live against the real API, no horizontal overflow at 393px,
standalone mode verified, commit per screen.
