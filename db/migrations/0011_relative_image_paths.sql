-- image_path was stored absolute ("/abs/path/to/froyo/media/submissions/x.jpg"),
-- which bakes one machine's directory layout into the data and breaks on any other
-- checkout. Paths are now stored relative to a configurable media root (MEDIA_ROOT,
-- default <repo>/media), so this rewrites the existing rows to match.
--
-- The pattern is deliberately machine-agnostic: it strips everything up to and
-- including the last "/media/" rather than a hardcoded prefix. A row whose path
-- does not contain "/media/" is left absolute, and the readers still handle that.
update raw_captures
   set image_path = regexp_replace(image_path, '^.*/media/', '')
 where image_path like '/%'
   and image_path like '%/media/%';
