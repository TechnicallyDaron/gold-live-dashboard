-- ═══ N-CORE schema v2 (additive — run AFTER schema.sql) ═══

-- Restart-proof alert dedupe: the fix for repeated IWM-style alerts.
create table if not exists cooldowns (
  key text primary key,
  until_ts timestamptz not null
);
-- Global system table (agent-owned, no per-user rows): RLS on, no public
-- policies — only the service role (backend) can touch it.
alter table cooldowns enable row level security;

-- Daily Catalyst Screener output
create table if not exists screener_results (
  id bigint generated always as identity primary key,
  scan_date date not null,
  ticker text not null,
  price numeric,
  rvol numeric,
  breakout_date date
);
alter table screener_results enable row level security;
create policy "screener readable by authenticated"
  on screener_results for select using (auth.role() = 'authenticated');

create index if not exists idx_screener_date on screener_results (scan_date desc);

-- Watchlist ordering (HUB top-4 drives the Daily Digest)
alter table watchlists add column if not exists priority int not null default 100;
create index if not exists idx_watchlists_prio on watchlists (user_id, priority asc, id asc);
