# N-CORE PWA — PHASE 5 (frontend): AUTOMATION + AVERAGE-JOE UX

Backend live after pull. Law: no Python edits. Commit per feature, build after each.
LANGUAGE RULE everywhere: plain everyday English, zero jargon — but NEVER promissory
("highly likely", "guaranteed"). History phrased as history: "setups like this won
67% of the time in testing."

## New/changed API surface
- /api/bias/{asset} gained: assigned_strategy{strategy,name,assigned_at} | null,
  signaling_today bool, signal_side "long"|"short"|null
- GET /api/scan → {hits:[{asset,ticker,strategy,strategy_name,side,price}], playbook_size}
- GET /api/notifications?since={unix_ts} → [{ts,kind:"playbook"|"exhaustion"|"macro",title,body}]
- POST /api/push/subscribe (raw PushSubscription JSON) → {ok,subscriptions,push_configured}
- POST /api/watchlist {name,ticker,unit} · DELETE /api/watchlist/{name}
  → both return {watchlist, persistence_warning} — ALWAYS surface the warning as an
  amber toast (Railway disk resets on redeploy).
- POST /api/positions {asset,strike,contract_type,entry_premium,entry_date,expiration,
  premium_stop?,time_stop?,invalidation_above?,invalidation_below?} → {id,position,
  shield_armed,persistence_warning}

## 1. ZERO-SCROLL BRIEFING (the big one)
Restructure Briefing to fit ONE viewport, no vertical scroll, on iPhone 16 (393×852)
in standalone:
- Keep: tape (or macro hijack banner) + slim title line
- Watchlist becomes a 2×2 paginated card grid: 4 assets per page, swipe horizontally
  (scroll-snap) or dots to page through the rest. Cards compress: name, price, %,
  and ONE status chip (😴 quiet / 👀 close / 🟢🔴 setup LIVE / 🎯 playbook firing —
  derive from bias color + signaling_today).
- Macro Week track shrinks to a single-row strip at the bottom.
- Nothing below the fold. Test with CDP viewport 393×852, assert scrollHeight ≤ innerHeight.

## 2. TICKER TAP → QUICK-LOOK MODAL
Tape items become tappable: opens a bottom-sheet modal (75vh, drag-to-dismiss) with
that symbol's quote + /api/bias read in plain language + a "Full analysis →" link
that adds it to context on the Bias tab. Reuse the plain phrasing from the API.

## 3. CYCLING MICRO-CHART (Briefing)
A compact sparkline card that auto-cycles through watchlist assets every 8s
(pause on touch): /api/history?days=90, price line only + baseline dashed, asset
name + price overlay. Tap → jumps to Chart tab with that asset selected.

## 4. SWIPEABLE TRADE CARDS + IN-APP VALIDATION (Bias)
The backtest trade rows become a horizontal swipe deck (scroll-snap cards).
Each card: entry→exit, dates, return badge — plus a "🔎 Validate this pattern now"
button that pre-fills the Validate control with that trade's entry price and fires
POST /api/validate. Plain-language rendering of the 3 bullets + verdict pill.

## 5. VOLT BELL + NOTIFICATIONS
- Header bell icon (volt #00E5FF) on all screens. Poll /api/notifications every 60s
  with `since` = last seen ts; unseen count badges the bell; panel lists events
  (kind icon, title, body, relative time).
- NEW playbook/exhaustion events ALSO flash the volt overlay card on the matching
  Briefing asset row (reuse the exhaustion flash pattern).
- WEB PUSH: service worker `push` handler shows the notification; on first launch
  (after a user gesture) request Notification permission, subscribe via
  pushManager.subscribe (userVisibleOnly, applicationServerKey = VAPID public key
  from VITE_VAPID_PUBLIC_KEY env), POST subscription to /api/push/subscribe.
  If push_configured=false in the response, show a one-time muted note
  "Server push not configured — in-app alerts still active."

## 6. POSITION ENTRY FORM (Positions screen)
"+ Log Position" button → bottom-sheet form matching PositionBody exactly
(asset picker from watchlist, strike, call/put toggle, premium, dates via native
date inputs, optional stops/invalidation). Submit → POST /api/positions → success
toast "🛡 Guardian armed" + the persistence_warning as amber sub-toast → refresh
/api/shield list. Also add watchlist add/remove UI on Briefing (long-press a card
→ remove; "+" tile on the last grid page → add form) using the new endpoints.

## 7. PLAIN-ENGLISH SWEEP
Audit every label/tooltip: "Z-Score" → "Stretch" (how far from its usual range),
"Invalidation" → "You're wrong past", "Target" → "Take profit near",
"HTF Trend" → "Bigger trend". Keep numbers everywhere. AI answer cards keep the
volt border; prompts already return plain language from the backend.
