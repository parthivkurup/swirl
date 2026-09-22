-- Classifies each deal so the froyo tracker can default to froyo while still
-- keeping adjacent-dessert and other offers (e.g. the burger deals on a hybrid
-- venue's promo image) rather than discarding them at extraction time.
alter table deals add column category text
  check (category in ('froyo', 'adjacent', 'other') or category is null);
