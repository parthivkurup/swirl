# Deferred

Non-blocking items parked during the autonomous phases 2 to 5 run. Each has
enough detail to act on later.

## Phase 2

- **content_hash for image-only captures hashes raw bytes, not pixels.** Two
  visually identical images saved with different compression would not dedupe.
  Acceptable now because manual image capture is low volume and the phase 2
  CHECK is text-based. If image dedupe matters later, hash a perceptual/pixel
  digest (decode, normalise, hash pixels) instead of file bytes.

## Phase 3

- **Free-text and confidence compared by rule, not equality.** headline and
  conditions are model-generated prose and confidence is subjective, so the test
  harness checks headline non-empty, confidence only by side of the 0.6
  threshold for low-confidence fixtures, and structured fields exactly. If a
  stricter free-text check is wanted later, add a semantic-similarity assertion
  rather than string equality.
- **store_hint resolution is untested against real stores.** The stores table is
  empty until phase 9, so resolve_store returns null for every fixture. A unit
  test exercises the fuzzy match with synthetic rows, but end-to-end store
  attribution cannot be verified until phase 9 seeds stores.
- **Stale cache entries accumulate across prompt edits.** Each prompt change
  makes a new prompt_hash, leaving the old per-caption cache files behind.
  Harmless and gitignored; add a prune step if the cache dir grows.

## Phase 5

- **/api/image serves local files by exact path match.** It only returns a file
  whose path is recorded in raw_captures.image_path and exists on disk, so
  arbitrary reads are blocked, but it does read from the server filesystem. When
  real image captures arrive, move stored images under a controlled media
  directory and serve by id rather than raw path.
- **No auth on the review dashboard or mutation API.** Fine for a local
  single-operator tool; add auth before exposing it beyond localhost.
- **Fixtures yield 19 pending deals, the CHECK asks for 20.** The 30 fixtures
  contain 18 positive captions producing 19 deal objects. Seeding from fixtures
  (as instructed) gives 19 pending. The operator will ingest the 20th; no queue
  padding.
- **RETRACTED: confidence is not bimodal.** An earlier note claimed the model's
  confidence was effectively bimodal (~0.95 clear / ~0.3 illegible). That was a
  fixture artifact: those 30 captions happened to land at the extremes. Real
  capture 31 returned 0.5 on unusually explicit wording under the old prompt and
  0.9 under the new prompt, i.e. the same caption moved 0.4 on a prompt edit.
  Confidence is uncalibrated and prompt-sensitive. Do NOT build any logic that
  assumes bimodality or any fixed confidence distribution. The only place
  confidence drives behaviour is the 0.8 + website auto-approve gate, which is a
  deterministic threshold tested by test_auto_approve_threshold; that stays.
  The compare.py 0.6-band check is a regression guard on the current 30 fixtures
  (they still bracket 0.6), not a calibration claim; if a future prompt
  legitimately moves a fixture across 0.6, revisit it, do not force it.
- **Prompt is fit, not generalised.** Iterated twice against the same 30
  fixtures it is scored on. Do not tune it further against those 30; build a
  phase-6 holdout first. Policy in tests/fixtures/HOLDOUT.md.

## Phase 5 addendum (2026-08-05, out-of-sample capture 31)

- **RESOLVED: per-unit pricing.** deals.unit_basis added (migration 0004,
  'flat' / 'per_100g' / 'per_kg') and the prompt now sets it whenever a price is
  stated, so self-serve per-weight pricing is representable. No longer a gap.
- **Capture 31 stored text is missing its price number, and needs re-ingesting.**
  raw_capture 31 reads "available for  per 100 grams" with a blank where the
  amount belongs; there is no '$', no digit for the rate, and no image_path. So
  discount_value cannot be extracted and the hand-labelled holdout expected
  leaves it null. If the real caption stated "$3 per 100g" (as reported),
  re-ingest capture 31 with the complete text; the expected then becomes
  discount_value 3, unit_basis per_100g unchanged. Until then the extractor is
  behaving correctly by not inventing a number.
- **RESOLVED: @mention -> chain_id.** Implemented as exact, case-insensitive
  match of an @handle against chains.instagram_handle (never fuzzy, never
  creates a chain), applied in build_deal_row when no store matched. Unit-tested.
- **--text is shell-expansion prone (data-loss defect, now guarded).** raw_capture
  31 lost its "$3" because --text was passed in double quotes and zsh expanded
  $3 to an empty positional parameter; the leftover double space
  ("available for  per 100 grams") was the signature. Mitigations: --stdin (now
  the documented default) and --file read the caption without a shell in the
  path; --text warns to stderr on expansion signatures (a run of 2+ spaces, or
  "per 100g" with no preceding digit) but does not block. Phase 6 scrapers are
  unaffected: they build RawCaptures in Python and never pass a caption through a
  shell.

## Phase 7

- **Dashboard suburb filter and chain attribution are thin until phase 9.**
  store_id is null on every deal (stores table empty until the phase 9 Google
  Places sweep), so suburb is always null and the suburb filter has nothing to
  bind to; many deals also have chain_id null. The controls work; they gain data
  in phase 9. No code change needed then, only data.
- **Past-dated approved deals show as active until expire_deals runs.** The
  dashboard shows status='approved' regardless of valid_to; the phase 8 nightly
  expire_deals job moves valid_to < today to 'expired', which removes them.
- **Dashboard coverage claim should be honest about scope (product decision
  2026-08-06, PROGRESS.md; no code change now).** The tracker covers what its
  sources publish - 16 monitored Instagram accounts and 2 scrapeable websites -
  not "all Melbourne froyo deals". The public copy should say so (e.g. "deals
  posted by the froyo shops we follow" rather than an exhaustive-coverage claim)
  so the dashboard does not overstate completeness. Deferred as a copy change;
  not implemented in this pass.

## Phase 6b

- **RESOLVED: every write path now has a test that executes the real SQL.** Two
  SQL parameter-type bugs (the reverify status reuse, and the phase-7
  last_verified `case when %(status)s='approved'`) reached runtime because no
  test executed a real write. Audited all seven write paths and closed the gap
  (rolled-back, skip without a DB): INSERT_DEAL, expire, and reverify's
  last_verified bump in tests/test_writes.py; approve, reject, edit-and-approve
  and save (which share EDIT_SQL) in web/tests/mutations.test.ts. The review-route
  SQL was extracted to web/lib/mutations.ts so the route and the test share one
  source of truth. Run with `pytest` and, in web/, `npm test`.
- **Submission content_hash follows manual semantics (text-first).** When a
  submitter adds text/store name, the capture dedups on that text, not the image,
  so two different photos with identical text would collide. Rare; acceptable for
  now. If it matters, hash the sanitized image bytes for submissions instead.
- **Rate limit is in-process per IP (5 / 10 min).** Resets on server restart and
  is per-process; fine for a single-instance hobby deployment. Move to a shared
  store if it ever runs multi-instance.

## Phase 6c

- **Auth is a single shared admin password with a signed, expiring session.**
  Login checks ADMIN_PASSWORD (timing-safe) and issues a cookie `<iat>.<hmac>`
  signed with a SEPARATE SESSION_SECRET (httpOnly, secure in production,
  sameSite=lax). The server verifies the MAC and rejects sessions older than 7
  days; rotating SESSION_SECRET revokes all sessions without touching the
  password. Token logic is in web/lib/session.ts, unit-tested in
  web/tests/auth.test.ts. No accounts, no session store. sameSite=lax mitigates
  CSRF on the mutation routes. Add real accounts/rotation if reviewers grow.
- **Secure cookie is production-only.** secure=true when NODE_ENV=production so
  localhost dev over http still works. Deploy over HTTPS.
- **If public images are ever wanted, the mechanism is a per-image publishable
  flag set at review time, never a blanket unauthenticated /api/image.** Decision
  (confirmed 2026-08-05, see PROGRESS.md): approved-deal images stay non-public
  because submission photos are untrusted pixels that EXIF stripping cannot
  sanitise. If that changes, add a boolean like deals.image_public (or
  raw_captures.image_public), default false, that the reviewer sets deliberately
  when approving; serve only those via a dedicated public image route that checks
  the flag AND approved status. Do NOT relax /api/image to allow unauthenticated
  reads of all approved-deal images.

- **Auth guards are per-route, not middleware.** Each protected route (review
  page, /api/deals/[id], /api/image) calls isAuthed() itself. A new protected
  route must remember to call it. Consider Next middleware if the surface grows.

## Phase 6d

- **The Instagram capture source is private and not part of this repository.**
  `ingest/scrapers/instagram.py` is the interface stub; the entries below cover
  only the public half — provenance, the auto-approve gate, dedupe and failure
  handling — because those are what the rest of the pipeline depends on.
- **chain_id resolves through source_handle -> via_handle -> @mention
  (2026-08-06).** raw_captures.source_handle (migration 0007) records the post's
  actual author; via_handle (migration 0008) records the monitored profile a post
  was surfaced under when the author is a third party (a tagged/collab/feature
  post). build_deal_row tries, in order: source_handle if it maps to a known
  chain, then via_handle, then the @mention rule. The 90 historical captures were
  backfilled zero-request from the author handle already embedded in content_text
  ("<handle> on <date>:") - NOT a 90-permalink re-fetch, and NOT the positional
  id-mapping (which records the surfacing visit, not the author). 80 monitored
  captures got source_handle; the 10 third-party got via_handle from the positional
  mapping (id-contiguous, chunk-by-6) and keep source_handle null. All 19 deals
  (all authored by monitored accounts) now carry chain_id.
- **Auto-approve rests on source_type alone in practice (2026-08-06).** Across
  the 19 Instagram deals, stated confidence spans 0.9-1.0 with nothing lower, and
  all 6 website deals sit at 0.95; only the deliberately-illegible fixtures ever
  fall below 0.8 (they span 0.3-0.95). The field tracks caption/sign legibility,
  not extraction correctness, so the `confidence >= 0.8` clause of the
  auto-approve gate filters nothing on real data. The effective gate is
  `source_type == 'website' AND _extraction_complete`; the confidence clause is a
  no-op in production. Instagram never auto-approves regardless (the source_type
  gate), so every Instagram deal is reviewed by hand. Not changing the gate yet;
  recorded so it is understood that source_type is the real control. Confidence-
  based filtering, if ever wanted, needs a calibrated signal, not this field.
- **Third-party posts are kept, not filtered (2026-08-06).** A monitored profile
  also surfaces posts it is tagged in or collab'd on, authored by someone else.
  These are kept on purpose - a local food account posting "Yolux is doing 20%
  off" is legitimate evidence - and attributed honestly via via_handle rather than
  being credited to the monitored account. In the historical run 10 of 90 captures
  were third-party, spread across 8 of 15 accounts. If they ever crowd out an
  account's own posts, the fix is to widen that account's per-run allowance, NOT
  to filter third-party posts out: filtering would discard legitimate sources.
- **Image dedupe is per-capture file, hashed by bytes.** Images are saved under
  `media/instagram/` and, for image-only posts, content_hash uses raw bytes (same
  limitation already noted for phase 2): two visually identical images with
  different compression would not dedupe. Fine at this volume.
- **Failure state is file-based and single-host.** The consecutive-failure counter
  and the sentinel that disables scheduled runs live on local disk under `data/`.
  Correct for a single box; would need rethinking if ingestion ever ran on more
  than one host. The runner also appends an incident note to PROGRESS.md at
  runtime.

## Finding 2: near-duplicate deals (2026-08-06)

- **Possible-duplicate detection is a query-time review hint, never an auto-merge.**
  web/lib/dedupe.ts scores a pending deal against the pending+approved pool on
  chain_id (null = wildcard), deal_type, discount_value (equal or both null),
  overlapping validity window (null = open-ended), and a char-bigram headline
  similarity; pairs sharing a raw_capture_id are excluded (one post yields
  multiple legitimate offers). Computed at read time in getPendingDeals, not
  stored, so it stays correct as deals are approved/edited/expired and spans
  sources. The queue shows "possible duplicate of deal N" for the reviewer to
  decide. Verified against real data: the four "50% off" rows flag each other, the
  two "first 300" rows flag each other, and the $3/100g pair flags each other AND
  the website copy (deal 79), i.e. cross-source dedupe works.
- **Null-value freebies over-flag; SIM_NULL_VALUE is the dial.** Because
  freebie/bogo/loyalty carry no discount_value, those matches lean entirely on the
  headline. With the current threshold (0.6) "first 30" (deal 118) is also flagged
  against "first 300" (114/115), and a generic "Free mini cup for first customers"
  (70) flags against them. These are surfaced hints a reviewer dismisses in a
  glance, judged the right trade-off vs missing true duplicates; raise
  SIM_NULL_VALUE to tighten, at the risk of dropping loosely-worded true pairs.
  Valued pairs use a lower bar (SIM_VALUED 0.35) because an equal discount_value is
  already strong identity.
- **Legacy null chain_id relies on the wildcard.** The 19 existing Instagram deals
  have null chain_id (Finding 1 is fix-forward), so they can only match each other
  via null-as-wildcard. Once chain-attributed captures flow, chain equality does
  more of the work and the wildcard matters less.
- **Pre-review merge uses earliest-id canonical; switch to most-complete if it
  bites (2026-08-08).** The merge job now runs on pending as well as approved deals
  (so the queue shows one canonical row per promo, not four to hand-adjudicate).
  Canonical = the approved deal in a group if any, else the earliest-created
  (lowest id) pending. For approved deals this is safe (all were vetted); for
  pending the canonical is unvetted, so if a later duplicate post carried a MORE
  COMPLETE extraction (full T&C vs a thinner repost), merging to the earliest could
  hide the better one and the reviewer would approve the thinner by default. This
  is blunted three ways: the strict gate refuses to merge genuinely-divergent
  extractions (different value/window/type -> both shown), the superseded filter
  lets the reviewer compare and undo, and merging never changes status. If a thin
  canonical is ever seen hiding a better duplicate, the switch is to pick the
  pending canonical by extraction completeness (most non-null fields / longest
  caption) instead of lowest id, in ingest/merge_dupes.find_merges.
- **Two duplicate-scorer implementations must stay in sync (2026-08-06).**
  web/lib/dedupe.ts flags possible duplicates in the review queue (query-time);
  ingest/dedupe.py (a Python port) decides which flagged pairs the nightly
  merge job (ingest/merge_dupes.py) actually collapses. The similarity function and
  thresholds (SIM_VALUED 0.35, SIM_NULL_VALUE 0.6) are identical and parity-checked
  in tests/test_dedupe.py, but a change to one MUST be mirrored in the other or the
  job will merge pairs the UI never surfaced (or vice versa). If this bites,
  consolidate to one implementation (the job shelling out to the TS scorer, or a
  shared spec both read).

## Extraction batching (2026-08-06)

- **Images cannot batch; they are sent one per request. Tested, not assumed.**
  Multi-image batching was tested by re-extracting all 90 stored Instagram
  captures forced into batches of 10 and diffing each re-extracted deal (mapped
  through the real build_deal_row) field-by-field against its stored singleton
  deal, on material structured fields only. Index-alignment held on 100% of
  batches (the caption_index guard works), but **10 of 90 captures were
  materially contaminated**: 5 captions that singleton-extracted to NO deal
  gained a spurious priced deal under batching, with values and dates bleeding
  from neighbours in the same request (capture 64 gained a freebie dated
  2026-06-20, another caption's date; 108 gained "$4.99 flat", capture 128's
  price; 62 gained "$4.20/100g"; 113 gained "$12.99"), and 5 lost their
  store_hint. This is semantic bleed between images, which index-alignment cannot
  catch. So `_batches` sends every image-bearing caption alone. Text-only captions
  still batch up to BATCH_SIZE. Stats now log `text_batches` and `image_calls`
  separately so the cost split is visible, not hidden in one aggregate.
- **PENDING DECISION: per-run image-call cost still blocks unattended cron.** With
  images singleton, cost is ~1 API call per image-bearing capture. Two framings
  matter: the 90-call figure is a COLD-START cost (the first full crawl). In
  steady state the scraper stops at each account's last-seen shortcode, so a run
  only extracts posts published since the previous run, which across 16 low-volume
  froyo accounts is a handful, not 90. The free-tier pain is the cold start
  hitting the per-minute quota (observed: 45 calls to clear 9 batches under 429
  backoff). Options proposed, not implemented, pending the owner's choice:
  1. **Text-first-pass filter (highest leverage).** Before sending the image, try
     a text-only extraction of the caption (cheap, batchable). If it yields a
     confident AND complete deal, skip the image entirely; only send the image
     when the caption alone is empty/decorative or incomplete. Must stay
     conservative because image-only promos with throwaway captions are the exact
     case images exist to catch, so skip the image only on a complete text result.
  2. **Fewer posts per profile** (6 -> 3), halving the worst-case per-run image
     calls at the cost of missing older unseen posts on a first crawl.
  3. **Lower scrape frequency** (2/day -> 1/day), the coarsest lever, halves cost.
  Plus a one-time throttled cold-start backfill so the initial 90 does not hit the
  per-minute cap. Recommendation: run cold start once (throttled), keep 2/day, and
  build option 1 (text-first-pass) as the durable structural fix; revisit 2/3 only
  if steady-state volume turns out higher than expected.
  **Owner decision (2026-08-06): build none of the three now. The 90 is confirmed
  a cold-start figure, not steady state. Concrete revisit trigger: do nothing
  unless a steady-state run exceeds ~20 image calls.** If option 1 is built later,
  a hard constraint: the text-first pass must NEVER skip the image when the caption
  is short/decorative and the text extraction returns [] (image-only promos with
  throwaway captions are the exact case images exist for). Skip the image ONLY on a
  confident AND complete text extraction, and ship a fixture proving an image-only
  promo still gets its image sent.
  **Update (product decision 2026-08-06, PROGRESS.md):** Instagram is now the
  PRIMARY source, and the census established that these accounts state offers in
  captions (image redundant). Text-only extraction would therefore suffice for
  nearly all primary-source captures, which strengthens option 1 (text-first-pass)
  as the eventual cost fix. STILL do not build it: the cold-start reframe stands
  (steady-state volume is small; revisit only above ~20 image calls/run).

## Image extraction: the a04 miss is a known limitation (downgraded 2026-08-06)

- **KNOWN LIMITATION, not a driver.** The ablation holdout measured that the
  extractor reads numeric price/discount from an image but MISSED a non-priced
  freebie ("300 FREE BOWLS") when the caption did not corroborate (a04; see
  HOLDOUT.md / MANIFEST.md). This failure mode lands hardest on captionless photos
  with non-priced offers, which is the `/submit` path (a submission is a photo with
  empty `content_text`, and non-priced freebies are common on in-store signage).
  **Per the product decision (2026-08-06, see PROGRESS.md): Instagram is the
  PRIMARY source, website scraping is secondary (2 chains), and /submit is a BETA
  feature that is not relied upon.** Since the primary source states offers in
  captions (see the census), the a04 gap does not affect primary ingestion, and
  the path it does affect (/submit) is beta. So this is downgraded from "the
  strongest argument for a prompt fix" to a recorded known limitation: non-priced
  freebies in captionless images may be missed. It is no longer driving anything.
  The ablation fixtures (a01-a04) stay as the validation set IF this is ever fixed
  (a fix flips a04 MISS -> READ without regressing the natural holdout's 5/5
  rejections), but nothing schedules that fix. Prompt tuning remains on hold.
