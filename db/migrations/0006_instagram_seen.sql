-- Phase 6d: per-account high-water mark for the Instagram feed scraper.
-- One row per monitored account. last_shortcode is the newest post shortcode we
-- have already captured, so the scraper can stop scrolling when it reaches it.
-- last_seen_at is when the account last appeared in the feed, which drives the
-- "not seen for 7+ days" single profile-visit fallback.
create table instagram_seen (
  account text primary key,
  last_shortcode text,
  last_seen_at timestamptz not null default now()
);
