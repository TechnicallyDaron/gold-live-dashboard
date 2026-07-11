-- ═══ N-CORE schema v4 (additive) ═══
-- Frequency column powers the Hub's re-layering: pairs sort by how often
-- they actually fire, so high-velocity pairs dominate the primary view.
alter table playbooks add column if not exists oos_signals_per_week numeric;
