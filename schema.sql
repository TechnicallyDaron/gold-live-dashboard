-- ═══ N-CORE TERMINAL — Supabase schema v1 ═══
-- Multi-tenant from day one: every user-owned row carries user_id,
-- and RLS makes cross-user reads physically impossible at the DB layer.
-- Run this in Supabase: SQL Editor → New query → paste → Run.

-- Profiles: one row per auth user; tier gates tool vs signals vs both
create table if not exists profiles (
  id uuid references auth.users(id) primary key,
  email text,
  display_name text,
  tier text not null default 'beta' check (tier in ('beta','signals','tool','full')),
  created_at timestamptz not null default now()
);

create table if not exists watchlists (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) not null,
  display_name text not null,
  ticker text not null,
  unit text not null default '/sh',
  created_at timestamptz not null default now(),
  unique (user_id, display_name)
);

create table if not exists positions (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) not null,
  asset text not null,
  contract_type text not null check (contract_type in ('call','put')),
  strike numeric not null,
  entry_premium numeric not null,
  entry_date date not null,
  expiration date not null,
  premium_stop numeric,
  time_stop date,
  invalidation_above numeric,
  invalidation_below numeric,
  status text not null default 'open' check (status in ('open','closed')),
  created_at timestamptz not null default now()
);

-- The permanent audit log — the track record.
create table if not exists journal (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) not null,
  position_id bigint references positions(id),
  asset text not null,
  contract_type text,
  strike numeric,
  entry_date date,
  exit_date date,
  entry_premium numeric,
  exit_premium numeric,
  pnl_pct numeric,
  holding_days int,
  strategy text,
  strategy_name text,
  verdict_at_close text,
  thesis text,
  rule_compliant boolean,
  notes text,
  logged_at timestamptz not null default now()
);

-- Per-user strategy playbooks (walk-forward assignments)
create table if not exists playbooks (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) not null,
  asset_key text not null,
  strategy text not null,
  strategy_name text not null,
  assigned_at date not null,
  oos_win_rate numeric,
  oos_profit_factor numeric,
  oos_expectancy_pct numeric,
  unique (user_id, asset_key)
);

create table if not exists notifications (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) not null,
  kind text not null,
  title text not null,
  body text not null,
  seen boolean not null default false,
  created_at timestamptz not null default now()
);

-- ═══ ROW LEVEL SECURITY: private workspaces, DB-enforced ═══
alter table profiles      enable row level security;
alter table watchlists    enable row level security;
alter table positions     enable row level security;
alter table journal       enable row level security;
alter table playbooks     enable row level security;
alter table notifications enable row level security;

create policy "own profile"       on profiles      for all using (auth.uid() = id)      with check (auth.uid() = id);
create policy "own watchlist"     on watchlists    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own positions"     on positions     for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own journal"       on journal       for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own playbook"      on playbooks     for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own notifications" on notifications for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create index if not exists idx_watchlists_user on watchlists (user_id);
create index if not exists idx_positions_user  on positions (user_id, status);
create index if not exists idx_journal_user    on journal (user_id, exit_date desc);
create index if not exists idx_notif_user      on notifications (user_id, created_at desc);
