# N-CORE PWA — PHASE 6 (frontend): PnL, JOURNAL, LOGIN GATE, SPACING

Backend live after pull. Law: no Python edits. Commit per feature.

## 1. TARGETED SPACING (do NOT touch Bias or News containers)
Audit Briefing, Chart wrapper, Positions containers only. Adjust inner
padding / safe-area top+bottom so headers, chart edges, and cards never
clip viewport boundaries. Verify at 393×852 standalone via CDP.

## 2. LIVE PnL BADGES (Positions)
/api/shield rows now carry pnl: {live_premium, entry_premium, pnl_pct,
source, note?}. Render a prominent badge per position: volt-green glow
for pnl_pct > 0 (e.g. "+21.2%"), muted crimson for negative.
pnl_pct === null → gray "PNL UNAVAILABLE" chip with the note as tooltip —
NEVER estimate from spot client-side.

## 3. CLOSE-POSITION FLOW (Positions)
"Close" button per card → bottom sheet: exit_premium (number), thesis
(text), rule_compliant (Yes/No toggle: "Did this exit follow your plan?"),
notes → POST /api/positions/{id}/close → success toast with pnl_pct +
persistence warning → refresh shield list.

## 4. JOURNAL DASHBOARD (new section on Positions, below actives)
GET /api/journal → entries + aggregates. Render:
- Headline stat row: total trades · win rate · avg PnL% · avg holding days
  · RULE ADHERENCE % (make adherence visually loudest — it's the discipline
  grade)
- Per-strategy mini-table from aggregates.per_strategy
- Entry list: asset, dates, pnl badge (same colors), rule-compliant ✓/✗,
  thesis on expand

## 5. EXPLAINABLE REFUSALS (Bias)
Wherever the API returns INVALID (reasons[]), NO_EDGE (thresholds+regime),
or NOTHING_VALIDATED (per-strategy fail_reasons[]): render the specific
failed hurdles as plain bullet chips under the verdict — e.g.
"only 3 out-of-sample trades (< 10)". Never a bare refusal.

## 6. CANDIDATES STRIP (Bias, collapsed by default)
GET /api/candidates → "🔎 Velocity leads" expandable: rows with family,
side, price, and a LOUD amber "⚠️ UNVALIDATED — run Lab first" chip unless
validated=true. Tapping a row deep-links to the Strategy Lab for that asset.

## 7. LOGIN GATE (Supabase Auth)
- npm i @supabase/supabase-js. Env: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY.
- If envs absent → skip the gate entirely (operator file-mode, current behavior).
- If present: unauthenticated users see a login screen (charcoal/volt tokens):
  email magic-link sign-in + a disabled "Continue with Google (soon)" button.
- On session: attach Authorization: Bearer <access_token> to API calls;
  verify once against /api/me; show email + sign-out in a settings corner.
- Data endpoints stay shared for now (migration to per-user rows is the next
  backend phase) — the gate establishes identity, not yet isolation.
