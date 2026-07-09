# N-CORE PWA — PHASE 7 (frontend): THE HUB, OBSIDIAN PORTAL, SCREENER

Backend live after pull. Law: no Python edits. Commit per feature.
Tokens: deep charcoal #0B0E14, neon volt, NEW accent: bullion gold #E8B54A
(Portal only — don't bleed gold into the terminal screens).

## 1. GLOBAL REBRAND: BRIEFING → HUB
Rename every user-visible "Briefing"/"Command Center" reference to "HUB":
tab label, route (/hub with redirect from old path), headers, aria labels.
Internal component filenames may keep their names if renaming risks churn —
user-visible strings are the requirement.

## 2. OBSIDIAN PORTAL (auth gateway upgrade)
Replace the plain login screen: full-viewport obsidian (#0B0E14) overlay,
thin bullion-gold (#E8B54A) border vectors/frame, slow-fading market data
arrays drifting in the background (decorative, low-opacity, CSS-animated —
use static sample arrays, no live fetch pre-auth). Blur the app behind it;
on successful Supabase session, unblur/dissolve into the HUB.
Existing behavior stands: no Supabase env → no gate at all.

## 3. MARQUEE TAKEOVER BUG FIX
When macro-radar hijack replaces the ticker tape, the banner currently
freezes into a static block. Root cause is likely the hijack branch
rendering outside the animation wrapper. Fix: the hijack content must
inherit the same scrolling/keyframe wrapper (or an equivalent pulse
animation) — never a dead static strip. Verify by forcing hijack=true
locally and confirming continuous animation.

## 4. SPACING PASS (HUB, Chart wrappers, Positions ONLY)
Push content down out of safe-area crowding at the top; keep the bottom
flush to the tab bar (that fix already shipped — don't regress it).
Bias and News: DO NOT TOUCH. Verify on real-device metrics (393×852).

## 5. QUIET-ASSET COLLAPSE (HUB)
Assets whose bias is neutral/no-trade AND not playbook-firing AND not in
the latest screener hits collapse into a compact "Quiet (N)" expandable
row at the bottom of the grid. Active/watch/firing assets keep full cards.
The 2×2 grid + pagination logic now applies to ACTIVE assets only.

## 6. CATALYST SPOTLIGHT (HUB, top of layout)
GET /api/screener → {scan_date, hits:[{ticker, price, rvol, breakout_date}]}.
If hits exist: a gold-edged spotlight strip ABOVE the watchlist grid:
"🚀 Catalyst: TICKER $price — X.X× volume, fresh 52-wk breakout".
Multiple hits: horizontal swipe. Tapping deep-links to Bias for that ticker.
Empty: render nothing (no empty-state card — silence is the state).

## 7. ONBOARDING BASKETS (post-signup, Supabase mode only)
First login with an empty watchlist → basket picker screen (charcoal/volt):
preset baskets (Index ETFs / Megacap Tech / High-Velocity / Commodities+Rates)
as multi-select chips with the ticker lists visible; POST each selection
to /api/watchlist. Skipping is allowed but requires confirming an empty HUB.

## 8. POSITIONS POLISH
Verify PnL badges + close flow against the store-backed endpoints (ids are
now numeric strings in DB mode). The close success toast should read
"🛡 Logged permanently" when no persistence_warning is present in the
response (DB mode), keeping the amber warning toast only in file mode.
