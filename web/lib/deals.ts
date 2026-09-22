import { unstable_noStore as noStore } from "next/cache";

import { pool } from "@/lib/db";
import { type DupeRow, type DuplicateHint, findDuplicatesFor } from "@/lib/dedupe";

// These read live, externally-mutated data (the nightly merge/expire jobs and the
// mutation routes change deals out of band), so every read must be uncached. The
// pages are already force-dynamic; noStore() is the explicit per-read guarantee
// Next recommends for non-fetch (DB) sources, and protects the data even if a
// route ever loses its dynamic flag.

export type QueueDeal = {
  id: number;
  headline: string;
  deal_type: string;
  discount_value: string | null;
  discount_unit: string | null;
  conditions: string | null;
  min_spend_cents: number | null;
  max_grams: number | null;
  channels: string[] | null;
  days_of_week: number[] | null;
  valid_from: string | null;
  valid_to: string | null;
  recurring: boolean;
  confidence: string | null;
  status: string;
  chain_id: number | null;
  raw_capture_id: number | null;
  content_text: string | null;
  image_path: string | null;
  capture_source_type: string | null;
  captured_at: string | null;
  // What the submitter typed into /submit's "Which shop" field. Structured since
  // migration 0010; before that it was concatenated into content_text.
  submitted_store: string | null;
  // The place the source named, if any. The extractor has always read this; it
  // was written and never shown, because resolve_store drops it when no store
  // matches (and the stores table is empty until Phase 9). It is the evidence
  // behind `scope`, so the reviewer can check the call rather than trust it.
  store_hint_raw: string | null;
  // Derived city scope. 'other' means the source named a city that is not
  // Melbourne, so approving it will not publish it - see the banner in /review.
  scope: string;
  // Attached at read time: other pending/approved deals this may duplicate.
  possibleDuplicates: DuplicateHint[];
};

// The candidate pool a pending deal is matched against.
//
// EXPIRED DEALS BELONG HERE. Do not re-exclude them. Most chains run the same
// promo on a cycle and post it again each time it comes round, so the thing a
// new capture most often duplicates is *last cycle's run*, which by definition
// expired before the repost arrived. Excluding expired meant the hint went quiet
// in precisely the case it exists for: deal 175 was a re-scrape of the identical
// Instagram post as deal 114, and it reached the queue eight hours after the
// nightly expire job retired 114, so nothing was flagged and it was rejected by
// hand. Expired is not dead, it is history, and history is what a repost repeats.
//
// Rejected stays out. A rejected deal was judged not to be a real deal, so
// nothing can meaningfully be a duplicate of it.
//
// Already-superseded deals stay out too. They are never a valid merge target:
// the route resolves any target through coalesce(superseded_by, id), so picking
// one silently acts on its canonical instead - a button labelled with an id it
// will not use. Offering them also multiplied the candidate list, since a merged
// group contributes every member (seven chips for blu spoon's 50% off, five of
// them resolving to the same #119).
async function getDedupePool(): Promise<DupeRow[]> {
  const { rows } = await pool.query(
    `select d.id, d.chain_id, d.deal_type, d.discount_value::float8 as discount_value,
            to_char(d.valid_from, 'YYYY-MM-DD') as valid_from,
            to_char(d.valid_to, 'YYYY-MM-DD') as valid_to,
            d.headline, d.raw_capture_id, d.scope
     from deals d
     where d.status in ('pending', 'approved', 'expired')
       and d.superseded_by is null`
  );
  return rows;
}

// Lowest confidence first: the deals most in need of a human are at the top.
// Each pending deal is annotated with possible duplicates from the pool.
export async function getPendingDeals(): Promise<QueueDeal[]> {
  noStore();
  const [{ rows }, poolRows] = await Promise.all([
    pool.query(
      `select d.id, d.headline, d.deal_type, d.discount_value, d.discount_unit,
              d.conditions, d.min_spend_cents, d.max_grams, d.channels, d.days_of_week,
              to_char(d.valid_from, 'YYYY-MM-DD') as valid_from,
              to_char(d.valid_to, 'YYYY-MM-DD') as valid_to,
              d.recurring, d.confidence, d.status, d.scope, d.store_hint_raw,
              d.chain_id, d.raw_capture_id,
              r.content_text, r.image_path, r.source_type as capture_source_type,
              r.submitted_store,
              to_char(r.captured_at, 'YYYY-MM-DD') as captured_at
       from deals d
       join raw_captures r on r.id = d.raw_capture_id
       where d.status = 'pending' and d.superseded_by is null
       order by (case when r.source_type = 'user_submission' then 0 else 1 end),
                d.confidence asc nulls first, d.id asc`
    ),
    getDedupePool(),
  ]);
  return rows.map((d) => ({
    ...d,
    possibleDuplicates: findDuplicatesFor(
      {
        id: d.id,
        chain_id: d.chain_id,
        deal_type: d.deal_type,
        discount_value: d.discount_value == null ? null : Number(d.discount_value),
        valid_from: d.valid_from,
        valid_to: d.valid_to,
        headline: d.headline,
        raw_capture_id: d.raw_capture_id,
        scope: d.scope,
      },
      poolRows
    ),
  }));
}

// Superseded deals are excluded from every count. A duplicate keeps its status
// (the "duplicate of" action sets superseded_by and nothing else), so counting
// raw status made the header claim a pending backlog the queue does not contain
// - it read "pending 12" against a queue of 2. Each number here now matches the
// set of deals it names: pending is what the queue will actually show you,
// approved is what the public dashboard will actually render.
export async function countByStatus(): Promise<Record<string, number>> {
  noStore();
  const { rows } = await pool.query(
    `select status, count(*)::int as n from deals where superseded_by is null group by status`
  );
  return Object.fromEntries(rows.map((r) => [r.status, r.n]));
}

export type ActiveDeal = {
  id: number;
  headline: string;
  deal_type: string;
  discount_value: string | null;
  discount_unit: string | null;
  unit_basis: string | null;
  category: string | null;
  // 'melbourne' or 'unknown' only: getActiveDeals never returns 'other'.
  scope: string;
  conditions: string | null;
  min_spend_cents: number | null;
  max_grams: number | null;
  channels: string[] | null;
  days_of_week: number[] | null;
  valid_from: string | null;
  valid_to: string | null;
  recurring: boolean;
  last_verified: string | null;
  chain_name: string | null;
  store_id: number | null;
  suburb: string | null;
  // Whether the reverify job can ever touch this deal. It keys on exactly what
  // reverify.py keys on (a non-null source_url), so a deal with nothing to
  // re-fetch is never described as merely unchecked. The URL itself is never
  // selected: this is a public surface and the boolean is all it needs.
  recheckable: boolean;
  // When the evidence was gathered, in Melbourne time. For a deal nobody can
  // re-check, last_verified is only the date the operator got round to approving
  // it, which overstates freshness by an unbounded review lag.
  seen_at: string | null;
};

export type DealFilters = {
  category?: string;
  chain?: string;
  deal_type?: string;
  day?: string;
  suburb?: string;
};

// Active = approved. Default sort last_verified desc (freshest first, unverified
// last). A day filter matches deals restricted to that weekday plus deals with
// no day restriction (available any day).
export async function getActiveDeals(f: DealFilters): Promise<ActiveDeal[]> {
  noStore();
  // scope <> 'other' is NOT a filter and is deliberately not parameterised: a
  // deal for a store in another city has no honest place on a Melbourne
  // dashboard, under any toggle. The Everything toggle widens `category`, which
  // is a different axis - a labelled non-froyo deal is still a deal you can walk
  // to, whereas a Canberra one is not. 'unknown' IS returned, and the page marks
  // it, because hiding it would silently drop the largest chains and losing a
  // real deal is the other half of the product's promise.
  const where = ["d.status = 'approved'", "d.superseded_by is null", "d.scope <> 'other'"];
  const params: unknown[] = [];
  // Default to froyo; "all" widens to every category.
  if (f.category && f.category !== "all") {
    params.push(f.category);
    where.push(`d.category = $${params.length}`);
  }
  if (f.chain) {
    params.push(f.chain);
    where.push(`ch.name = $${params.length}`);
  }
  if (f.deal_type) {
    params.push(f.deal_type);
    where.push(`d.deal_type = $${params.length}`);
  }
  if (f.day) {
    params.push(Number(f.day));
    where.push(`($${params.length} = ANY(d.days_of_week) OR cardinality(coalesce(d.days_of_week, '{}')) = 0)`);
  }
  if (f.suburb) {
    params.push(f.suburb);
    where.push(`s.suburb = $${params.length}`);
  }
  const { rows } = await pool.query(
    `select d.id, d.headline, d.deal_type, d.category, d.scope, d.discount_value, d.discount_unit,
            d.unit_basis, d.conditions, d.min_spend_cents, d.max_grams, d.channels,
            d.days_of_week,
            to_char(d.valid_from, 'YYYY-MM-DD') as valid_from,
            to_char(d.valid_to, 'YYYY-MM-DD') as valid_to,
            d.recurring,
            to_char(d.last_verified, 'YYYY-MM-DD') as last_verified,
            ch.name as chain_name, d.store_id, s.suburb,
            (d.source_url is not null) as recheckable,
            to_char(rc.captured_at at time zone 'Australia/Melbourne', 'YYYY-MM-DD') as seen_at
     from deals d
     left join chains ch on ch.id = d.chain_id
     left join stores s on s.id = d.store_id
     left join raw_captures rc on rc.id = d.raw_capture_id
     where ${where.join(" and ")}
     order by d.last_verified desc nulls last, d.id desc`,
    params
  );
  return rows;
}

export type SupersededDeal = {
  id: number;
  headline: string;
  deal_type: string;
  discount_value: string | null;
  valid_from: string | null;
  valid_to: string | null;
  source_url: string | null;
  chain_name: string | null;
  superseded_by: number;
  canonical_headline: string | null;
};

// Deals merged into a canonical duplicate. Shown under a filter in /review so the
// merge can be inspected and undone; excluded from the public dashboard.
export async function getSupersededDeals(): Promise<SupersededDeal[]> {
  noStore();
  const { rows } = await pool.query(
    `select d.id, d.headline, d.deal_type, d.discount_value,
            to_char(d.valid_from, 'YYYY-MM-DD') as valid_from,
            to_char(d.valid_to, 'YYYY-MM-DD') as valid_to,
            d.source_url, ch.name as chain_name,
            d.superseded_by, c.headline as canonical_headline
     from deals d
     left join chains ch on ch.id = d.chain_id
     left join deals c on c.id = d.superseded_by
     where d.superseded_by is not null
     order by d.superseded_by, d.id`
  );
  return rows;
}

export type DealSearchResult = {
  id: number;
  headline: string;
  chain_name: string | null;
  status: string;
  deal_type: string;
  scope: string;
};

// Candidates a pending deal can be marked a duplicate of: non-superseded
// approved/pending/expired deals matching by headline or exact id. Used by the
// "duplicate of" picker when the right canonical is not among the flagged hints.
//
// Expired is included for the same reason it is in getDedupePool: a repost's
// canonical is usually the previous run, which has expired by the time the
// repost lands. Note the status gate also covered the id branch, so before this
// change typing an expired deal's id returned nothing either - the reviewer who
// already knew the right answer still could not enter it. The picker shows each
// result's status, so an expired candidate is chosen knowingly.
export async function searchDeals(q: string): Promise<DealSearchResult[]> {
  noStore();
  const asId = Number(q);
  const { rows } = await pool.query(
    `select d.id, d.headline, ch.name as chain_name, d.status, d.deal_type, d.scope
     from deals d
     left join chains ch on ch.id = d.chain_id
     where d.status in ('approved', 'pending', 'expired') and d.superseded_by is null
       and (d.headline ilike $1 or ($2::bigint is not null and d.id = $2::bigint))
     order by d.id desc
     limit 20`,
    [`%${q}%`, Number.isInteger(asId) ? asId : null]
  );
  return rows;
}

export async function getFilterOptions() {
  noStore();
  const [chains, suburbs] = await Promise.all([
    pool.query(`select name from chains order by name`),
    pool.query(
      `select distinct s.suburb from deals d join stores s on s.id = d.store_id
       where d.status = 'approved' and d.superseded_by is null and s.suburb is not null
       order by s.suburb`
    ),
  ]);
  return {
    chains: chains.rows.map((r) => r.name as string),
    suburbs: suburbs.rows.map((r) => r.suburb as string),
    dealTypes: ["percent_off", "dollar_off", "fixed_price", "bogo", "freebie", "loyalty", "bundle"],
  };
}
