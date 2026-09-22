-- The shop name a submitter types into /submit, kept as its own column instead of
-- being concatenated into content_text as "Store: <name>". The extractor prompt is
-- right that a labelled form field is not caption prose, so the model correctly
-- refuses to read it as a store_hint; carrying it structurally is the fix.
--
-- Deliberately not named store_hint: deals.store_hint_raw holds whatever a model
-- derived from content, this holds what a human typed into a form, and the two
-- have different trust characteristics. Null for every non-submission source.
alter table raw_captures add column submitted_store text;
