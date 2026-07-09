-- ═══ N-CORE schema v3 (additive — run AFTER schema.sql + schema_v2.sql) ═══
-- The Signal Ledger: every playbook signal the system ever fires, logged
-- and resolved by the machine with zero human involvement. This is the
-- verified track record — losses land here as automatically as wins.
create table if not exists signal_ledger (
  id bigint generated always as identity primary key,
  fired_at timestamptz not null default now(),
  fired_date date not null,
  asset text not null,
  ticker text not null,
  strategy text,
  strategy_name text,
  side text not null check (side in ('long','short')),
  entry_ref numeric,
  stop_ref numeric,
  target_ref numeric,
  status text not null default 'open'
    check (status in ('open','target_hit','stopped','expired')),
  resolved_date date,
  resolve_price numeric,
  result_pct numeric
);
alter table signal_ledger enable row level security;
create policy "ledger readable by authenticated"
  on signal_ledger for select using (auth.role() = 'authenticated');
create index if not exists idx_ledger_status on signal_ledger (status, fired_date desc);
