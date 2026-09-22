# Notes on arguable calls

Everything below is a place where the caption does not settle the answer and I
had to choose. I have recorded the choice and the alternative rather than
picking one silently. If your pipeline disagrees on any of these, the fixture
is probably wrong for you, not the pipeline.

## Reconciliation applied (SPEC.md wins, 2026-08-04)

Two conventions in the original fixtures conflicted with SPEC.md and were
rewritten across all `.expected.json`. SPEC.md is authoritative.

1. `days_of_week` was lowercase day names; the schema column is `int[]` and
   SPEC.md sets `1` = Monday. Every value is now an integer array, Mon=1 to
   Sun=7. Affected: 002 `[1]`, 008 `[2]`, 010 `[5, 6, 7]`, 014 `[6, 7]`,
   016 `[1, 2, 3, 4, 5]`.
2. `channels` used `in_store`, `app`, `online`, `delivery`, `dine_in`. The
   vocabulary is now the SPEC.md set `dine_in`, `takeaway`, `app`, `delivery`.
   `in_store` was a catch-all for a physical purchase with no stated
   restriction, which is not the same as `dine_in`, so those became `[]` and
   the absence now means unrestricted. `app` and `dine_in` were already in the
   target set and were kept. No fixture used `online`, so no mapping for it was
   needed. Sixteen objects across fifteen files changed from `["in_store"]` to
   `[]`; 007 and 011 keep `["app"]`, 012 keeps `["dine_in"]`.

## Field conventions I assumed

These are not stated in the schema, so I fixed them and applied them
consistently. Change the fixtures if your pipeline defines them differently.

- `discount_unit` is `"percent"` or `"aud"`, and is null when no numeric
  discount applies (`bogo`, `freebie`, `loyalty`).
- `channels` uses `dine_in`, `takeaway`, `app`, `delivery` (the SPEC.md
  vocabulary). An empty array means no channel restriction: the offer is
  available on any channel, including an ordinary physical purchase. A caption
  with no channel language gets `[]`, not an inferred physical-channel token.
  See the reconciliation note below for the earlier convention this replaced.
- `days_of_week` holds integers, `1` = Monday through `7` = Sunday (ISO 8601,
  matching the schema `int[]` column), and is populated only when the offer is
  restricted to particular days on a repeating basis. A one-off dated offer
  that happens to land on a Friday gets `[]`, not `[5]`.
- `recurring` is true only for offers that repeat on a stated cycle. An
  open-ended standing offer with no cycle is false.
- Absent information is null. Nothing is inferred from outside the caption
  except the resolution of relative dates against `CAPTURE_DATE`.

## Per-fixture calls

**001, store_hint from context rather than statement.** The caption states no
channel, so `channels` is `[]` (unrestricted). More debatably, I populated
`store_hint` as "The District Docklands" from the hashtag `#districtdocklands`.
A hashtag is literally present in the caption, but treating hashtags as location
evidence is a policy decision. If you would rather hashtags never feed
`store_hint`, this should be null.

**holdout 032, store_hint from a suburb named in prose (unresolved, 2026-08-06).**
The froyolicious bottle-flip caption says "try docklands best froyo". The current
extractor set `store_hint` to "Docklands"; the hand label set it null. Both
readings are defensible and are recorded here rather than settled:
- **Null (the label that stands).** A business describing its own suburb in
  marketing copy is not naming a store, and froyolicious has a single location, so
  the hint carries no attribution information. Consistent with the 001 stance that
  promotional/hashtag location is not a store designator.
- **"Docklands" (the model's reading).** The suburb is literally present in prose
  (not just a hashtag) and would help fuzzy store matching where it matters.
The prompt is deliberately NOT changed for this. Revisit only if it recurs on a
multi-location chain, where attributing to the wrong branch (or failing to
attribute) actually costs something; a single-location business is the case where
the distinction is free to get wrong.

**002, 008, 010, 016, no channel stated.** None of these state a channel
restriction, so `channels` is `[]` for all of them. (Earlier drafts inferred
`["in_store"]` from the self-serve framing; the reconciliation below dropped
that inference.)

**003 and 005, single dates and short windows in days_of_week.** 003 runs on
one day, a Friday. 005 runs Monday to Wednesday. Both get `days_of_week: []`
with the dates carrying the restriction, on the convention above. A pipeline
that populates days whenever a day is identifiable would emit `[5]` and
`[1, 2, 3]`.

**004, discount_value for BOGO.** Left null. Some schemas encode buy-one-get-one
as `discount_value: 100, discount_unit: "percent"` on the second item, or as
`50` on the pair. The caption states a mechanic, not a number, so null. Note
the $12 value cap sits in `conditions`, not `max_grams`, since it caps dollars
rather than weight. There is no field for a dollar cap.

**006, recurring for an open-ended offer.** "every single day" is ongoing with
no end, so `recurring: false` and both dates null. Arguing the other way,
"every day" is a cycle and could be `recurring: true` with all seven days in
`days_of_week`. I think that overloads a field meant for restriction, but it
is a real reading.

SETTLED 2026-08-16, and 006 stands as labelled. The test is whether anything
RESETS. 006 is continuously available - the cake slice comes with every froyo,
always, nothing restarts - so there is no cycle, only the absence of an end
date. `recurring: false` is correct.

The instinct above about `days_of_week` was right and is now a rule: all seven
days is never correct. `days_of_week` states a RESTRICTION, so an offer
available every day is restricted to no weekdays and the field is `[]`. Listing
all seven asserts "restricted, to every day", which is a stronger claim than
"not restricted", and the source never made it. The two fields are independent:
`recurring` answers "does this come back", `days_of_week` answers "which
weekdays is it limited to". Frequency belongs to the first only.

**013, corrected: recurring is true.** Originally labelled `recurring: false`
by analogy with 006. That was my error, found while settling the rule above.
"free mini cup for the first customers in each day, while stocks last" is not
continuous availability: it has a fresh allocation every day and a per-day cap,
so miss it today and there is a new one tomorrow. That is a cycle, of period one
day. Expected output changed to `recurring: true`, `days_of_week: []` - it comes
back daily, and it is limited to no particular weekday.

This is a label correction, not a test being made to pass: the fixture now
encodes the distinction (does it reset?) rather than a surface reading of the
words "every day", which 006 and 013 share while meaning different things.

**a03 (ablation holdout), corrected: recurring is true.** Same class of label
error as 013, found by the same rule. The item is "Monday Mania 50% off" - a
promo that runs every Monday. That is a weekly cycle, which is the prompt's own
long-standing example of `recurring: true` ("every monday", "$6 tuesdays"), so
the original `false` contradicted a rule that predates this whole question.

`days_of_week: [1]` is unchanged and correct. Monday IS a genuine weekday
restriction here - the offer is unavailable Tuesday to Sunday - which is exactly
what the field is for. This is the case that shows the two fields are
independent in both directions: a03 is recurring AND restricted, 013 is
recurring and NOT restricted, 006 is neither.

The model had been returning `true` for a03 consistently (3 of 4 measured runs;
the fourth was an API failure, not a disagreement). The fixture was wrong, not
the extractor.

**007, the $10 in a loyalty earn rate.** "1 point for every $10 u spend" is an
accrual rate, not a threshold, so `min_spend_aud` is null and the rate lives in
`conditions`. A pipeline that pattern-matches dollar figures near "spend" will
emit `min_spend_aud: 10`, which I consider wrong but easy to fall into. This is
a useful adversarial case for exactly that bug.

**010, recurring with no dates.** "fri sat sun only" names days but no start or
end. I set `recurring: true` with the three days and null dates, matching the
treatment of `$6 tuesdays` in 008. The alternative is that this is a one-off
upcoming weekend and should resolve to dates against `CAPTURE_DATE`
(2026-11-05, a Thursday, so 6 to 8 November). The caption does not say
"this weekend", so I did not resolve it. Genuinely close.

**013, confidence and recurrence.** "first customers in each day" implies a
daily repeat but names no cycle boundary and no quantity. Left
`recurring: false`. Confidence is 0.62, deliberately just above the 0.6
threshold, so it pairs with 017 at 0.35 to bracket the boundary. If your
threshold logic is `<= 0.6` rather than `< 0.6` this fixture will need moving.

**015, second offer's validity window.** "all school holidays" is a real period
but the caption states neither dates nor which state's calendar. Both date
fields are null. Resolving it to Victorian term holiday dates would be
importing knowledge the caption does not contain, which the brief rules out.

**017, unit retained with a null value.** The caption establishes the offer is a
percentage but the number is illegible. I kept `discount_unit: "percent"` with
`discount_value: null`. A schema that forbids a unit without a value would
null both. Confidence 0.35 reflects the illegibility plus the unresolved
question of whether it applies only to small bowls.

**021, competition treated as a negative.** "win a $50 voucher" involves money
and an action, and a naive extractor may read it as a freebie. It is a prize
draw, not an offer available to a customer who walks in, so it extracts to
`[]`. If your product definition of "promotion" includes competitions, this
fixture flips from negative to positive and the expected array needs writing.

**024, expired deal treated as a negative.** The caption names a real deal
(`$5 cup`) but states it has ended. Expected `[]`. A pipeline that extracts
then filters on dates would produce an object here and discard it later; one
that extracts only live offers returns nothing. The fixture assumes the
latter. If yours is extract-then-filter, this belongs in a different test
layer.

**020, store_hint on a negative.** The opening announcement names Clyde North.
Since there is no offer, the whole array is empty and the location is not
captured anywhere. That is correct under this schema, but worth knowing if you
later want location extraction independent of offer extraction.

## A note on the real captions

Seven fixtures are grounded in promotions I verified against a live source, and
the source URL is in `MANIFEST.md` for each. In every one of the seven the caption
wording is mine: I verified the promotion's substance from the source and then
wrote the caption in the business's register rather than reproducing the post, so
the discount, dates and conditions are real while the phrasing is not. 001 and 005
originally carried a short verbatim fragment (including the source's own typo,
which was exactly the kind of noise worth having in a fixture set); both were
rewritten as synthetic equivalents for the public repository, keeping the offer
they encode intact. A deliberate misspelling was kept in 001 so the set still
exercises typo noise. `MANIFEST.md` records the provenance of each, so you are
never guessing whether a string is authentic.

If verbatim authenticity matters more than I have assumed here, the fix is to
collect the captions directly from the businesses' own accounts and drop them
in over the reconstructed text. The expected JSON for those five was written
from the promotion's actual terms, so it should mostly survive the swap, though
you would want to re-check `channels` and `store_hint` against the real
wording.
