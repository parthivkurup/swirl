# Fixture manifest

31 fixtures in `captions/`, 19 positive and 12 negative. Each has a `.txt`
caption and a `.expected.json` holding a JSON array of extracted offer
objects. Negatives expect `[]`. 001-030 are the original set; 031 was added later
as a regression fixture (see PROGRESS.md) and is included below.

## Provenance categories

- **real (facts verified, wording reconstructed)** - the promotion is real and
  the source was recorded when the fixture was written, but the caption wording
  here is written by me in the business's register rather than copied from the
  post. The discount, dates, caps and conditions match the source. The `Source`
  column reads `private`: links to individual posts are not published here.
- **synthetic** - invented promotion and invented wording.

**No fixture in `captions/` reproduces a real post's wording.** Two of them (001,
005) originally carried a verbatim fragment of the source post; both captions were
rewritten as synthetic equivalents for the public repository, preserving the offer
they encode (value, dates, conditions, confidence band) so the expected output is
unchanged in substance. Their `Provenance` below reads "facts verified, wording
reconstructed" like the other real-promotion fixtures.

See `NOTES.md` for calls that are genuinely arguable.

## Fixtures

| Fixture | CAPTURE_DATE | Expected | Provenance | Source | Hard case |
|---|---|---|---|---|---|
| `001_froyolicious_15_off` | 2026-04-02 | positive (1) | real (facts verified, wording reconstructed) | private | - |
| `002_yochi_monday_20` | 2026-02-05 | positive (1) | real (facts verified, wording reconstructed) | private | recurring weekday deal, but with explicit outer dates |
| `003_chillpit_flat_ten` | 2026-02-04 | positive (1) | real (facts verified, wording reconstructed) | private | store_hint; relative date resolved from CAPTURE_DATE |
| `004_yobar_mothers_day_bogo` | 2026-05-07 | positive (1) | real (facts verified, wording reconstructed) | private | relative date resolved from CAPTURE_DATE |
| `005_yobar_neapolitan_30` | 2026-07-10 | positive (1) | real (facts verified, wording reconstructed) | private | - |
| `006_justcraveit_free_cake` | 2026-06-18 | positive (1) | real (facts verified, wording reconstructed) | private | store_hint; open-ended standing offer |
| `007_yochi_chi_club_loyalty` | 2026-01-22 | positive (1) | real (facts verified, wording reconstructed) | private | app channel |
| `008_six_dollar_tuesdays` | 2026-03-03 | positive (1) | synthetic | n/a | recurring weekday deal with no explicit dates |
| `009_two_off_200g_cap` | 2026-09-12 | positive (1) | synthetic | n/a | weight cap |
| `010_three_off_min_spend` | 2026-11-05 | positive (1) | synthetic | n/a | minimum spend |
| `011_app_only_ten` | 2026-08-21 | positive (1) | synthetic | n/a | app-only channel restriction |
| `012_dine_in_bogo` | 2026-02-19 | positive (1) | synthetic | n/a | dine-in-only channel restriction |
| `013_while_stocks_last` | 2026-05-28 | positive (1) | synthetic | n/a | vague expiry leaves valid_to null |
| `014_this_weekend_25` | 2026-10-16 | positive (1) | synthetic | n/a | relative date resolved against CAPTURE_DATE |
| `015_double_offer` | 2026-04-25 | positive (2) | synthetic | n/a | two distinct offers in one caption |
| `016_glen_waverley_bundle` | 2026-07-02 | positive (1) | synthetic | n/a | store_hint from named location |
| `017_smudged_sign` | 2026-06-06 | positive (1) | synthetic | n/a | ambiguous / partly illegible, confidence below 0.6 |
| `018_stamp_card` | 2026-12-03 | positive (1) | synthetic | n/a | - |
| `019_new_flavour` | 2026-01-15 | negative | synthetic | n/a | negative: new flavour announcement |
| `020_store_opening` | 2026-03-27 | negative | synthetic | n/a | negative: store opening |
| `021_tag_and_follow_comp` | 2026-08-08 | negative | synthetic | n/a | negative: competition requiring tag-and-follow entry |
| `022_job_ad` | 2026-04-09 | negative | synthetic | n/a | negative: job ad |
| `023_public_holiday_hours` | 2026-06-05 | negative | synthetic | n/a | negative: public holiday trading hours notice |
| `024_expired_deal` | 2026-02-25 | negative | synthetic | n/a | negative: expired past deal |
| `025_generic_brand` | 2026-11-20 | negative | synthetic | n/a | negative: generic brand advertising, no offer |
| `026_follower_milestone` | 2026-05-14 | negative | synthetic | n/a | negative: milestone thanks |
| `027_supplier_visit` | 2026-09-30 | negative | synthetic | n/a | negative: supplier / sourcing post |
| `028_hot_day` | 2026-12-19 | negative | synthetic | n/a | negative: weather / vibe post |
| `029_temp_closure` | 2026-07-23 | negative | synthetic | n/a | negative: temporary closure notice |
| `030_customer_repost` | 2026-10-02 | negative | synthetic | n/a | negative: user generated content repost |
| `031_instore_only_per_100g` | 2026-09-09 | positive (1) | synthetic | n/a | regression: per-100g pricing plus channel exclusions (app / delivery) |

## Deal type coverage across the 20 positive objects

| deal_type | count | fixtures |
|---|---|---|
| percent_off | 6 | 001, 002, 005, 014, 015 (first object), 017 |
| dollar_off | 2 | 009, 010 |
| fixed_price | 4 | 003, 008, 011, 031 |
| bogo | 2 | 004, 012 |
| freebie | 2 | 006, 013 |
| loyalty | 2 | 007, 018 |
| bundle | 2 | 015 (second object), 016 |

Fixture 015 is the only caption producing two objects, so 19 positive captions
yield 20 objects.

## Required hard cases

| Hard case | Fixture |
|---|---|
| Recurring weekday deal, no explicit dates | 008 (`$6 tuesdays`) |
| Weight cap | 009 (`up to 200g`) |
| Minimum spend | 010 (`spend $15 or more`) |
| App-only channel | 011 |
| Dine-in-only channel | 012 |
| Vague expiry, `valid_to` stays null | 013 (`while stocks last`) |
| Relative date resolved against CAPTURE_DATE | 014 (`this weekend only`); also 003, 004, 012 |
| Two offers in one caption | 015 |
| Named store location populating store_hint | 016; also 003, 006 |
| Ambiguous / illegible, confidence below 0.6 | 017 (0.35); 013 sits at 0.62 |

## Required negative categories

| Category | Fixture |
|---|---|
| New flavour announcement | 019 |
| Store opening | 020 |
| Competition with tag-and-follow entry | 021 |
| Job ad | 022 |
| Public holiday trading hours | 023 |
| Expired past deal | 024 |
| Generic brand advertising | 025 |

Fixtures 026 to 030 are additional negatives: follower milestone, supplier
visit, hot weather post, temporary closure, and a customer content repost.

## Natural holdout (031-041)

**Private set, not in this repository.** The eleven natural holdout captions
reproduce real posts verbatim, so their `.txt` / `.expected.json` pairs are held
outside the public tree; `tests/test_holdout.py` skips each item when its caption
is absent. `HOLDOUT.md` keeps the analysis and the recorded results.

## Ablation holdout (synthetic image-only extraction test, 2026-08-06)

The 90 Instagram captures contain NO natural image-only promo (census: all 19
priced deals state their value in the caption text; all 52 thin/decorative
no-deal images are non-promo). To measure image reading at all, each item below
pairs a REAL promo image (offer legibly rendered in the graphic) with a SYNTHETIC
decorative caption carrying no offer, forcing extraction onto the image. Labelled
from the image alone. **The four images are a private set and are NOT in this
repository**, so these items cannot be scored here: tests/test_ablation.py skips
each one whose image is absent rather than running it caption-only, which would
score a false miss. Place an image at `tests/fixtures/holdout/<label>.jpg` to run
that item. The ablation (real caption replaced with the decorative line) is recorded
per row; the original real captions live in `raw_captures`, and a02/a04 are the
same promos that appear with full captions as holdout `034`/`035`.

| Item | Source capture | Offer rendered in image | Ablated caption (synthetic) | Image-read result |
|---|---|---|---|---|
| `a01_justcraveit_499_imageonly` | private | "$4.99 UNLIMITED FROYO & TOPPINGS" | "swirl season is officially open ✨🍦" | READ (exact) |
| `a02_yomg_3per100g_imageonly` | private | "$3 per 100 grams today" | "self-serve szn 🥄" | READ (exact; resolved "today"→capture_date) |
| `a03_bluspoon_50off_imageonly` | private | "MONDAY MANIA … 50%" (cropped) | "blu spoon kind of mood 💙" | READ (exact, incl Monday-only) |
| `a04_yobar_300free_imageonly` | private (same promo as holdout 035, ablated) | "YO CANBERRA 300 FREE BOWLS" | "the wait is nearly over 🎉" | MISS (produced no deal) |

First measured image-reading result: **3/4 offers read from the image, 1 miss.**
The three hits all carry a $ or % in the graphic; the miss is the non-priced
freebie. a04 vs holdout 035 (same image, real caption → extracted) isolates the
failure to image reading of a non-priced offer. Prompt NOT tuned.
