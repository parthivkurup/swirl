-- Phase 6d / author-match guard: record which monitored profile visit SURFACED a
-- capture, distinct from source_handle (who actually wrote the post). For a post
-- read off a monitored profile that is authored by a third party (a tagged /
-- collab / feature post, e.g. a food blogger posting "Yolux is doing 20% off"),
-- source_handle honestly records the third-party author and via_handle records the
-- monitored profile it was surfaced under. Null for the account's own posts (where
-- source_handle already is the visited profile) and for non-Instagram sources.
-- Chain resolution reads: source_handle, then via_handle, then the @mention rule.
alter table raw_captures add column via_handle text;
