-- Links each extracted deal back to the raw_capture it came from, so the review
-- queue can show the original caption and image beside the extracted fields.
-- Nullable: deals may predate this column or come from paths without a capture.
alter table deals add column raw_capture_id bigint references raw_captures(id);
create index deals_raw_capture_idx on deals (raw_capture_id);
