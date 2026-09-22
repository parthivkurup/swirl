# Holdout policy

> **The natural holdout captions (031-041) are a private set and are not in this
> repository.** They reproduce real posts verbatim, so the `.txt` /
> `.expected.json` pairs are held outside the public tree; `tests/test_holdout.py`
> skips each item when its caption is absent. The four ablation images (a01-a04)
> are private for the same reason, and `tests/test_ablation.py` skips those. The
> analysis below is unchanged and is the record of what was measured when the set
> was present — it is not reproducible from this repository alone.

The extraction prompt (`ingest/prompts/extract_deal.txt`) was iterated twice
against the same 30 fixtures in `captions/` that the test suite scores it on.
So `30/30` measures **fit, not generalisation**: the prompt has seen every
caption it is graded on. A green run on `captions/` proves the prompt still
handles those 30; it is not evidence the prompt generalises to captions it has
not been shaped against.

## A green run is not evidence of anything on its own (2026-08-15)

`extract_captions` caches per caption, keyed `content_hash + prompt_hash`. So
while the prompt is unchanged, **the suite scores the cache, not the model.**
Every green run after the first is the cache reciting answers recorded whenever
the prompt hash last changed. The model can drift underneath it for weeks and
nothing goes red, because nothing asks the model anything.

This is not hypothetical. The 2026-08-15 `stated_location` change altered the
prompt, invalidated the cache, re-ran all 30 `captions/` fixtures against the
live model, and two of them failed immediately — see "Known current failures"
below. They had presumably been failing for some time, invisibly.

**It applies to the baseline stated in the next section.** The 032-041 comparison
run is recorded below as "all from warm cache, 0 API calls". That number
therefore describes the cache as it stood on 2026-08-06, not the model's
behaviour then and certainly not now. Treat the natural-set and ablation-set
figures as unverified against the current model until re-measured with
`--no-cache`.

How to actually check:

```
pytest tests/test_extractor.py --no-cache      # re-extracts all 30 from the model
```

The suite reports which it did. A fully-cached run prints a red banner saying so;
a `--no-cache` run prints a green line confirming the result reflects current
model behaviour; a mixed run says how many were live. Costs real API calls and
takes minutes, which is why it is explicit rather than the default — but a green
run without that banner addressed is not a measurement.

## Current baseline (2026-08-06, MEASURED ON CACHE — see above)

Stated plainly, this is what the current prompt scores on the two out-of-sample
sets. Any future prompt change must be measured against BOTH sets, before and
after, and must not regress the rejections.

- **Natural set (10 real Instagram captions, `032`-`041`):** 0 genuine errors,
  5/5 correct rejections, 1 policy divergence (032 `store_hint`, unresolved - see
  NOTES.md). **The 5/5 needs re-measurement** - every one of those five is a
  zero-deal result, and until 2026-08-16 a dropped request scored identically to
  a correct rejection. See "EVERY ZERO-DEAL MEASUREMENT BEFORE 2026-08-16 IS
  AMBIGUOUS" below.
- **Ablation set (4 synthetic image-only captures, `a01`-`a04`):** 3/4 image reads,
  1 miss (a04, the non-priced freebie - see MANIFEST.md and DEFERRED.md). **The
  a04 miss needs re-measurement** for the same reason, and has only ever been
  measured once. The 3 reads are unaffected: the bug could not invent a deal.

The bar for any prompt change: it must not lower the natural set's 5/5 rejections
or turn a read into a miss, and a change aimed at the a04 failure is judged by a04
flipping MISS -> READ on the ablation set. The 30 `captions/` fixtures remain
regression fixtures (must keep passing) but do not measure generalisation.

## Rule

Do not tune the prompt further against the existing 30 fixtures. Any further
prompt change must be validated on captions the prompt has not been fitted to.

## Before the next prompt change

1. Take the first 10 real captions from the phase 6 website scraper
   (`raw_captures` rows with `source_type = 'website'`).
2. Hand-label each with its expected deal JSON, following the conventions in
   `NOTES.md` and the field rules in the prompt. Label them blind, before
   looking at what the current extractor returns.
3. Add them under `tests/fixtures/holdout/` as paired `.txt` / `.expected.json`,
   the same format as `captions/`.
4. Score the CURRENT prompt on the holdout first and record the number. That is
   the generalisation baseline.
5. Only then consider tuning the prompt, and judge any change by the holdout
   score, not the in-sample 30. Report the holdout score as the headline metric.

The 30 in `captions/` stay as regression fixtures: they must keep passing, but
keep them separate from the holdout used to measure generalisation.

## Holdout items

### 031_yomg_per_100g (first item, YOMG "$3 per 100g")

First real out-of-sample capture. It exposed three gaps now fixed: `unit_basis`
(per-weight pricing, migration 0004), channel exclusions in the prompt, and deal
category (migration 0005). The original capture lost its "$3" to a shell
quoting bug (double-quoted `$3` expanded to empty); it was re-ingested via stdin
with the complete caption, and this holdout uses that corrected text.

Hand-labelled expected: `fixed_price`, `discount_value` 3, `unit_basis` per_100g,
`category` froyo, `channels` [dine_in, takeaway] (online and third-party delivery
excluded), valid_from and valid_to 2026-08-05, `store_hint` null ("all locations"
names no single store), `chain_id` 4 (resolved from the @yomgburgers mention).

`chain_id` is a post-processing result, not extractor output; it is recorded here
because this holdout documents the whole-pipeline result, not just the model
output. The holdout is the generalisation reference per the policy above, not a
regression gate: `tests/test_holdout.py` scores it only when the private captions
are present and skips every item otherwise.

### 032-041 (phase-6d Instagram out-of-sample, 2026-08-06)

Ten captures drawn from the 90 real Instagram captures, selected for spread using
only counts (deal_count, caption length, image presence), never deal contents: 5
that produced deals (percent_off, loyalty, fixed_price/per_100g, freebie, and one
multi-offer bogo+freebie), 5 that produced nothing (3 image-heavy thin-caption
posts, 2 long non-promo posts). Labelled from caption + image alone, before
looking at extractor output; `extract_deal.txt` was NOT changed.

Baseline result against the current prompt (comparison run 2026-08-06, all from
warm cache, 0 API calls): **one structured divergence in the whole set** and
5/5 correct rejections. The divergence is 032 (froyolicious bottle-flip)
`store_hint`: labelled null (per the 001 convention that a business's own
promotional location is not a store designator), model returned "Docklands"
(named in prose "docklands best froyo"). This is a genuine policy question, not a
clear model error: should a suburb named in caption prose populate `store_hint`?
Unresolved; recorded, prompt unchanged.

Caveats on evidentiary weight:
- The 5 deal-producers were seen (their stored structured fields) earlier in the
  same session during dedupe/batching work, so their near-exact match is weak
  evidence of generalisation (possible anchoring). The confidence values were not
  matched (labelled 0.7-0.9, actual 0.95-1.0), minor evidence against pure
  copying. The 5 no-deal rejections were genuinely blind and the images viewed
  fresh; the model correctly rejected all 5 non-promos, including 2 wordy posts
  built to bait a false positive. Zero false positives.
- GAP (now addressed by the ablation set below): the 3 image-heavy thin-caption
  picks all turned out to be non-promo images, so they test false-positive
  avoidance, not image-only promo extraction.

### Census: no natural image-only promos in the 90 captures (2026-08-06)

Complete, load-bearing: **none of the 90 Instagram captures is an image-only
promo.** All 19 priced deals have their value in the caption text (SQL); all 52
thin/decorative no-deal images were viewed (52/52) and are flavours, food photos,
lifestyle reels, memes, brand statements, closures, or store shots. The images
that do render an offer also state it in the caption, so none isolate image
reading. Implication: these accounts put offers in captions; the image is
redundant (which also strengthens the deferred text-first-pass cost fix).

### Ablation holdout a01-a04: first measured image reading (2026-08-06)

Because no natural case exists, image reading is measured with 4 synthetic items
(real promo image + decorative caption ablated of the offer; see MANIFEST.md).
Result against the current prompt: **3/4 offers read from the image, 1 miss.**
a01 ($4.99 flat), a02 ($3/100g, resolved "today"→capture_date), and a03 (50% off,
read correctly off a CROPPED graphic) all extracted; a04 ("300 FREE BOWLS")
produced no deal, even though holdout 035 (same image, real caption) extracts it.
So the extractor reads numeric price/discount from images but can miss a
non-priced freebie when the caption does not corroborate. Recorded, not acted on;
extract_deal.txt unchanged.
- These items carry images at media/instagram/<shortcode>.jpg (gitignored), so
  the .txt alone is not reproducible for the image-dependent items; a future run
  needs the images present.

## Known current failures (2026-08-15) — SUPERSEDED, see the clean sweep below

**Read this section as history, not as the current failure set.** It was written
from runs taken during an API outage, before protocol failures could be
distinguished from extraction failures. The current, cleanly measured failure set
is 004, 006 and 013 — see "Clean uncached sweep, post-fix (2026-08-16)" at the
end of this file. Both fixtures named below pass now.

Recorded, not fixed. Both are in the in-sample `captions/` set, so they are
regression fixtures rather than generalisation measurements — but the policy
above says they must keep passing, and right now two do not.

They surfaced only because the `stated_location` prompt change busted the cache.
Neither expected file has been edited: rewriting an expectation to match current
output would convert a real quality loss into a passing test and delete the
evidence. Neither is marked xfail, for the same reason — xfail makes the suite
green again, which is the outcome that hid this in the first place.

### 015_double_offer: bundle -> fixed_price (PASSES as of 2026-08-16)

Expected two deals, `percent_off` + `bundle`; during the 2026-08-15 runs the
model returned `percent_off` + `fixed_price`. Deal count and the percent_off deal are correct; only the second
deal's type differs. Per the prompt, `bundle` is a multi-item price ("2 cups for
$22") and `fixed_price` is a single-item price, so this is a real distinction and
the current output is wrong about it.

### 017_smudged_sign: one deal -> none (PASSES as of 2026-08-16)

Expected one `percent_off` deal; during the 2026-08-15 runs the model returned
none. The policy question below is still worth settling, because the behaviour
recurs intermittently — but it is not a standing failure.

**This one may not be a bug.** The fixture is a deliberately ambiguous, partly
illegible sign, and the prompt's standing rule is "Never infer anything not
stated" with confidence "below 0.6 when the terms are ambiguous or the image is
partly illegible". Returning nothing rather than guessing at a smudged number is
arguably the correct behaviour, and the expectation may simply encode what the
model happened to do when the fixture was written. It is also the same shape as
the a04 miss below: a caption that does not corroborate the image, and the model
declining.

Deciding whether the right answer is a deal or nothing is a judgement about
extraction policy, and it is a separate question from making the test pass. Do
not resolve it by editing the fixture in either direction until that judgement is
made.

### Relationship to the a04 miss

a04 (ablation set, "300 FREE BOWLS" image with the offer ablated from the
caption) also produces no deal. Three of the recorded failures — a04, 017, and
arguably the 032 `store_hint` divergence — are all the same underlying question:
how much should the extractor commit to when the caption does not corroborate
what the image or the wording implies? They are listed separately because they
were found separately, but a change aimed at any one of them should be judged
against all three, and against the natural set's 5/5 rejections, since making the
extractor bolder is exactly what would turn correct rejections into false
positives.

### Evidence that these are not a regression from `stated_location`

Six runs, varying only the prompt block that introduced the field:

| prompt | 015 | 017 |
|---|---|---|
| new block, 1460 chars | fail | fail |
| same, cache-busted | fail | fail |
| block stripped (control 1) | **pass** | **pass** |
| new block, 734 chars | fail | fail |
| new block, 268 chars | fail | fail |
| block stripped (control 2) | fail | fail |

The single passing control was the outlier: repeating it with the field absent
reproduced both failures. Shrinking the block 5x changed nothing either. The
schema change alone is also cleared — control 1 ran the new required
`stated_location` field with the old prompt text and passed. Conclusion: these
fixtures are unstable against the current model regardless of the change, and
the warm cache had been hiding it. 014_this_weekend_25 failed once in the same
sweep (`days_of_week` [6,7] -> []) and has not recurred; it is genuinely flaky
rather than consistently failing, and is not listed above.

### 006_every_single_day: recurring/days_of_week, the reading NOTES.md predicted

Expected `recurring: false` with `days_of_week: []` ("every single day" as an
open-ended standing offer); the model now returns the daily-cycle reading,
`recurring: true` with all seven days.

NOTES.md line 88 already documents both readings and calls the second "a real
reading". Neither is wrong. The fixture encodes the labeller's preference — that
`days_of_week` is a field for restriction and putting all seven days in it
overloads it — and the model has landed on the other side of a judgement the
project had already recorded as genuinely open.

Recorded, not resolved. Do not change the fixture or the prompt: this is the same
class as 015 and a04, a documented ambiguity rather than a defect, and tuning the
prompt to force one reading would be fitting to the in-sample 30 in exactly the
way the policy above forbids.

## Correction to the 015/017 evidence table (2026-08-15, later)

**017 passed the first full `--no-cache` sweep** (31 fixtures, 189s, 6 failures,
017 not among them). The six-run table above therefore overstates its
consistency. 017 is not a stable failure; it is a fixture that sometimes extracts
the deal and sometimes returns nothing.

Two consequences:

1. **Single-run results on 017 are not reliable evidence in either direction.**
   Any future claim about it — that a prompt change fixed it, or broke it —
   needs repeated runs, not one. The same caution applies to a04, which is the
   same shape and has only ever been measured once.
2. The earlier runs were sampled while the API was degraded (503 UNAVAILABLE and
   sustained 429s). See the extractor drop-path note below: an empty model
   response was, at that time, silently converted into "no deals", which is
   indistinguishable from a considered rejection. Some or all of those 017
   failures may have been that bug rather than model judgement.

**Superseded (2026-08-16): 015 is not a consistent failure either.** It passed
the clean post-fix sweep — see "Clean uncached sweep, post-fix" at the end of
this file. Both 015 and 017 are unstable, and the six-run table below was
measuring a degraded API more than it was measuring the model.

## EVERY ZERO-DEAL MEASUREMENT BEFORE 2026-08-16 IS AMBIGUOUS

Read this before citing any number in this file that takes the form "returned no
deal" or "correctly rejected".

Until the fix on 2026-08-16, an empty model response and a correct rejection
produced **byte-identical output**: an empty deal list. There is no way, from the
recorded results alone, to tell whether the extractor read a caption and judged
it a non-promo, or whether the request failed and the failure was silently
recorded as "nothing here". Both look like `[]`.

That contaminates, and these all need re-measuring:

- **The natural set's 5/5 correct rejections (032-041).** This has been treated
  as the one solid result in the holdout. It is 5 measurements of exactly the
  ambiguous kind: each is a caption that produced no deal. Some or all may have
  been real rejections - the captions were hand-checked as non-promos when
  labelled, which is genuine independent evidence - but the *extractor's*
  agreement with that label is not established, because a dropped request would
  have scored identically. Treat 5/5 as unverified pending re-measurement.
- **a04's miss** (image-only "300 FREE BOWLS", no deal produced). Measured once.
- **017's failures**, already corrected above for a separate reason.
- Any "12 negatives correctly produced none" style count in PROGRESS.md from
  phase 3 onward.

Not re-measured in this pass, by decision: recorded as needing re-measurement so
the numbers are not quietly reused. The re-measurement must be a `--no-cache`
sweep taken while the API is healthy, because a degraded API is exactly when the
old bug fired most.

Note the asymmetry: this only ever inflated apparent *rejections*. It could not
invent a deal, so any recorded positive extraction is unaffected.

## The extractor could convert an empty response into "no deals" (2026-08-15, fixed 2026-08-16)

Found while investigating four sweep failures reported as "no extractor output
(unprocessed)". Those four were exceptions and were handled correctly (left
unprocessed, retried). But the investigation turned up a separate, worse path.

`BatchResult(captions=[])` is schema-valid. `_aligned_batch` catches it — the
count check fails and it logs `extract.batch_misaligned` — and then falls back to
`_singletons`, which has no equivalent check and flattens the identical empty
response to `[]`. `[]` means "the model read this and found no promotion", so in
the scheduled path the capture is marked `processed = true` and never looked at
again. Proven against the real database (rolled back): capture consumed,
`processed=true`, zero deals, and the run logged `"captures": 3,
"deals_inserted": 0` and exited 0.

Why it matters here: **a protocol failure and a considered rejection produce
byte-identical fixture output.** See the section above for what that
contaminates.

Fixed 2026-08-16. `_singletons` now returns None on an empty response (logging
`extract.item_empty`) rather than `[]`, so the capture is left unprocessed and
retried instead of consumed. Only the empty case is rejected: `len(res) > 1` is
the deliberate multi-array shape and still flattens, guarded by a test. Two
further changes landed with it - the run summary now reports `failed` and
`failed_ids` alongside successes, and a capture that fails 5 consecutive runs is
abandoned and written up in PROGRESS.md rather than retried forever in silence.

## Clean uncached sweep, post-fix (2026-08-16)

The first sweep where protocol failures and extraction disagreements can be told
apart, and the first with **zero protocol failures** — so for once every result
is a measurement rather than possibly an outage.

31 fixtures, no cache, 20 API calls, 4 text batches, no images present.

```
PROTOCOL   0
EXTRACTION 3   004_yobar_mothers_day_bogo, 006_justcraveit_free_cake,
               013_while_stocks_last
PASS      28
```

### This corrects two earlier claims in this file

- **015_double_offer PASSED.** It was recorded above as "a consistent failure,
  unaffected by the 017 correction". That was wrong. It failed five of six runs
  during the 2026-08-15 API degradation and passes cleanly now. Like 017, it is
  unstable rather than consistently failing, and the earlier six-run table was
  measuring a degraded API as much as the model.
- **017_smudged_sign PASSED** again, confirming the correction already recorded.

More broadly: 002, 003, 007, 010, 025 and 028 all failed the previous pytest
sweep and all pass here. Every one of those was a protocol failure wearing the
costume of an extraction failure. The honest summary of the 2026-08-15 evidence
is that almost none of it measured the model.

### The three real disagreements

- **004_yobar_mothers_day_bogo:** no extracted deal with `deal_type` bogo. Not
  previously seen; needs a second run before it means anything.
- **006_justcraveit_free_cake:** `recurring` expected False, got True. The
  documented ambiguity, now seen twice.
- **013_while_stocks_last:** `recurring` expected False, got True. New, and the
  **same class as 006** — an open-ended standing offer ("while stocks last")
  read as a repeating cycle. Two fixtures failing the same way is the first
  evidence that this is a systematic reading rather than a one-off: the model
  currently treats "no stated end" as recurring, where the fixtures treat
  recurring as meaning an explicit weekly cycle.

That pattern is worth a decision eventually, but it is the same judgement call
NOTES.md line 88 already flagged, and it is still a policy question rather than a
defect. Prompt unchanged; fixtures unchanged.

### Standing caution

One clean run is one clean run. 013 was passing in the previous sweep and fails
here; 015 was failing and passes here. Treat any single-run result on this corpus
as provisional, and require repeated runs before concluding a prompt change
helped or hurt. That applies to the three above as much as to anything else.

## `recurring` for an offer with no stated end — DECIDED 2026-08-16

**Correction before anything else in this section: the half of "Reading B" about
`days_of_week` was wrong, and it was mine.** I described the model's reading as
`recurring: true, days_of_week: [1..7]`. It never did that. Across all four
measured sweeps — two before the prompt change and two after — `days_of_week`
was `[]` on every one of these fixtures, every time. Every divergence was on
`recurring` alone: `True/[]` against an expected `False/[]`.

The all-seven-days behaviour was **inferred from a failure message, not
observed**. The message only ever said `recurring: expected False got True`; I
reasoned from it to what the model must be doing with the other field and did not
check the raw output until much later. Everything below that argues against
enumerating seven days was arguing with nobody.

The rule that came out of it — `days_of_week` states a restriction, never a
frequency, so an everyday offer is `[]` and never all seven — is correct on its
own terms and is now in the prompt. But it was written in response to something
the model was not doing, so it is a clarification of an ambiguity in the spec,
not a fix for observed behaviour. Read the argument below with that in mind: its
`days_of_week` half is hypothetical throughout.

### The decision (2026-08-16)

- **006** stays `recurring: false`. Continuously available, nothing resets.
- **013** corrected to `recurring: true, days_of_week: []`. Resets daily with a
  fresh allocation, so it is a cycle of period one day, restricted to no weekday.
- **a03** corrected to `recurring: true`, keeping `days_of_week: [1]`. Every
  Monday is a weekly cycle; Monday is a real weekday restriction.
- The two fields are independent. `recurring` answers "does this come back",
  `days_of_week` answers "which weekdays is it limited to".

The original write-up follows, with the caveat above.

006 and 013 both fail as `recurring: expected False got True`. Two fixtures
diverging identically is why this is written up for a decision rather than left
as documentation.

### What the two readings actually are

- **Reading A (the fixtures, and the prompt as written):** `recurring: false`,
  `days_of_week: []`. "Recurring" means an explicit weekly cycle; an offer with
  no stated end is a standing offer that happens to run until further notice.
- **Reading B (the model, currently):** `recurring: true`. "Every single day"
  states a cycle. *(As written this said `days_of_week: [1..7]` as well. That was
  never observed — see the correction at the top of this section. The model
  returned `[]` throughout.)*

Note the prompt is not silent here. It says `recurring` is "true only when the
offer repeats on a stated weekly cycle ... false for ... an open-ended standing
offer with no cycle". So the model is diverging from a written rule, not filling
a gap. What the rule lacks is an example of a DAILY cycle: every example it gives
is weekday-named ("every monday", "$6 tuesdays", "fri sat sun only").

### What this does to the dashboard: one word, and nothing else

Traced through every path that reads either field. The two readings are
observably identical except for a single word in the meta line.

| path | `recurring:false, days:[]` | `recurring:true, days:[1..7]` (hypothetical) |
|---|---|---|
| `runsToday` (page.tsx:243) | `days.length === 0` -> true | `days.includes(dow)` -> true |
| band | 1, "Available today" | 1, "Available today" |
| sort within band | `checkedAgo` | `checkedAgo` |
| status line | "no end date given" (dimmed) | "no end date given" (dimmed) |
| day list in meta (page.tsx:195) | not printed (`length > 0` fails) | not printed (`length < 7` fails) |
| the `?day=N` filter (deals.ts:208) | matches via `cardinality = 0` | matches via `= ANY` |
| `wait` / "Other days" (page.tsx:283) | unreachable | unreachable |
| dedupe / merge | neither field is read | neither field is read |
| **meta line (page.tsx:198)** | — | **prints "recurring"** |

So the practical question is: should these rows carry the word "recurring" under
the headline, or not? Everything else — position, band, sort, filtering,
duplicate detection — is bit-identical. The `days.length < 7` guard at
page.tsx:195 already neutralises the all-seven-days case, so it never produces
the "Mon, Tue, Wed, Thu, Fri, Sat, Sun" noise it looks like it would.

### The case for A

- It is what the prompt says, so B is a rule violation rather than a judgement.
- "Recurring" earns its place in the meta line by telling the reader something
  they cannot otherwise infer — that a deal absent today will return next
  Tuesday. On a deal available every day it tells them nothing; it is a word
  that costs a line and adds no information.
- `days_of_week: [1..7]` is a lie of the same kind the project already rejects
  elsewhere: it asserts an explicit restriction to seven days where the source
  stated no restriction at all. Empty means "no restriction"; enumerating all
  seven means "restricted, to everything", which is a claim the caption did not
  make.

### The case for B

- The captions do say it. 006 is "every single day"; 013 is "first customers in
  each day". A rule that calls those "no cycle" is arguably reading past the text.
- `recurring: false` plus a null `valid_to` is currently indistinguishable from
  a one-off whose end date the extractor failed to find. B makes "this repeats"
  explicit rather than leaving it implied by two nulls.
- The prompt's examples are all weekday-named, so a model generalising from them
  to a daily cycle is behaving reasonably.

### A third possibility, which is why these two may not be one case

**006 and 013 may not actually be the same question**, and treating them as one
finding may be the mistake:

- **006** — "free cake slice with every froyo, every single day" — is
  *continuously available*. Nothing resets. There is no cycle in any meaningful
  sense, only an absence of an end date. Reading A looks right.
- **013** — "free mini cup for the first customers in each day, while stocks
  last" — *resets daily* and is capped per day. There genuinely is a daily cycle:
  miss it today and there is a fresh allocation tomorrow. Reading B's
  `recurring: true` is defensible here on the merits, independent of the
  no-stated-end question.

If that distinction is the right one, then the correct answer for 013 is
**`recurring: true` with `days_of_week: []`** — a cycle, but not a weekday
restriction. Neither the fixture nor the model currently produces that, because
both treat the two fields as moving together when they answer different
questions: `recurring` is "does this come back", `days_of_week` is "which
weekdays is it limited to". A daily offer is limited to no weekdays.

### To decide

1. Does an offer with no stated end and no reset (006) carry `recurring`? A says
   no, B says yes.
2. Does an offer that resets daily (013) carry `recurring`? Possibly yes even if
   the answer to 1 is no.
3. If `recurring: true`, should `days_of_week` be `[]` rather than all seven?
   This is separable from both and, on the "empty means no restriction"
   convention the project already uses, `[]` looks right regardless.

Whatever is decided, the dashboard consequence is one word on two rows today, so
this is a data-semantics decision, not a display one. Prompt unchanged, fixtures
unchanged, pending the call.

## Measured: the `recurring` prompt change, before and after (2026-08-16)

Prompt hash `005649f4026457f8` -> `149adaa360fd6403`. Change: the `recurring` and
`days_of_week` rules separated, a daily-cycle example added (recurring true,
days `[]`), the weekday example kept, and `days_of_week` stated as a restriction
never a frequency. Fixture labels corrected on 013 and a03; 006 unchanged.

**Two runs each way, not one.** One sweep of this corpus cannot support
attribution — see the noise section below.

| set | Before 1 | Before 2 | After 1 | After 2 |
|---|---|---|---|---|
| `captions/` (31) | 27 pass | 28 pass | 31 pass | 30 pass |
| `holdout/` (15) | 9 pass, 1 protocol | 12 pass | 11 pass | 11 pass |
| **natural-set rejections** | **5/5** | **5/5** | **5/5** | **5/5** |
| in-sample rejections | 12/12 | 12/12 | 12/12 | 12/12 |

The rejection guard the policy names held in every run, before and after. No
rejection was lost.

The two targeted fixtures moved onto the decided reading and stayed there:

| fixture | B1 | B2 | A1 | A2 |
|---|---|---|---|---|
| 006 (expected False) | `True` FAIL | `False` | `False` | `False` |
| 013 (relabelled True) | `False` | `True` | `True` | `True` |

### THIS CORPUS CANNOT SUPPORT SINGLE-RUN ATTRIBUTION

**The two before-runs, same prompt, same fixtures, minutes apart, disagree on
five fixtures**: 006, 013, 018, 033, 036 all flip between B1 and B2. A sixth,
035, flips too. Nothing changed between those two runs except the model's output.

Anyone reading a single sweep result — including the "clean uncached sweep"
recorded earlier in this file, and including the after-numbers above — should
treat it as **one sample**, not a measurement. Before concluding that a prompt
change helped or hurt any individual fixture, run it several times both ways and
look at the rate, not the outcome. The aggregate counts are more trustworthy than
any single fixture's verdict, and even they move by 3-4 items run to run.

This is also why 004 (`bogo`) and 015 (`bundle`) going from fail-fail to
pass-pass is **not** claimed as a benefit of this change. Both concern
`deal_type`, a field the change never touched. The likelier explanation is the
API recovering from the degraded window in which the before-runs were taken.

## Open, watch rather than act (2026-08-16)

Two single-asymmetry observations. Neither is acted on; both need several more
sweeps before they mean anything on a corpus this noisy. Revisit if either
persists.

### 007_yochi_chi_club_loyalty — `recurring: true` in 1 of 4 runs

Returned `recurring: True, days_of_week: []` in After-2 only; passed in B1, B2
and A1. Chi Club is a continuously-available loyalty program with nothing
resetting, so under the settled rule `false` is correct and A2 is wrong. One
occurrence in four. If it recurs it would suggest the daily-cycle example is
bleeding onto standing loyalty offers, which would be a real cost of the change —
but one occurrence is not evidence of that.

### 035_yobar_canberra_300_free — `channels` in 2 of 2 after-runs, 1 of 2 before

`channels: expected [] got ['dine_in', 'takeaway']`. The only asymmetry pointing
the wrong way: it failed both after-runs but only one before-run. Causation is
hard to argue — this is the channel-exclusion rule, which the change did not
touch, and the fixture was already unstable beforehand. Watch the rate across
future sweeps; 2/2 versus 1/2 is not a signal yet.
