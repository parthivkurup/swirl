-- How many times extraction has failed for this capture.
--
-- A capture whose extraction fails is left processed = false and retried on the
-- next run, which is correct for a transient API failure and wrong forever after
-- that: before this column a capture that failed every single time was retried
-- twice a day indefinitely, and the only trace was one log line per run buried in
-- logs/scrape.log. The shape is a bounded strike count: after a number of
-- consecutive failures, stop and say so loudly rather than failing quietly
-- forever.
--
-- Reset to 0 by hand to requeue a capture that was abandoned:
--   update raw_captures set extract_attempts = 0 where id = ...;
alter table raw_captures add column extract_attempts int not null default 0;

-- The retry queue is "not processed and not yet abandoned", so this is the index
-- the scheduled extract actually reads.
create index raw_captures_retry_idx on raw_captures (processed, extract_attempts);
