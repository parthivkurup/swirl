-- Auto-merge of duplicate approved deals: supersede, never delete. The canonical
-- (earliest-created, lowest-id) deal keeps its row; each duplicate points at it via
-- superseded_by. The dashboard excludes any deal with superseded_by set; /review
-- can list them to inspect and undo (clear the column).
alter table deals add column superseded_by bigint references deals(id);
create index deals_superseded_by_idx on deals (superseded_by);
