-- Insert (or update if name already exists) the three adjacent competitors.
-- Idempotent: safe to re-run. Mirrors scripts/insert_new_competitors.py.

insert into competitors (name, meta_search_terms, seo_domain, appstore_id, active, notes)
values
  ('ElliQ',
   array['ElliQ', 'Intuition Robotics'],
   'elliq.com',
   null,
   true,
   'Adjacent: robot companion for seniors. Meta page_id 434160116949836. Runs Meta ads.'),
  ('Papa',
   array['Papa Inc', 'Join Papa'],
   'papa.com',
   null,
   true,
   'Adjacent: human caregiving / companionship marketplace. No Meta ads at integration time.'),
  ('friend.com',
   array['friend.com', 'Friend AI'],
   'friend.com',
   null,
   true,
   'Adjacent: AI friend pendant (hardware). No Meta ads at integration time.')
on conflict (name) do update set
  meta_search_terms = excluded.meta_search_terms,
  seo_domain        = excluded.seo_domain,
  appstore_id       = excluded.appstore_id,
  active            = excluded.active,
  notes             = excluded.notes;

select name, seo_domain, active from competitors where name in ('ElliQ', 'Papa', 'friend.com');
