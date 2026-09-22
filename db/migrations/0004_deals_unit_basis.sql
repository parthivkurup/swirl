-- Self-serve froyo is priced by weight, so a stated price needs a basis:
-- 'flat' (per cup/item), 'per_100g', or 'per_kg'. Without this a "$3 per 100g"
-- offer could only be stored as a misleading flat $3.
alter table deals add column unit_basis text
  check (unit_basis in ('flat', 'per_100g', 'per_kg') or unit_basis is null);

-- The extracted location hint verbatim, kept whether or not fuzzy resolution to
-- a store succeeds, so the review queue can tell "no location named" (null) from
-- "location named but unresolved" (non-null with store_id still null).
alter table deals add column store_hint_raw text;
