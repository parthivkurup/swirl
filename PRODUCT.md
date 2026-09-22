# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary: the operator (a single person, the owner).** Triages the review queue
at `/review` on a laptop, keyboard-driven, in batches. Decides what becomes
public. Holds the only account; auth is a single shared admin password with a
signed cookie session, no user accounts and no roles.

**Secondary: friends and word-of-mouth visitors.** A small, non-anonymous
audience given the link. Two situations, both real:

- on a phone, out and about, deciding where to go now;
- on a desktop, browsing and planning rather than deciding in the moment.

Not a public, cold-traffic site. Nobody arrives from search, so the surfaces do
not have to sell the product to strangers, but they do have to be trusted by
people who will tell the owner when something is wrong.

**Tertiary: submitters.** Anyone with the link can post a photo of an in-store
promo sign through `/submit` without logging in. Submissions never auto-approve.

## Product Purpose

Track frozen yoghurt promotions across Melbourne so that the deals available
right now are findable in one place. Deals are the product; store data and menu
prices are supporting features, deliberately built last.

Success has two halves, and both were named by the owner:

1. **Everything shown is true.** Nothing fabricated, nothing inferred that the
   source did not state, staleness disclosed rather than hidden, every deal
   traceable to the capture it came from.
2. **Nobody misses a deal.** Comprehensive coverage of real Melbourne froyo
   promos, with duplicates merged rather than deleted, so a promo is never
   silently lost.

Where the two halves conflict, truth wins.

## Positioning

A human-reviewed deal record, not an aggregated feed. Every promo passes through
a two-stage pipeline (scrapers write immutable captures, an LLM extractor turns
captures into structured pending deals) and then through a person before it is
public. The only automatic path to publication is a high-confidence extraction
from a chain's own promo page; Instagram and user submissions always wait for a
human.

That is the thing a neighbouring product could not truthfully copy: coverage of
a niche too small to be worth scraping at scale, compiled from sources that
disagree with each other, reconciled by someone who checks.

## Operating Context

- **Scheduled, unattended ingestion on the owner's own machine.** launchd agents
  run the website and Instagram scrapes plus one extract at 08:30 and 18:30, and
  the expire / reverify / merge jobs at 03:35. Postgres runs in local Docker, so
  a run is skipped cleanly when Docker is down.
- **Instagram captures come from a private ingestion source.** It is read-only
  and not part of this repository; the public tree carries the interface stub, the
  monitored-account list, the dedupe and the high-water table. Three consecutive
  failed runs disable it and log an incident, because a source that returns nothing
  must not read as a healthy run.
- **Deployment (decided 2026-08-09).** Vercel for the web app, Neon for
  Postgres, with the scrapers, extractor and nightly jobs staying on the owner's
  Mac under launchd, which is where ingestion has to run. An
  earlier Binary Lane VPS plan is cancelled. Vercel's filesystem is ephemeral,
  so local media storage does not work there: `/api/submit` (which spawns the
  repo's Python venv) and `/api/image` (which reads files under `MEDIA_ROOT`)
  both need rework before the submission path can run on Vercel.
- **Review happens in batches, after a scrape.** The queue is worked down with
  `j` `k` `a` `r` shortcuts; each item shows the raw capture (including the
  source image) beside every extracted field, all editable.
- **Sources disagree and are often thin.** Many chains have no website, only an
  Instagram account; some have no readable promo page; some could not be
  verified at all. The research file records `null` where a fact was not
  confirmed, and that discipline is load-bearing.

## Capabilities and Constraints

**Surfaces that exist**

- `/` public dashboard: active approved deals in one ranked column, banded by
  availability (available today and ending soon, available today, other days,
  not checked in 14 days, ended). The only control is a froyo / everything
  toggle; category defaults to froyo. Deals not verified in 14 days render
  greyed with the date visible rather than hidden.
- `/review` operator queue: capture beside extracted fields, approve, reject,
  edit-and-approve, mark as duplicate of another deal (supersede, never delete),
  plus a collapsed superseded list with undo.
- `/submit` public photo submission. `/login` operator auth.

**Rules that must not drift**

- Auto-approve only when confidence >= 0.8 and the source is a chain website.
  Everything else, including every user submission, stays pending.
- Approved images stay non-public. Source images are reviewer evidence served
  only to an authenticated reviewer via `/api/image`; approving a deal does not
  publish its photo. User photos are untrusted pixels and can show faces,
  plates, and house numbers that metadata stripping does not remove.
- Location is stated honestly: a named store when one is known, otherwise
  "all <chain> locations" when only the chain is known, otherwise nothing at
  all. Never a placeholder.
- Captures are permanent evidence and scrapers never write deals, so extraction
  can be re-run over history when the prompt changes.
- Duplicates are superseded, never deleted, and a promo must never end up with
  no live representative.
- No em dashes anywhere: code, prose, or UI copy.
- Structured JSON logging to stdout for every scrape and extract.

**Terminology** (use these words in UI copy): capture, deal, chain, store,
pending / approved / rejected / expired, superseded, stale, recurring,
unit basis (per 100g, per kg, each, per serve), category (froyo, adjacent,
other), channel (in store, Uber Eats, DoorDash, Menulog).

**Not built, and not to be implied as built**

- Phase 9 (stores and prices) is deferred: no store-level display, no menu
  prices, no `/stores` page, no map.
- Melbourne only. A Geelong location was explicitly excluded as out of scope.

## Brand Commitments

No name, logo, wordmark, or identity asset. "Melbourne froyo" is a working
title the owner is open to changing, and naming is an open decision rather than
an absent one.

**Standing aesthetic preference (confirmed 2026-08-09).** Asked to choose a
visual world for the public dashboard, the owner re-rolled three dealt
directions and then chose convention over concept: no metaphor, no borrowed
visual world, no clever naming. The craft bar is Linear, Vercel, and Raycast.
Colour strategy is one accent on a mostly neutral ground. Future surfaces
inherit this unless the owner says otherwise; a proposal that dresses this
product in a world is a proposal they have already declined three times.

Voice: plain, factual, no persuasion, no em dashes.

## Evidence on Hand

- `config/chains.yaml`: 19 researched Melbourne froyo businesses with sourcing
  notes, location counts, Instagram handles, and promo URLs. Unverified fields
  are `null` on purpose, with the reason written out.
- `tests/fixtures/captions/`: paired `.txt` and `.expected.json` extractor
  fixtures, including negatives that must return `[]`.
- A live Postgres database of real captures and reviewed deals (roughly 18 live
  approved deals at the last logged count), plus real submitted photos under
  `media/`.
- `SPEC.md`, `PROGRESS.md`, and `DEFERRED.md` record every phase decision and
  every knowingly deferred limitation.

**Absences future work must not fabricate:** no testimonials, no user counts, no
traffic or engagement numbers, no press, no partnerships or chain relationships,
no pricing or menu data, no store addresses in the product surface, no coverage
claim beyond what `chains.yaml` actually verifies.

## Product Principles

1. **Truth outranks completeness.** An unverified fact is shown as unknown or
   not shown at all. Absence is stated, never filled in.
2. **Nothing reaches the public unreviewed**, except a high-confidence
   extraction from a chain's own page. The reviewer is the product's quality
   floor, so operator speed is a product concern, not just an ergonomic one.
3. **Staleness is disclosed, not hidden.** An old deal stays visible and marked
   rather than disappearing, because a visitor standing outside a shop needs to
   know the difference between "no deal" and "we have not checked lately".
4. **Never lose a promo.** Deduplicate by superseding with an undo, never by
   deleting, and never leave a real promo with no live representative.
5. **Evidence is immutable, interpretation is not.** Captures are kept forever
   so extraction can be re-run when the prompt improves.
