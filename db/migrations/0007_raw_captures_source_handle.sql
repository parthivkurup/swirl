-- Phase 6d / Finding 1: record the Instagram profile a capture was scraped from.
-- The chain is known at scrape time (we visit a known handle), so keep it instead
-- of discarding it and re-guessing later. Post-processing resolves chain_id from
-- source_handle before falling back to the @mention rule. Null for non-Instagram
-- captures (website, manual, user submissions), which carry no owning handle.
alter table raw_captures add column source_handle text;
