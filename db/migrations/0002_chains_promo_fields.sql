alter table chains add column promo_url text;
alter table chains add column posts_promos text;

-- CHECK not a native enum, so values can be added later without a type migration.
-- A CHECK passes on NULL, so null stays a valid posts_promos value.
alter table chains add constraint chains_posts_promos_check
  check (posts_promos in ('instagram', 'website', 'both', 'none'));
