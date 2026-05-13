-- Listn Intel — fix RLS on admin tables so the dashboard can write to them.
-- Run in Supabase SQL Editor.
--
-- These two tables are internal admin-only data with no end-user exposure.
-- Disabling RLS matches the pattern your other reference tables already use
-- (competitors / content_clusters / tone_keywords).

alter table admin_audit disable row level security;
alter table competitor_candidates disable row level security;

-- If you'd rather keep RLS on, comment the lines above and uncomment these:
-- alter table admin_audit enable row level security;
-- alter table competitor_candidates enable row level security;
-- create policy admin_audit_all on admin_audit for all using (true) with check (true);
-- create policy competitor_candidates_all on competitor_candidates for all using (true) with check (true);
