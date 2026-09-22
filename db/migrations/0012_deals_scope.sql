-- Which city a deal is for.
--
-- Some monitored chains are national, so their Instagram announces deals for
-- stores we do not serve. Before this column those extracted identically to a
-- Melbourne deal and were published as one: #114 and #156 (Yo-Bar's Canberra
-- Centre grand opening) and #123 (Yo Way) were all approved and went live on the
-- public dashboard. That is the tracker publishing something FALSE, which is a
-- different and worse failure than publishing something incomplete.
--
-- Classified, never discarded, the same way category handles non-froyo deals.
--   melbourne - for a Greater Melbourne store; the only thing '/' publishes
--               without qualification.
--   other     - for a store somewhere else; captured and reviewable, but never
--               shown on '/' at all, not even under the Everything toggle.
--               (Everything is a category axis; scope is not a category.)
--   unknown   - genuinely not established. Shown on '/' but visibly marked,
--               because hiding it would lose the largest chains entirely and
--               "nobody misses a deal" is half the point. Same principle as the
--               stale band: state the gap, do not hide the row.
--
-- Default 'unknown' so a writer that forgets this column cannot silently produce
-- a Melbourne-looking deal. Set by ingest.postprocess.derive_scope, which
-- combines the extractor's caption-local evidence with the chain's footprint.
alter table deals add column scope text not null default 'unknown'
  check (scope in ('melbourne', 'other', 'unknown'));

create index deals_scope_status_idx on deals (scope, status);

-- Does the monitored account announce deals for stores outside GREATER
-- Melbourne? Mirrors config/chains.yaml; see the header there for the full
-- definition. 'unknown' is treated exactly as 'national' (the safe side).
alter table chains add column footprint text not null default 'unknown'
  check (footprint in ('melbourne_only', 'national', 'unknown'));

-- Backfill, by hand and exactly, not by heuristic.
--
-- Part 1: the 16 deals whose store_hint_raw already named a place. The extractor
-- had been reading the location correctly all along; resolve_store then dropped
-- it, because the stores table is empty until Phase 9 and so never matched. Only
-- seven distinct values exist, so every one is classified explicitly here rather
-- than pattern-matched.
update deals set scope = 'other'
  where store_hint_raw in ('Canberra Centre', 'Coolangatta');

update deals set scope = 'melbourne'
  where store_hint_raw in (
    'Port Melbourne',
    'The Glen & Melbourne Central',
    'Carlton',
    'Docklands',
    'Shop 1, 221 Queen Street, Melbourne'
  );

-- Part 2: the 19 deals whose caption named no place at all. These get the same
-- answer the live rule gives for stated_location = 'none': the chain decides.
-- A national chain, an unknown-footprint chain, or no chain at all stays
-- 'unknown'.
--
-- The melbourne_only chains are listed by name rather than read from
-- chains.footprint on purpose: db.seed runs AFTER migrations, so at this point
-- every chain still carries the 'unknown' default and joining on it would
-- silently do nothing. This is a point-in-time backfill of one existing
-- database; on a fresh one there are no deals and it is a no-op. The live rule
-- reads chains.footprint properly.
update deals d set scope = 'melbourne'
  where d.store_hint_raw is null
    and d.chain_id in (
      select id from chains where name in (
        'Yokli', 'Yolux', 'gojé', 'Froyolicious',
        'FRO-BAE Frozen Yoghurt & Acai', 'Just Crave It', 'YO MAMA Froyo & Acai',
        'Froyo Culture', 'YO-TO Frozen Bar', 'blu spoon', 'Big Bang Yogurt',
        'Vanilla Dessert Bar'
      )
    );
