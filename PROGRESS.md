# Progress log

Autonomous run through phases 2 to 5. Newest entries at the bottom of each phase.

## Decisions carried across the whole run

- **store_hint from prose only.** Hashtags do NOT feed store_hint; only a
  location named in prose does. Stated explicitly in the extractor prompt.
  Fixture 001 changed from `"The District Docklands"` to `null` (see phase 4).
- **content_hash for image-only captures.** SPEC defines content_hash as the
  sha256 of normalised text. An image-only capture has no text, so its bytes
  are hashed instead. Text captures still hash normalised text.

---

## Phase 2: manual ingestion (2026-08-04)

### Built
- `ingest/scrapers/base.py`: `RawCapture` dataclass and the `Scraper` interface
  (`fetch() -> list[RawCapture]`). `RawCapture.captured_at` is optional so
  historical/fixture captures can set it; None lets the DB default apply.
- `ingest/scrapers/manual.py`: `ManualScraper` for a text blob or local image.
- `ingest/scrapers/instagram.py`, `aggregator.py`: interface stubs raising
  NotImplementedError, per the ingestion architecture in SPEC.
- `ingest/hashing.py`: `content_hash` = sha256 of normalised text (lowercase,
  strip URLs, strip emoji, collapse whitespace).
- `ingest/captures.py`: `insert_captures`, dedupe via `on conflict (content_hash)
  do nothing`. Reused by the manual CLI and later fixture seeding.
- `ingest/manual.py`: CLI `python -m ingest.manual --text ... | --image ...`.
- `ingest/db.py`, `ingest/log.py`: connection helper and structured JSON logging.

### CHECK: same caption twice produces one row
```
{"event": "manual.capture", "content_hash": "3f894fca...", "id": 1, "inserted": true, "duplicate": false}
{"event": "manual.capture", "content_hash": "3f894fca...", "id": null, "inserted": false, "duplicate": true}
raw_captures total: 1
  row: (1, 'manual', False, '3f894fca43b3...')
```
The second insert used the same text with reordered whitespace, an added
trailing URL, and a moved emoji; normalisation collapsed it to the same hash.
Image path smoke-tested separately: identical file bytes deduped the same way.
raw_captures reset to empty afterward so phase 3 starts clean.

### Requirement audit (SPEC phase 2 + ingestion architecture)
- CLI `--text` and `--image`: PASS (both exercised)
- writes one raw_captures row: PASS
- dedupe on content_hash: PASS
- content_hash = sha256 normalised (lowercase, collapse ws, strip emoji+URLs): PASS
- scrapers in ingest/scrapers/ sharing one list[RawCapture] interface: PASS
- instagram.py / aggregator.py stub with NotImplementedError: PASS
- website.py: correctly NOT built (phase 6)
- structured JSON logging to stdout for every scrape: PASS

### Deferred
- Image-only OCR/text: none by design at this stage. See DEFERRED.md for the
  content_hash-on-bytes note.

---

## Phase 3: extractor (2026-08-04)

### Built
- `ingest/prompts/extract_deal.txt`: system prompt, loaded at runtime, written
  to SPEC's bullets plus the store_hint-prose-only rule and the days_of_week /
  channels conventions from NOTES.md.
- `ingest/schemas.py`: pydantic `Deal` / `CaptionResult` / `BatchResult` with
  enum fields (deal_type, discount_unit, channels), used as the Gemini
  responseSchema so invalid enum values are impossible.
- `ingest/gemini_client.py`: google-genai client, model gemini-flash-latest,
  fallback gemini-flash-lite-latest on 429 with exponential backoff.
  responseMimeType application/json + responseSchema. Images sent as inline
  bytes in the same request.
- `ingest/extractor.py`: per-caption disk cache keyed by content_hash +
  prompt_hash; batches up to 10 text captions per request (images sent singly);
  a failed or misaligned batch retries as individual requests; captures that
  still fail are left unprocessed.
- `ingest/postprocess.py`: store_hint -> store_id fuzzy match (difflib) on name
  plus suburb, null with no confident match and chain_id from the matched store;
  min_spend_aud -> cents; source_hash for repost dedupe; auto-approve only when
  confidence >= 0.8 AND source_type == 'website'.
- `ingest/extract.py`: CLI. Default reads unprocessed raw_captures and writes
  pending deals; `--reprocess-since YYYY-MM-DD`; `--fixtures` for inspection.
- `ingest/fixtures_io.py`, `ingest/seed_fixtures.py`: fixture loading and
  seeding fixtures into raw_captures (used to verify the DB path and to seed the
  phase 5 queue).

### CHECK: run against tests/fixtures/captions/, inspect output
Extractor output compared to fixture ground truth via `tests/compare.py`:
```
STATS: {'total': 30, 'cache_hits': 0, 'batches': 3, 'api_calls': 3}
30/30 fixtures pass; 0 problems; failed=[]
```
DB path end to end:
```
{"event": "extract.db", "deals_inserted": 19, "captures": 30, "cache_hits": 30, "api_calls": 0}
raw_captures total/processed: (30, 30)
deals by status: [('pending', 19)]
distinct source_hash / total deals: (19, 19)
reprocess-since re-run: deals_inserted 0, deals unchanged at 19
```
19 deals = the 19 positive objects (12 negatives correctly produced none). All
pending because source_type is 'fixture', not 'website'.

### API budget
7 API calls total for the whole phase (1 connectivity + 3 + 3 across two prompt
iterations). Cache means re-runs and the phase 4 tests cost 0. Well under 200.

### Requirement audit (SPEC phase 3 + extractor section)
- reads unprocessed raw_captures, writes deals as pending: PASS
- google-genai, gemini-flash-latest, flash-lite fallback on 429: PASS (fallback
  coded and reachable; not triggered in this run)
- native structured output, responseMimeType + responseSchema, enum fields: PASS
- images as inline_data in same request, no separate OCR: PASS (coded; no image
  fixtures to exercise it)
- batch up to 10, array-of-arrays index-aligned, per-item retry on validation
  failure, 429 backoff, unprocessed stay unprocessed: PASS
- system prompt in ingest/prompts/extract_deal.txt loaded at runtime: PASS
- store_hint -> store_id fuzzy on name+suburb, null with no match, chain if
  identifiable: PASS (stores table empty by design until phase 9, so resolves to
  null now; fuzzy logic unit-tested in phase 4)
- auto-approve only confidence >= 0.8 AND source_type == 'website': PASS
- source_hash prevents duplicate deals: PASS (reprocess inserted 0)
- python -m ingest.extract --reprocess-since: PASS
- cache keyed by content_hash + prompt_hash, under 200 API calls: PASS

### Decisions
- Fixture 001 store_hint set to null (hashtag-only location), per the run's
  store_hint-prose-only rule, stated in the prompt.
- Prompt iterated twice against ground truth: (1) a recurring weekday offer with
  no stated dates has null valid_from/valid_to (do not use CAPTURE_DATE as
  valid_from); (2) a named weekday category ("this weekend", "sat + sun")
  populates days_of_week even when dates are also resolved, while a numeric dated
  range does not. Both are faithful to NOTES.md, not overfitting to answers.
- Comparison treats free-text (headline, conditions) and confidence by rule, not
  equality (an LLM cannot reproduce them verbatim). See DEFERRED.md and the
  docstring in tests/compare.py.

---

## Phase 4: tests (2026-08-04)

### Built
- `tests/compare.py`: structured comparison of extractor output vs fixture
  ground truth (created during phase 3 iteration, committed here).
- `tests/conftest.py`: session-scoped `extraction` fixture that runs the
  extractor over all 30 fixtures once, using the cache.
- `tests/test_extractor.py`: 30 parametrized fixture-match tests, 12 negative
  tests asserting `[]`, and a resolve_store fuzzy-match unit test.

### CHECK: green, and corrupting the prompt turns it red
Green (warm cache, no API calls):
```
43 passed, 1 warning in 0.04s
```
Prompt corrupted (truncated to drop every field rule), tests re-run:
```
17 failed, 26 passed in 112.16s
FAILED ...[001] channels: expected [] got ['dine_in'...]
FAILED ...[010] days_of_week: expected [5, 6, 7] got ...
FAILED ...[017] deal count expected 1 got 0
```
Prompt restored (sha256 d7cd15d5a7bc4854), re-run: `43 passed in 0.04s`. The red
run made real API calls against the new prompt_hash, proving the suite depends on
the prompt rather than on cached answers.

### Requirement audit (SPEC phase 4)
- pytest over fixture captions with expected JSON: PASS (30 parametrized)
- negatives returning []: PASS (12 dedicated tests; the match test also asserts
  count 0 for them)
- CHECK green: PASS (43 passed)
- corrupting the prompt turns it red: PASS (17 failed)
- fixtures are ground truth, .expected.json not edited to pass: honoured (the
  only fixture edit was the directed 001 store_hint -> null in phase 3)

### API budget
Roughly 40 API calls across the whole run so far (phase 3 iteration plus the
one deliberate corrupt-prompt run). A normal green pytest run costs 0.

### Deferred / decided
- Tests make real API calls on a cold cache (first run on a machine) to warm it,
  then cost nothing. The cache is gitignored, not committed. Recorded in
  DEFERRED.md.

---

## Phase 5: review queue (2026-08-04)

### Built
- Migration `0003_deals_raw_capture.sql`: adds nullable `deals.raw_capture_id`
  FK so the queue can show the originating caption beside each extracted deal.
  Additive, no data loss. Extractor now populates it.
- Next.js 14 app-router app under `web/` with Tailwind, raw SQL via `pg` (no
  ORM):
  - `app/review/page.tsx`: server component, loads pending deals joined to their
    raw_capture, lowest confidence first.
  - `app/review/ReviewQueue.tsx`: client component. Raw capture on the left
    (caption text plus inline image when present), every extracted field
    editable on the right. Buttons and keyboard shortcuts j / k / a / r
    (shortcuts ignore keystrokes while typing in a field).
  - `app/api/deals/[id]/route.ts`: POST approve / reject / edit_approve / save,
    parameterised SQL.
  - `app/api/image/route.ts`: serves a capture's source image, restricted to
    paths recorded in raw_captures.
  - `lib/db.ts`, `lib/deals.ts`: pooled connection and queries.
- Queue seeded from the extractor output over the fixtures: 19 pending deals.

### CHECK (operator-driven): approve 20 deals through the UI end to end
Cannot be completed by me (requires manual approval). What I verified instead:
- `/review` renders: `HTTP 200`, shows raw capture, editable fields, and real
  caption text.
- All four mutations persist to the DB through the same HTTP API the UI calls:
```
APPROVE 39: pending -> approved, last_verified set
REJECT  40: pending -> rejected
EDIT_APPROVE 43: headline/discount 30->42/channels []->[app,dine_in]/days []->[3,4]/
                 recurring false->true, status approved, last_verified set
SAVE 44: fields updated, status stays pending, last_verified not set
```
- `next build` compiles cleanly (typechecked).
After verifying, the queue was regenerated to a pristine 19 pending deals
(0 API calls) so the operator starts clean.

### Requirement audit (SPEC phase 5 + dashboard/review + stack)
- /review in the dashboard: PASS
- raw capture left, extracted fields right: PASS
- every field editable: PASS
- approve, reject, edit-and-approve: PASS (persistence verified)
- keyboard shortcuts j k a r: PASS
- show source image inline when present: PASS (route + <img>; no image fixtures
  to display, so not visually exercised)
- Next.js 14 app router + Tailwind, no ORM (raw pg SQL): PASS

### How to run the queue
```
cd web && npm install && npm run build && PORT=3000 npm start
# open http://localhost:3000/review
```
web/.env.local carries DATABASE_URL (gitignored).

### Decisions
- Added deals.raw_capture_id (migration 0003) to link deals to captures for the
  review UI. Additive nullable FK, no stored data lost.
- Mutations exposed as a POST API (not only server actions) so persistence could
  be verified headlessly and so the client is a thin caller.

### Stop / ask
- Fixtures produce 19 pending deals; the CHECK asks for 20 approvals. Seeded 19
  from fixtures as instructed and flagged the one-deal gap (see DEFERRED.md and
  the handoff) rather than fabricating a 20th. Not a blocker for the queue
  itself. Operator will ingest the 20th; no padding.

### Addendum (2026-08-05): confidence bands and holdout policy
Two operator questions, both actioned while holding at phase 5:
- The confidence assertion in tests/compare.py only tested the low band and left
  013 (high side of 0.6) and the 0.8 threshold untested. Strengthened
  _confidence_ok to bracket 0.6 in BOTH directions (exp < 0.6 => act < 0.6;
  exp >= 0.6 => act >= 0.6), so 013 and 017 now bracket the boundary for real.
  Added test_auto_approve_threshold, a deterministic unit test of the 0.8
  auto-approve line (0.80/website approved, 0.79/website pending, 0.80/fixture
  pending). The model's confidence is bimodal and does not reproduce the
  fixtures' mid-band, so a 0.6-0.8 band is not asserted on model output; the
  0.8 logic is tested directly instead. Suite: 44 passed.
- Added tests/fixtures/HOLDOUT.md: the prompt was iterated against the same 30
  fixtures it is scored on, so 30/30 is fit not generalisation. The first 10
  real phase-6 captions must be hand-labelled into tests/fixtures/holdout/
  before the prompt is tuned again. The existing 30 are not to be tuned against
  further.

### Addendum (2026-08-05): out-of-sample capture 31, schema gaps

Real capture 31 (YOMG, self-serve froyo per 100g) exposed gaps that would block
phase 6. Fixed while holding at phase 5.

- Migration 0004 (additive): deals.unit_basis text CHECK ('flat','per_100g',
  'per_kg') and deals.store_hint_raw text. store_hint_raw stores the extracted
  hint verbatim regardless of fuzzy resolution, so the queue can tell "no
  location" (null) from "location named but unresolved" (non-null, store_id
  null). stores is empty until phase 9 so every hint resolves to null now.
- Prompt: unit_basis required whenever a price is stated, default flat, per_100g
  or per_kg for per-weight; a stated basis with no number sets the basis and
  leaves discount_value null; never null a stated price for unclear basis.
  Channel exclusions now populate the remaining permitted channels ("in store
  only, not on app/delivery" -> [dine_in, takeaway]) instead of [].
- Schema/postprocess: Deal.unit_basis added to the responseSchema; build_deal_row
  writes unit_basis and store_hint_raw.
- Regression fixture 031_instore_only_per_100g added to captions/ covering both
  new rules (per_100g price plus channel exclusion). compare.py checks unit_basis
  only for fixtures that declare it, so the original 30 (which omit it) are
  unaffected. NEGATIVES now derived from empty expected JSON, not an id range.
- Suite: 45 passed. The channels edit briefly regressed fixture 007 (['app'] ->
  []); fixed in the prompt (not the fixture) by clarifying "download the app to
  join" -> ["app"]. No fixture conflicts with the unit_basis rule.
- Confidence: retracted the bimodal claim (DEFERRED.md). Capture 31 returned 0.5
  (old prompt) then 0.9 (new prompt); confidence is uncalibrated. No logic
  assumes bimodality; the 0.8 auto-approve test stays.

Capture 31 re-extracted (deal id 78): fixed_price, unit_basis per_100g,
channels [dine_in, takeaway], valid 2026-08-05, discount_value NULL because the
stored caption has no price number (no '$', no digit, no image). Hand-labelled
into tests/fixtures/holdout/031_yomg_per_100g as the first holdout item, with
the missing-price defect flagged. See DEFERRED.md / HOLDOUT.md.

### Decision requested (item 4): @mention -> chain_id
Reading, not implemented (awaiting confirmation). Recommendation: YES, resolve
an @mention to chain_id, but only on an EXACT match of the handle (minus the @,
case-insensitive) to a chains.instagram_handle. @yomgburgers matches YOMG ->
chain_id set; @sweettooth.example (customer, fixture 030) matches nothing -> null.
This does not contradict the "hashtags do not feed store_hint" rule, because:
(1) different field: store_hint is a fuzzy LOCATION guess, chain_id is a BRAND
identity; (2) different reliability: a handle is a structured key that maps
exactly to chains.instagram_handle, whereas a hashtag is free-form marketing
text. It only ever attaches to a known chain, never invents one. Caveat: a
caption could tag a chain it is not actually from ("we love @yomgburgers");
rare, and still a defensible attribution. Not built until you confirm.

### Addendum (2026-08-05): manual-path hardening and chain resolution

Root cause of capture 31's missing price confirmed: a shell quoting bug, not a
data problem. --text was passed in double quotes, so zsh expanded $3 to an empty
positional parameter; the leftover double space was the signature. Actioned:
- ingest/manual.py: added --stdin (immune to shell expansion, now the documented
  default for text) and --file PATH. --text still works but warns loudly to
  stderr on expansion signatures (a run of 2+ spaces, or "per 100g" with no
  preceding digit); it warns, does not block. Verified: `--text "$3 per 100g"`
  delivers " per 100g" to Python, and the warning fires; --stdin/--file bypass
  the shell entirely.
- DEFERRED.md records the defect and that phase 6 scrapers are unaffected (they
  build RawCaptures in Python, never through a shell).
- Implemented @mention -> chain_id (postprocess.resolve_chain_from_text): exact,
  case-insensitive match against chains.instagram_handle, never fuzzy, never
  creates a chain; applied in build_deal_row when no store matched. Unit tests
  cover a repost mentioning a known chain handle (attaches) and an unknown handle
  (null), plus case-insensitivity and no partial match. chain_id is a
  post-processing output, not part of extractor .expected.json, so it is tested
  at the postprocess layer like resolve_store and the auto-approve threshold, not
  as a caption fixture. Suite: 47 passed.
- Deleted raw_capture 31 and its deal for re-ingestion via stdin. Review work
  (18 approved, 1 rejected) untouched. holdout/031 NOT yet updated to
  discount_value 3: waiting on your re-ingest confirmation, per your instruction.

---

## Phase 6: website scraper (2026-08-05)

### Decision applied first: auto-approve rule
build_deal_row now auto-approves only when source_type == 'website' AND
confidence >= 0.8 AND the extraction is complete (no null in deal_type, headline,
and either discount_value or a non-numeric deal_type: bogo/freebie/loyalty). A
partial extraction never auto-approves. confidence stays numeric. Covered by
test_auto_approve_requires_complete_extraction.

### Built
- ingest/scrapers/http.py: PoliteFetcher. Respects robots.txt, identifiable
  User-Agent, one request per host at a time, >= 5s between requests to a host.
- ingest/scrapers/website.py: WebsiteScraper(Scraper), fully config-driven from
  config/scrapers.yaml (nothing chain-specific hardcoded). Returns list of
  RawCapture; writes raw_captures only, never deals. Text pages -> one capture
  per selected block; image_only pages -> fetches the promo image, saves under
  media/promo_images/, sets image_path.
- ingest/scrape.py: CLI, logs per-source outcome and inserts captures.
- config/scrapers.yaml: all 17 chains classified after probing. scrapeable:
  Yo-Chi (section.join-section), Yo-Bar (.standard-blog-content). image_only:
  YOMG (img.attachment-full). blocked: Just Crave It (domain did not resolve /
  blocks fetch). none: the other 13. Selectors only on the scraped ones.
- ops/crontab: daily 03:15 scrape then extract.

### CHECK (manual run; overnight is yours to confirm)
```
scrape.source Yo-Chi        scrapeable  http 200  captures 1
scrape.source Yo-Bar        scrapeable  http 200  captures 4
scrape.source YOMG          image_only  http 200  captures 1 (image saved)
scrape.source Just Crave It blocked                captures 0 (not scraped)
... 13 chains status none, captures 0
scrape.done captures 6 inserted 6 duplicates 0
```
6 website raw_captures written (ids 33-38), all unprocessed. Then extract (cron
step 2) produced 6 deals: Yo-Chi loyalty; Yo-Bar 30% birthday (its 3 store-opening
posts correctly yielded nothing); YOMG image yielded 4 deals read straight from
the promo graphic. The image inline path is now exercised end to end.

### Two findings (flagged, not acted on)
- The CHECK says the run "leaves new pending items", but the auto-approve rule
  sends confident+complete website deals to approved, not pending. All 6 here
  auto-approved (0.95, complete). The scraper does leave new unprocessed
  raw_captures ("pending items" at the capture level); pending DEALS from
  website only arise from low-confidence or incomplete extractions.
  CONFIRMED (2026-08-05): "new pending items" means new unprocessed raw_captures.
  The overnight scrape leaves fresh raw_captures with processed=false; whether the
  downstream extract auto-approves or leaves pending deals is a separate, expected
  outcome of the auto-approve rule.
- YOMG's offers image yielded burger deals ($8 Cheesy Burgers, etc.), accurate
  to the image but off-domain for a froyo tracker (YOMG is a burger business
  with a froyo counter). Not a prompt bug, the extraction is correct; a product
  scoping question. Prompt NOT tuned (HOLDOUT constraint).

### HOLDOUT constraint honoured
Did not tune extract_deal.txt. The scraped captures are the first real phase-6
captions; per HOLDOUT.md they are candidates for the hand-labelled holdout
before any future prompt tuning.

### Requirement audit (SPEC phase 6 + ingestion architecture)
- config-driven from scrapers.yaml (url + CSS selectors per chain), nothing
  hardcoded: PASS
- shares the Scraper interface returning list[RawCapture]: PASS
- writes raw_captures only, never deals: PASS
- each chain classified scrapeable/image_only/blocked/none, selectors only for
  scraped: PASS
- robots.txt respected, 5s per-host, identifiable UA, one request per domain at
  a time: PASS
- image promo captured with image_path rather than skipped: PASS (YOMG)
- daily cron built: PASS (ops/crontab); overnight run is yours to confirm

---

## Phase 7: public dashboard (2026-08-05)

### Built
- web/app/page.tsx: the public dashboard at / (previously a redirect to /review).
  Shows active (approved) deals, default sort last_verified desc nulls last.
  Filters by chain, deal_type, day of week and suburb (GET form, server-rendered).
  A deal not verified in 14 days renders greyed with its last-verified date
  visible, not hidden.
- unit_basis is shown in the card itself: the price reads "$3 / 100g" for
  per_100g (or "/ kg"), plus an explicit "priced by weight (per_100g)" badge, so
  a weight price can never be mistaken for a flat price. Not a tooltip.
- web/lib/deals.ts: getActiveDeals(filters) with parameterised SQL, and
  getFilterOptions(). Day filter matches deals restricted to that weekday OR with
  no day restriction (available any day).
- ingest/postprocess.py: auto-approved deals now get last_verified = now() at
  insert (a fresh scrape is a verification), so they are not instantly stale.
  Backfilled the 6 existing auto-approved website deals.

### CHECK (dashboard renders correctly)
Verified against a running server with a throwaway stale per_100g deal:
```
GET / -> HTTP 200
price shows "$3 / 100g"                       (unit_basis visible in card)
"priced by weight (per_100g)" badge present
20-day-old deal: greyed styling + "· stale" + date shown (not hidden)
filters chain/deal_type/day/suburb all present
/?deal_type=loyalty -> 3 loyalty deals (incl Chi Club)
/?day=1 -> day filter narrows the set
```
Throwaway deleted afterward. pytest: 48 passed.

### Requirement audit (SPEC phase 7 + your unit_basis instruction)
- / with filters: PASS (chain, deal_type, day of week, suburb)
- active approved deals, default sort last_verified desc: PASS
- not verified in 14 days -> greyed with date visible rather than hidden: PASS
- unit_basis visible in the deal card, not a tooltip: PASS

### Limitation (deferred, not a bug)
suburb filter and chain attribution are thin right now: store_id is null until
phase 9 seeds stores, so suburb is null on every deal and many deals have
chain_id null. The filter controls work; they just have little to bind to until
phase 9. Recorded in DEFERRED.md.

---

## Phase 8: jobs (2026-08-05)

### Built
- ingest/expire_deals.py: nightly. Sets status 'expired' for approved deals with
  valid_to < current_date. Open-ended deals (valid_to null, e.g. loyalty) never
  expire on date. Applied to approved only; pending stays for the operator.
- ingest/reverify.py: weekly. Re-fetches the configured sources with the polite
  scraper (no model call, no writes to raw_captures/deals) and checks whether
  each approved deal's original raw_capture content_hash is still carried. If so,
  bumps last_verified = now(); if not, leaves it unbumped so it ages to stale
  under the dashboard's 14-day rule. partition() split out and unit-tested.
- ops/crontab: expire_deals nightly at 03:30, reverify weekly Monday 04:00.

### CHECK (no stated CHECK in SPEC; verified by running)
```
expire_deals: 7 approved past-valid_to deals -> expired
  statuses after: approved 17, expired 7, rejected 1, pending 1
  re-run idempotent: expired 0
reverify: re-fetched 3 sources (21s wall, confirming the >=5s per-host throttle),
  checked 5 approved website deals, bumped 5, stale 0, no model call
  last_verified moved to 2026-08-05 on all 5
pytest: 49 passed (test_reverify_partition covers bumped and stale)
```

### Requirement audit (SPEC phase 8 + your reverify constraint)
- expire_deals nightly, valid_to < today becomes expired: PASS
- reverify weekly, refetch source_url for approved deals, bump last_verified or
  flag stale: PASS
- reverify must NOT re-extract, only confirm source still carries and bump
  last_verified: PASS (re-fetch + content_hash comparison; zero Gemini calls)

### Decision
"flag stale" is implemented as "do not bump": a deal whose source no longer
carries it keeps its old last_verified and greys out under the existing 14-day
staleness rule, rather than adding a new status or column. No schema change.

Stopped at the end of phase 8. Phase 9 not started.

---

## Pre-phase-9 (2026-08-05): holdout correction, phase-6 reading, deal category

Requested before the phase 9 vs user-submission decision. Held after; phase 9
not started.

### Holdout 031 corrected
The capture was re-ingested via stdin with the complete caption (raw_capture 32,
"$3 per 100 grams" present twice). Updated tests/fixtures/holdout/031_yomg_per_100g
to the corrected caption and expected output: discount_value 3, unit_basis
per_100g, category froyo, channels [dine_in, takeaway], valid_from and valid_to
2026-08-05, store_hint null, chain_id 4 (from the @yomgburgers mention). chain_id
is a post-processing result recorded here because the holdout documents the whole
pipeline. HOLDOUT.md DEFECT note removed.

### Phase 6 CHECK reading confirmed
"new pending items" means new unprocessed raw_captures. Recorded in the phase 6
section above.

### deals.category (migration 0005)
- 0005 adds deals.category text CHECK ('froyo','adjacent','other' or null).
- Prompt sets category for every deal: froyo for frozen yoghurt/acai, adjacent
  for other desserts, other for anything else including burgers. Explicit
  instruction not to drop non-froyo deals, only classify them.
- schema.py Category enum (required on Deal); postprocess writes it; compare.py
  checks category only when a fixture declares it (the 30 are unaffected).
- Backfill: update all to 'froyo', then 'other' where headline matches
  burger/lunch-combo. Result 23 froyo, 3 other (the YOMG Veg/Cheesy Burgers and
  Lunch Combos; "Take Home Froyo Tubs" stayed froyo).
- Dashboard defaults to froyo (searchParams.category defaults 'froyo'); a category
  filter widens to adjacent, other, or all. Verified: default view 14 froyo deals
  (burgers hidden), ?category=other 3 burger deals, ?category=all 17.

### Verification
- pytest 49 passed (category prompt change did not disturb the 30; one transient
  API failure on 024 self-healed on retry and cached).
- Classification spot-check: burger->other, cake/waffles->adjacent, coffee->other,
  acai->froyo, all froyo fixtures->froyo.

### HOLDOUT note
This run modified extract_deal.txt (added the category field) under your explicit
instruction, which supersedes the standing "do not tune" constraint. The change
is additive (a new field and its rule); existing extraction rules were untouched
and the 30 fixtures stay green.

---

## Phase 6b: user submission (2026-08-05)

### Transient fixture-024 failure resolved first (committed 48018a2)
Determined it was a Gemini 429 rate limit (RESOURCE_EXHAUSTED) on
gemini-flash-latest during a cold re-extraction, not network and not
nondeterminism (output was always structurally valid). Proven by adding
gemini.rate_limited logging and reproducing: 4 batches, 20 api_calls (backoff
retries), explicit 429 events, all recovering via backoff + flash-lite fallback.
Under heavier pressure one caption exhausts its retries -> None (unprocessed) ->
red; an isolated re-run is under quota -> green. Extractor now logs swallowed
errors; backoff widened to [2,5,15]. Warm-cache runs make no API calls.

### Built
- ingest/images.py: sanitize_image decodes (jpg/png/heic via pillow-heif), bakes
  EXIF orientation, re-encodes WITHOUT metadata (strips EXIF incl GPS), HEIC->JPEG.
- ingest/submit.py: sanitizes then writes through the SAME path as manual
  ingestion (ManualScraper + insert_captures) with source_type 'user_submission'.
- web /submit page + SubmitForm (client) + /api/submit route: validates jpg/png/
  heic by magic bytes, caps at 10MB, in-process IP rate limit (5/10min), spawns
  ingest.submit, returns a confirmation (not a result). Extraction runs on the
  schedule, not on upload. Dashboard links to /submit.
- Verified auto-approve never fires on user_submission (rule already requires
  'website'; test_user_submission_never_auto_approves added, rule unchanged).

### Bug found and fixed (INSERT_DEAL)
The first real DB-path insert since phase 7 crashed with AmbiguousParameter: the
last_verified `case when %(status)s='approved'` reused the status param in two
type contexts (text vs deal_status). Fixed with a separate %(auto_approved)s
boolean. Added tests/test_submission.py::test_insert_deal_executes (runs
INSERT_DEAL against the real schema, rolled back) so this class of bug can no
longer reach runtime.

### CHECK: submit a promo-sign photo through the web form
Submitted a generated promo sign ("$5 froyo cups / Tuesdays / Glen Waverley")
carrying GPS EXIF, through POST /api/submit:
```
response: {"ok":true,"message":"Thanks! Your submission is pending review."}
raw_capture 40: source_type user_submission, processed=false
stored image: EXIF fully stripped, GPS empty
extract -> deal 87: status pending (NOT auto-approved), fixed_price $5,
           category froyo, days [2], store_hint "Glen Waverley"
/review: queue includes the submission with its image; /api/image -> HTTP 200
approve -> dashboard (default froyo) shows it: "Glen Waverley" visible
```
All CHECK steps pass. Deal 87 (a test submission from a generated image) is left
in place as the visible artifact; delete at will.

### Requirement audit (phase 6b)
- public /submit, no auth, photo + optional text + optional store: PASS
- writes raw_captures with source_type user_submission + image_path, reusing the
  manual path: PASS (ingest.submit -> ManualScraper + insert_captures)
- auto-approve never fires on submissions (verified, not changed): PASS
- accept jpg/png/heic, reject else, cap 10MB: PASS (magic-byte sniff + size)
- strip EXIF incl GPS: PASS (verified stripped)
- rate limit by IP, in-process: PASS (5/10min)
- no submitter identity stored: PASS (no email/account fields)
- extractor runs on schedule not on upload; submitter gets confirmation: PASS
- /review shows the submitted image: PASS

Phase 9 remains deferred. Held after phase 6b.

---

## Write-path SQL coverage audit (2026-08-05)

Two runtime bugs (reverify status reuse; phase-7 INSERT_DEAL last_verified
ambiguity) shared a root cause: no test executed a real write. Audited every
write path and added rolled-back integration tests (skip without a DB) for the
uncovered ones.

| Write path | SQL location | Test (executes real SQL) |
|---|---|---|
| INSERT_DEAL | postprocess.py | test_writes.py::test_insert_deal_executes |
| expire | expire_deals.py (EXPIRE_SQL) | test_writes.py::test_expire_sql_executes |
| reverify last_verified bump | reverify.py (BUMP_SQL) | test_writes.py::test_reverify_bump_sql_executes |
| approve | web/lib/mutations.ts (APPROVE_SQL) | web/tests/mutations.test.ts |
| reject | web/lib/mutations.ts (REJECT_SQL) | web/tests/mutations.test.ts |
| edit-and-approve | web/lib/mutations.ts (EDIT_SQL) | web/tests/mutations.test.ts |
| save | web/lib/mutations.ts (EDIT_SQL, same stmt) | web/tests/mutations.test.ts |

- Python SQL extracted to module constants (EXPIRE_SQL, BUMP_SQL) and executed
  in a rolled-back db_conn fixture (conftest.py). TS review SQL extracted to
  web/lib/mutations.ts so the route and the test use one source of truth; the
  test runs each statement against the schema in a rolled-back transaction via
  node --test (Node 26 native TS). edit-and-approve and save share EDIT_SQL; the
  test exercises both param combinations.
- Result: pytest 55 passed; web `npm test` 1 passed; `next build` green.
- Also deleted the phase-6b CHECK artifact (deal 87 + raw_capture 40 + image).

Phase 9 remains deferred. Held.

---

## Phase 6c: admin auth + queue triage (2026-08-05)

### Auth
- web/lib/auth.ts: single ADMIN_PASSWORD (env). Login verifies it timing-safe and
  sets an httpOnly, secure (prod), sameSite=lax session cookie whose value is an
  HMAC of the password (no password stored, unforgeable). isAuthed() validates
  the cookie server-side timing-safe.
- /login page + /api/login + /api/logout. /review redirects to /login when
  unauthenticated; a Log out control clears the session.
- Every mutation validated server-side: /api/deals/[id] and /api/image return 401
  without a valid session. /submit and / stay public. No user accounts.

### Triage (rule unchanged; submissions still never auto-approve)
- Queue sort: user_submission first, then lowest confidence first within source
  (getPendingDeals ORDER BY).
- Each item flagged with why it is pending, several possible: user-submitted,
  low confidence (<0.8), incomplete extraction (null deal_type/headline, or null
  price where a numeric deal_type expects one).
- Items below 0.8 render visually distinct: a loud "needs a careful look" banner
  and an amber ring around the item, so a rhythm-approve is interrupted.
- Source image enlarged (max-h 36rem, legible) and click-to-view-full-size, since
  on a low-confidence image submission the photo is the evidence.

### CHECK (auth + triage, verified against a running server)
```
AUTH
  POST /api/deals/79 (no session)   -> 401
  GET  /review       (no session)   -> 307 redirect to /login
  GET  /api/image    (no session)   -> 401
  GET  /  and  /submit (no session) -> 200 (public)
  POST /api/login wrong password    -> 401
  POST /api/login correct           -> 200, Set-Cookie httpOnly + secure
  GET  /review with session         -> 200
  POST /api/deals/101 with session  -> 200 (mutation works)
TRIAGE
  queue first card = the user_submission item (sort)
  flags shown: user-submitted, low confidence (0.4), incomplete extraction
  loud banner + amber ring on the <0.8 item
  image: legible (max-h 36rem) + click to view full size
```
Throwaway triage items removed afterward. Regression: pytest 55, web npm test
passed, next build green.

Phase 9 remains deferred. Held after phase 6c.

---

## Auth hardening (2026-08-05)

1. Session expiry and revocation. The session cookie is now `<iat>.<hmac>` signed
   with a SEPARATE SESSION_SECRET (not derived from the password). The server
   verifies the MAC and rejects sessions older than 7 days; rotating
   SESSION_SECRET revokes all sessions independently of the password. Pure token
   logic in web/lib/session.ts, unit-tested (web/tests/auth.test.ts: fresh,
   >7-day expiry, tampered MAC, re-dated iat, future-dated, garbage). Live CHECK:
   fresh login -> authed POST 200; a validly-signed but 8-day-old cookie -> 401;
   tampered -> 401; freshly crafted -> 200. web npm test 7 passed; build green.
2. /api/image on the public dashboard: investigated, not implemented (awaiting
   confirmation). The public dashboard renders NO image (0 /api/image refs, 0
   <img> in the HTML; getActiveDeals does not select image_path), so there is no
   broken image today. Reading: keep public cards image-free rather than serving
   approved-submission images unauthenticated, because submission photos are
   untrusted pixels (faces, plates, location scenery) that EXIF stripping does
   not remove. If images on public cards are wanted, gate to website-sourced or a
   per-image publishable flag, not a blanket unauth allow. See handoff.

Phase 9 remains deferred. Held.

---

## Decision: approved images stay non-public (confirmed 2026-08-05)

Confirmed by the owner. Recorded here so it is not relitigated.

Decision: the public dashboard (/) shows deal fields only, never the source
image. Source images are served only to authenticated reviewers via /api/image;
approving a deal does NOT make its image public.

Why:
- Approval is of the DEAL (extracted price, dates, terms), not of the image for
  publication. The two are separate acts.
- User-submitted photos are untrusted pixels. They can contain incidental
  private content (faces, bystanders, licence plates, house numbers,
  location-revealing surroundings). EXIF/GPS stripping removes metadata, not what
  is visible in the frame, so publishing the image publishes whatever was shot.
- The structured deal is the public product and is sufficient for the dashboard.
  The image is reviewer evidence, not a public asset.
- Current state already matches this: the dashboard requests no image (0
  /api/image refs, 0 <img> in the HTML), so there is nothing to change.

If public images are ever wanted, see DEFERRED.md for the only acceptable
mechanism (a per-image publishable flag set at review time), never a blanket
unauthenticated /api/image.

---

## Phase 6d: Instagram ingestion (2026-08-06)

Instagram captures come from a **private ingestion source that is not part of this
repository.** `ingest/scrapers/instagram.py` is the interface stub it satisfies;
`ingest/scrape_instagram.py` is the public runner. In this checkout a run raises
`NotImplementedError`, writes nothing and exits non-zero.

The public half is here and is what the rest of the pipeline depends on:

- Writes to `raw_captures` only. Extraction is unchanged and runs on its own
  schedule, so the two-stage split holds for this source as for the website
  scraper.
- Monitored accounts are the 16 chains with a non-null `instagram_handle` in
  `config/chains.yaml` (not 18; Vanilla Dessert Bar and one other are null).
  Everything else is ignored.
- New table `instagram_seen(account pk, last_shortcode, last_seen_at)` (migration
  0006) is the per-account high-water mark, so a run only picks up what is new.
- Captures dedupe on `content_hash` at insert.
- Instagram never auto-approves (the `source_type` gate), so every Instagram deal
  is reviewed by hand.

A missing capture source is a **failure**, not an empty success: the runner logs
`instagram.source_unavailable` and returns non-zero rather than reporting a clean
run that found no posts. A source that silently returns nothing must never read as
healthy.

Held.

---

## Product decision: source priority (2026-08-06)

Recorded so downstream trade-offs are judged against it.

**Instagram is the primary ingestion source. Website scraping is secondary and
covers 2 chains (Yo-Chi, Yo-Bar). /submit is a beta feature, not relied upon.**

Consequences (see DEFERRED.md for the adjusted entries):

- **a04 image-miss downgraded to a known limitation.** The ablation holdout showed
  the extractor can miss a non-priced freebie in a captionless image (a04). That
  failure lands on the /submit path, which is now beta and not relied upon; the
  primary source (Instagram) states offers in captions, so the gap does not touch
  primary ingestion. It is no longer "the strongest argument for a prompt fix" -
  it is a recorded limitation (non-priced freebies in captionless images may be
  missed). The a01-a04 ablation fixtures stay as the validation set if it is ever
  fixed, but nothing schedules that fix. Prompt tuning stays on hold.

- **Census finding now applies to the primary source.** These accounts state
  offers in captions (images redundant) - established as load-bearing across all
  90 captures. Because Instagram is primary, this strengthens the text-first-pass
  cost option (option 1). Still NOT building it: the cold-start reframe stands
  (steady-state volume is small; revisit only above ~20 image calls/run).

- **Dashboard coverage must be honest.** The dashboard covers what 16 Instagram
  accounts and 2 websites publish, not all Melbourne froyo deals. The public copy
  should reflect that rather than imply exhaustive coverage. Logged in DEFERRED.md
  as a copy change; no code change in this pass.

---

## Backfill provenance: source_handle / via_handle / chain_id (2026-08-06)

Recorded because these were one-off data mutations, not migrations, and the
method matters for auditability.

**source_handle (80 monitored captures).** The proposed id-ordering backfill was
verified and REJECTED as the source of truth: the 90 captures are not a clean
15x6 profile scrape (10 are third-party tagged/collab posts, per-visit own-post
share varies). Instead, backfilled zero-request from the author handle already
embedded in every caption's content_text ("<handle> on <Month> <day>, <year>:"),
parsed 90/90. 80 captures authored by a monitored account got source_handle set
to that handle; the 10 third-party captures were left source_handle NULL.

**via_handle (10 third-party captures).** Backfilled from the positional mapping
(instagram ids are contiguous 42-131, chunk-by-6 into the recorded profile order),
which is safe here because it records which profile visit SURFACED the post, not
who wrote it. Verified: the positional via_handle for all 10 matches the account
each post references/@tags. (The third-party authors are individuals' and other
businesses' accounts, so they are not named here.) Going forward the scraper's
author-match guard sets via_handle live.

**chain_id (19 deals).** Re-resolved from the backfilled handles via
build_deal_row's source_handle -> via_handle -> @mention order. Went from 1 deal
with a chain to 19/19. All 19 are authored by monitored accounts, so all resolve
via source_handle; 0 deals came from third-party captures.

Code: author-match guard added in the capture source (keep third-party posts,
attribute honestly); migration 0008 adds via_handle; 3-tier chain resolution in
build_deal_row. Displacement tradeoff recorded in DEFERRED.md.

---

## Auto-merge duplicate approved deals (2026-08-06)

Nightly `ingest.merge_dupes` supersedes (never deletes) duplicate approved deals:
keeps the earliest-created (lowest-id) canonical and sets `deals.superseded_by`
(migration 0009) on the rest. Strict gate (`ingest.dedupe.merge_candidate`): same
non-null chain_id, same deal_type, equal non-null discount_value, overlapping
window, headline similarity >= SIM_VALUED, and never two offers from the same post.
Null-value freebies are NEVER auto-merged (the "first 30" vs "first 300" over-flag
case) - left for /review. Does NOT gate on model confidence (all Instagram deals
score 0.9-1.0, so 0.85 filters nothing). Every merge logs structured output
(canonical, superseded, score). Dry-run by default; cron runs `--commit` at 03:35
(after expire).

Dashboard excludes any deal with superseded_by set; /review lists superseded deals
under a collapsed filter with an Undo (the `unsupersede` action clears the column).

Manual cleanup applied this session: superseded **#120 -> canonical #119**
(identical "50% off Frozen Yogurt", blu spoon, same window, score 1.000) - the only
pair on the current approved set meeting the strict gate.

`ingest/dedupe.py` is a Python port of `web/lib/dedupe.ts`; similarity and
thresholds verified identical (parity test). Both must stay in sync.

---

## Merge job widened to pending; #114 restored (2026-08-08)

The auto-merge job now runs on pending as well as approved deals, so the review
queue shows one canonical row per promo instead of duplicate copies to adjudicate
by hand (the cause of the earlier inconsistent housekeeping - approving 2 and
rejecting 2 of the same "50% off"). Two refinements: (1) canonical = approved deal
in a group if any, else earliest-id pending, so a pending never demotes a vetted
approved deal; (2) getPendingDeals hides superseded pendings (they stay visible
under the /review superseded filter). Merging never changes status. Earliest-id
canonical caveat and the most-complete-extraction switch recorded in DEFERRED.md.

Data: restored deal #114 (yobar "first 300 free bowls") from rejected to approved
- both #114 and #115 had been rejected, leaving that promo with no live
representative (the lose-a-deal-silently case). #115 stays rejected.

Dry-run over the current pool (18 live approved, 0 pending): 0 pairs - nothing to
merge now; the job will dedup pending duplicates as new captures arrive.

---

## Submission path, freshness honesty, portable media, deployment (2026-08-09)

### Capture 162: first user_submission through the extractor
Produced deal #157 (fixed_price, $5, unit_basis flat, Wednesdays, recurring,
confidence 0.95), correctly pending. Nothing in post-processing assumed an absent
field: source_handle/via_handle/source_url all read through .get() and degrade.
Three real problems surfaced, all now fixed except where noted.

### Problem 1: the submitter's shop name never reached the deal
The route concatenated it as "Store: X" into content_text, and the prompt is
right that a labelled form field is not caption prose, so the model declined to
read it as a store_hint. Fixed on the submission side, prompt untouched:
- migration 0010 adds `raw_captures.submitted_store`
- RawCapture, insert_captures, ManualScraper, ingest.submit --store, and the
  /api/submit route all carry it structurally
- `build_deal_row` prefers the typed value over the model's store_hint (the
  submitter physically stood there; on a submission the model's hint can only
  derive from that same person's free text)
- getPendingDeals + /review render it, or the reviewer would stop seeing it

Deliberately NOT done: fuzzy chain-name matching from the typed store. It would
invent attribution; phase 9's stores table is the real fix.

### content_hash collision (found while fixing problem 1)
`content_hash` prefers text whenever text is non-empty, so a submission's image
bytes were ignored the moment the submitter typed anything: two different photos
with the same typed words collided and the second was silently discarded by
`on conflict do nothing`. Real data loss. Added `combine=True`, used only by the
submission path, hashing normalised text plus the image digest. The shared path
is unchanged so Instagram still dedupes reposts by caption.

### Problem 2: "not checked" was a lie for anything unre-checkable
reverify only touches deals with a source_url, so a user submission can never be
re-verified and decayed into the stale band permanently, described as neglected.
Rejected a longer window (delays the same false signal) and never dimming (a
six-month-old sighting at full brightness is a different lie). Instead:
- the predicate is `source_url is not null`, exactly what reverify.py keys on
- rows read "checked <date>" when re-checkable and "seen <date>" when not
- band 3 retitled "Unconfirmed for two weeks"; its note says the seen ones
  cannot be re-checked at all and will not move back up
- staleness and sort now measure from the evidence date, not from approval

The third part matters most: for a sighting, last_verified is only when the
operator got round to approving it, and the review lag is unbounded, so the old
behaviour overstated freshness by an arbitrary amount. getActiveDeals now joins
raw_captures for `captured_at` (Melbourne time) and selects
`(d.source_url is not null) as recheckable`. The URL itself is never selected:
public surface, boolean is enough.

### Problem 3: dead basisLabel branches removed
deals.unit_basis is ('flat','per_100g','per_kg') per migration 0004. The each /
per_serve branches came from SPEC's prices.unit, a different table. 'flat' falls
through to null and renders bare, which deal #157 confirms.

### Privacy copy on /submit corrected
The rate limiter keys on the raw client IP (first hop of x-forwarded-for, else
"local") as a Map key in process memory. Never logged, never written to the DB,
never attached to the capture, but the key is not evicted when its timestamps
expire, so it lives until restart. "Nothing here identifies you" was therefore
too strong. Now states the exception explicitly rather than dropping the claim,
since the EXIF stripping is genuinely worth saying. Not done: hashing the IP and
evicting empty keys, both one-liners, left as a decision.

### image_path is now relative to a configurable media root
It was absolute and Mac-specific, so it broke on any other machine. Added
ingest/media.py (MEDIA_ROOT, default <repo>/media) plus web/lib/media.ts, and
migration 0011 rewrites existing rows with a machine-agnostic pattern (strips up
to the last "/media/"). All three writers were affected, not just submissions:
the Instagram and website scrapers also hardcoded their own dirs and ignored
MEDIA_ROOT. Readers handle legacy absolute paths, and /api/image gained a
containment check so a stored path cannot escape the root.

### Deployment target corrected
The Binary Lane VPS is cancelled. Plan is Vercel plus Neon, scrapers staying on
the Mac (ingestion has to run there). Every "the VPS" assertion outside this log now
reads "a cloud host". README gained a Deployment section recording that Vercel's
ephemeral filesystem makes local media storage unworkable, and two unresolved
consequences: /api/submit spawns the repo's Python venv (which does not exist in
a Vercel function at all) and /api/image reads files that live on the Mac.

## 2026-08-15 — deal scope: the dashboard published deals for other cities

### The failure
Some monitored chains are national, so their Instagram announces deals for
stores we do not serve. A Yo-Bar Canberra promo extracted identically to a
Melbourne one, and nothing downstream could tell them apart.

**Three deals went live on the public dashboard as Melbourne deals when they were
not**: #114 and #156 (Yo-Bar's Canberra Centre grand opening, "free bowl for the
first 300 customers", 8 Aug) and #123 (Yo Way). All three were approved, carried
`last_verified`, and rendered on `/` under "Available today". #114 is the deal
the whole duplicate reconciliation earlier that day was about; nobody noticed it
was Canberra.

This is the first time the tracker published something FALSE rather than
something incomplete. Every honesty problem before it was an overstatement of
confidence — freshness overstated, a basis omitted, a store implied. This was a
plain untruth: the page said a deal was available in Melbourne and it was not.
Recording it because the distinction is the product's whole premise, and because
it took eleven days and an unrelated question to notice.

Scale at the time: 12 of Yo-Bar's 21 captures name another city. Two deals
(#177, #178) were sitting in the review queue with `store_hint_raw` =
"Coolangatta", one approval away from repeating it.

### The evidence was already there and was being discarded
`store_hint_raw` held "Canberra Centre" and "Coolangatta" the whole time. It is
passed to `resolve_store`, which matches against the `stores` table — and that
table has 0 rows until Phase 9, so every lookup returned `(None, None)` and the
location was dropped. `store_hint_raw` was a write-only column: never read,
never shown in /review, never used. The extractor had been doing its job.

### The shape: capture and classify, like category
`deals.scope` in ('melbourne', 'other', 'unknown'), migration 0012, defaulting to
'unknown' so a writer that forgets the column cannot produce a Melbourne-looking
deal.
- `other` is never shown on `/` at all, not even under the Everything toggle.
  Everything widens `category`, a different axis: a labelled non-froyo deal is
  still something you can walk to; a Canberra one is not.
- `unknown` IS shown, in its own band, "City not stated". Hiding it would drop
  the largest chains entirely and "nobody misses a deal" is half the point. Same
  principle as the stale band: state the gap, do not hide the row. Deals in it
  are never counted as available today, so the headline claim stays a Melbourne
  claim.

### The extractor never decides scope
It emits `stated_location` (melbourne / other / unclear / none) — what the
caption prose said, nothing more. `derive_scope` in postprocess combines that
with the chain's `footprint` from config/chains.yaml.

This split exists because the hard case is not answerable from the caption. Most
posts name no city, and what that silence means depends on the business: for blu
spoon (one shop, Port Melbourne) it means Melbourne; for Yo-Chi (70 stores
nationally) it means genuinely unknown. Same silence, opposite answers. Asking
the model to interpret it would be asking it to guess, so it is never asked.
The rule is: usable evidence wins, otherwise the chain decides.

`unclear` falls through to the chain exactly like `none`. A place that cannot be
located carries no more information than no place at all — and Yokli's own suburb
is Richmond, which also exists in Sydney, so a one-city chain would otherwise
have every deal demoted.

A missing or 'unknown' footprint behaves as 'national'. Being unsure about a
chain must never publish a Melbourne claim.

### footprint, curated by hand
17 chains: 12 melbourne_only, 4 national (Yo-Chi, Yo-Bar, Yo Way, YOMG), 1
unknown (Yo-Art — every venue found is Melbourne, the operator believes it is
national, unresolved and therefore left on the safe side). It asks whether the
MONITORED ACCOUNT announces for stores outside GREATER MELBOURNE, not whether
the company is national. Greater Melbourne, not Victoria: Yo Way's Westfield
Geelong site alone disqualifies it.

The chains.yaml notes were stale in two places and the live data corrected them:
Yo-Bar's Melbourne-venue list predates the Canberra opening, and YOMG's "VIC
stores" heading was a subset, not a footprint.

### Also
- Auto-approve now requires scope 'melbourne'. A national chain's own promo page
  has the same problem as its Instagram, and that is the one path that publishes
  without a human.
- Duplicate matching gates on scope in both copies. A national chain posts one
  promo once per city, so the copies are word-identical; merging the Melbourne
  one INTO the Canberra one would hide a real deal behind an unpublishable row.
  'unknown' stays compatible with everything, since blocking on it would strand
  the reposts the matcher exists to catch.
- /review shows `store_hint_raw` ("Source names Coolangatta") for every deal, so
  the classification can be checked rather than trusted, makes scope editable,
  and interrupts an approve on a scope-'other' deal.
- Backfill was done by hand, not by heuristic: only 7 distinct store_hint_raw
  values existed, each classified explicitly in the migration.

### Not done
Hashtags are not location evidence, matching the existing store_hint rule, so a
caption whose only signal is #canberra derives from the chain instead. Hashtag
sprays are exactly the noise that rule was written against.

### Discovered while shipping this: two fixtures are unstable, and the cache hid it
Adding a field to extract_deal.txt changes the prompt hash, which invalidates the
whole extraction cache (keyed content_hash + prompt_hash) and re-hits the model
for every fixture. Three then failed: 014_this_weekend_25, 015_double_offer,
017_smudged_sign.

014 was transient and has not recurred. 015 and 017 are not: across six runs —
the new block at 1460, 734 and 268 chars, and two runs with the block stripped
out entirely — 015 returns fixed_price where the fixture expects bundle, and 017
returns no deal where the fixture expects one, in five of six. The single passing
control was the outlier, not the rule.

**This is not a regression from stated_location.** The first control run passing
made it look like one; repeating the control reproduced both failures with the
new field absent. Recorded because the wrong conclusion was reached first and the
evidence for the right one is only visible in aggregate.

What it means: the suite was green on cached answers from whenever the prompt last
changed, not on current model behaviour, so extraction quality had drifted
silently.

Resolved: neither re-tune nor xfail. The expected files are untouched — rewriting
an expectation to match current output converts a real quality loss into a
passing test, and xfail makes the suite green again, which is the exact outcome
that hid this. Both failures are recorded in tests/fixtures/HOLDOUT.md as known
current failures, with the six-run evidence table showing they are not a
regression from stated_location.

017 is explicitly left undecided rather than unfixed: returning nothing on a
partly illegible sign is arguably correct under the prompt's standing
"never infer anything not stated" rule, and it is the same shape as the a04
miss. Whether the right answer is a deal or nothing is an extraction-policy
judgement, and that is a different question from making the test pass.

The cache itself is now visible rather than silent:
- `pytest --no-cache` re-extracts every fixture from the live model.
- The terminal summary reports what was actually measured. A fully-cached run
  prints a red banner saying it verified the cache and not the model; a
  --no-cache run prints a green confirmation; a mixed run says how many were
  live. It stays silent when no test used the extraction fixture.

HOLDOUT.md also now flags that its own 2026-08-06 baseline was recorded "all from
warm cache, 0 API calls" and is therefore unverified against the current model.

## 2026-08-16 — the extractor could silently consume a capture

### The bug
`BatchResult(captions=[])` is schema-valid. `_aligned_batch` rejected that shape
on its count check (`extract.batch_misaligned`) and then fell back to
`_singletons`, which had no equivalent check and flattened the identical empty
response to `[]`. **The safety check was undone by the retry it triggered:** the
same response was rejected as malformed and accepted as fact seconds later.

`[]` means "read it, found no promotion", so `run_db` marked the capture
`processed = true` and it was never looked at again. Proven against the real
database (rolled back): a real promo capture consumed, zero deals, no error, run
exited 0, and the summary logged `"captures": 3, "deals_inserted": 0` — a clean
line for a run that lost data.

Found while investigating four fixtures the first `--no-cache` sweep reported as
"unprocessed". Those four were plain exceptions during a 503 window and were
handled correctly; the investigation turned up this instead.

### Three fixes
1. **`_singletons` rejects an empty response** (`extract.item_empty` -> None ->
   retried), so a protocol failure can no longer masquerade as a judgement. Only
   the empty case: `len(res) > 1` is the deliberate multi-array shape that
   preserves a second offer, and a test guards it.
2. **The run summary reports failures**: `failed`, `failed_ids`,
   `outage_suspected`, `abandoned` alongside the successes. Counting only
   successes is what made a lossy run look identical to a clean one — the real
   log line `"captures": 1, "total": 2` was a capture failing in silence.
3. **Five-strike abandonment**, the same bounded-strike shape used on the scrape
   side: `raw_captures.extract_attempts` (migration 0013), dropped from the retry queue
   at the limit, with a structured log line and a dated PROGRESS.md note. Nothing
   is deleted or marked processed; `extract_attempts = 0` requeues it.

**Why 5 where the scrape side uses 3.** The asymmetry is deliberate and runs the
other way on purpose. On the scrape side a fast trip is protective: hammering a
source that is refusing you makes it worse, so stopping early is the safe error. Here the
opposite holds — abandoning a capture is the destructive act and a retry costs one
API call, so giving up early on a live promo is the expensive mistake. Twice-daily
runs make 5 strikes ~2.5 days, which outlives the transient API weather seen so
far (429 bursts, the 2026-08-15 503 window, both measured in hours) where 3
(~36 hours) sits uncomfortably close to a weekend outage. Past ~5 it is a defect,
not weather.

Plus a guard against mass abandonment: if EVERY capture in a run fails, that is
the API, not the captures, so strikes are not counted and `extract.outage_suspected`
is logged instead. With a single capture the two are indistinguishable, so it counts.

### Exposure
113 processed captures produced no deal. 13 carry promo vocabulary; on reading
all 13, every one is explicable as a correct rejection under the prompt's own
exclusion rules (store openings, competitions requiring an entry action,
third-party posts, teasers), with 2-3 borderline. No `batch_misaligned` event
appears anywhere in the logs — but the logs only reach back to 2026-08-08, so
that clears 8 days, not the corpus. **No evidence the bug fired in production,
and no way to prove it did not**, which is the point: it was undetectable by
construction.

### The measurement consequence
A dropped request and a correct rejection produced byte-identical output, so
every zero-deal measurement taken before this is ambiguous — including the
natural set's 5/5 rejections, which had been treated as the one solid result in
the holdout. Marked in HOLDOUT.md as needing re-measurement, not re-measured in
this pass. The asymmetry is worth noting: this could only ever inflate apparent
rejections, never invent a deal, so recorded positive extractions are unaffected.

## Phase 6d incident (2026-08-17)

- **Instagram ingestion stopped after 3 consecutive failed runs and was disabled
  automatically.** Recorded because it is the point of the failure counter: a
  source that returns nothing must not read as a healthy run. Diagnosis and
  recovery are handled in the private ingestion source.
