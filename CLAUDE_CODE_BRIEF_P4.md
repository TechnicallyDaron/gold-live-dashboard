# N-CORE PWA — PHASE 4: HIGH-ALPHA LAYER (frontend)

Backend live after pull. Law unchanged: no Python edits. Commit per feature,
npm run build after each, existing tokens + safe-areas exactly.

## New endpoints
- GET /api/optimized-edge/{asset} → {flag: "EDGE_FOUND"|"NO_EDGE",
    candidates:[{name, signal_today, win_rate_5y, trades_5y, expectancy_pct}],
    scanned:[...], regime:{label, drift_pct, band_breaks, note}, thresholds}
- GET /api/macro-radar → {hijack: bool, nearest:{event, time_et,
    minutes_remaining}, events_today:[...]}
- POST /api/validate {asset, entry, side?} → {verdict "VALID"|"INVALID",
    side, reasons[], analysis (markdown, 3 bullets + bold verdict line),
    usage} · rules-only fallback has analysis:null + note
- GET /api/shield → [positions + shield:{atr, spot, target, horizon_days,
    elapsed_days, pct_exhausted, status: OK|WARN_80|CUT|NO_ENTRY_DATE|NO_HORIZON|DATA_ERROR}]
- GET /api/exhaustion/{asset} → {triggered, side, z, rsi, price}

## 1. Bias — Alpha Optimizer strip
Fetch optimized-edge with the bias load. NO_EDGE → clean notice card:
"🛡 NO EDGE DETECTED — no strategy is both signaling and 5y-validated.
Sitting on hands IS the position." (muted border, regime label as sub-line).
EDGE_FOUND → volt-edged card per candidate: name, side chip, 5y win %, n,
expectancy. Always render the regime note in small muted text — never hide it.

## 2. Banner Hijack
Poll /api/macro-radar every 60s. hijack=true → replace the tape with a
STATIC banner, identical height/radius/placement: amber (#E2A93B) border +
text, slow 1.2s opacity pulse (no marquee motion), content:
"⚠️ HIGH IMPACT: USD {event} in {minutes_remaining}m" (live-tick the minutes
client-side between polls). hijack=false → normal tape returns.

## 3. Validate Trade (Bias screen)
Under Quick Prompts: number input (entry) + Long/Short segmented toggle
(optional — omit to let the engine infer) + "🔎 Validate" button →
POST /api/validate. Render analysis markdown; verdict pill: VALID = long-green
fill, INVALID = short-red fill, large + bold. Rules-only fallback: render
reasons[] as bullets + the note, same pill.

## 4. Theta Shield (Positions screen)
Switch data source to /api/shield. Per position add a lifecycle progress bar
(pct_exhausted): OK = volt fill · WARN_80 = amber fill + pulsing
"⚠️ 80% of statistical window exhausted — cut if target unmet" ·
CUT = red full bar + "⛔ Window exhausted — close the contract".
NO_ENTRY_DATE → muted bar + "add entry_date to positions.json to arm the shield".

## 5. Exhaustion flash (Briefing)
On the Briefing refresh cycle, check /api/exhaustion/{asset} for watchlist
assets. triggered=true → neon-green volt overlay card on that asset row:
"💰 EXHAUSTION — extreme overextension at ${price}. Consider locking premium."
Dismissible; re-shows only on a new trigger day.

## 6. Strategy Lab (Bias screen, below the optimizer strip)
GET /api/strategy-lab/{asset} → {flag: "STRATEGY_ASSIGNED"|"NOTHING_VALIDATED",
  assigned:{name, test:{win_rate, profit_factor, expectancy_pct, signals_per_week, n}},
  results:[{name, validated, test:{...}, fail_reasons[]}], criteria, note}
- "🧪 Run Strategy Lab" button (it's compute-heavy — on demand, not on load)
- Result: one row per family — ✅/❌, name, OOS win % · PF · exp/trade · signals/wk;
  failed rows show fail_reasons small + muted
- STRATEGY_ASSIGNED → bullion-glow banner "🎯 ASSIGNED: {name} — this asset's
  one strategy" · NOTHING_VALIDATED → the shield card: "standing aside IS
  the strategy"
- ALWAYS render the API's `note` line in muted text under the results.
