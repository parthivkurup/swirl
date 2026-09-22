// Query-time near-duplicate detection for the review queue. Surfaces "possible
// duplicate of deal N" as a hint for the reviewer to decide; never auto-merges.
// Computed at read time (not stored) so it stays correct as deals are approved,
// edited, or expired, and so it naturally spans sources (the same promo posted to
// Instagram and a website).

export type DupeRow = {
  id: number;
  chain_id: number | null;
  deal_type: string | null;
  discount_value: number | null;
  valid_from: string | null; // 'YYYY-MM-DD' or null (open-ended)
  valid_to: string | null;
  headline: string | null;
  raw_capture_id: number | null;
  scope?: string | null;
};

export type DuplicateHint = { id: number; headline: string };

// Headline-similarity gates. A shared, equal discount_value is already a strong
// identity signal, so a valued pair needs only weak headline agreement; a
// null-value pair (freebie/bogo/loyalty carry no number) leans entirely on the
// headline, so it must clear a higher bar. This is what separates "first 30"
// from "first 300" when neither has a discount_value.
export const SIM_VALUED = 0.35;
export const SIM_NULL_VALUE = 0.6;

export function normHeadline(s: string | null): string {
  return (s ?? "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
}

function bigrams(s: string): Map<string, number> {
  const m = new Map<string, number>();
  for (let i = 0; i < s.length - 1; i++) {
    const g = s.slice(i, i + 2);
    m.set(g, (m.get(g) ?? 0) + 1);
  }
  return m;
}

// Dice coefficient over character bigrams: 1.0 identical, 0 disjoint.
export function similarity(a: string, b: string): number {
  if (a === b) return a.length ? 1 : 0;
  if (a.length < 2 || b.length < 2) return 0;
  const A = bigrams(a);
  const B = bigrams(b);
  let inter = 0;
  let total = 0;
  for (const [g, n] of A) {
    total += n;
    const bn = B.get(g);
    if (bn) inter += Math.min(n, bn);
  }
  for (const [, n] of B) total += n;
  return (2 * inter) / total;
}

// null chain_id is a wildcard: an unattributed deal can still duplicate a
// chained one. (The 19 legacy Instagram deals have null chain_id, so without
// this they could never match each other.)
function chainCompatible(a: number | null, b: number | null): boolean {
  return a == null || b == null || a === b;
}

// Two deals for different cities are not the same deal, however identical their
// wording. A national chain runs one promo in several cities and posts it once
// per city, so without this the Melbourne and Canberra copies look like perfect
// duplicates - and merging the Melbourne one INTO the Canberra one would hide a
// real, actionable deal behind a row the dashboard refuses to publish.
// 'unknown' stays compatible with everything: it means we do not know, and
// blocking on it would strand exactly the reposts this matcher exists to catch.
function scopeCompatible(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a || !b) return true;
  if (a === "unknown" || b === "unknown") return true;
  return a === b;
}

function valueCompatible(a: number | null, b: number | null): boolean {
  if (a == null && b == null) return true;
  if (a == null || b == null) return false;
  return a === b;
}

// null valid_from = open start (-infinity), null valid_to = open end (+infinity).
export function windowsOverlap(
  aFrom: string | null,
  aTo: string | null,
  bFrom: string | null,
  bTo: string | null
): boolean {
  const startOk = aFrom == null || bTo == null || aFrom <= bTo;
  const endOk = bFrom == null || aTo == null || bFrom <= aTo;
  return startOk && endOk;
}

export function isPossibleDuplicate(a: DupeRow, b: DupeRow): boolean {
  if (a.id === b.id) return false;
  // Same post yields multiple offers legitimately (a bogo and a step-goal
  // freebie in one caption); those are not duplicates of each other.
  if (a.raw_capture_id != null && a.raw_capture_id === b.raw_capture_id) return false;
  if (!a.deal_type || a.deal_type !== b.deal_type) return false;
  if (!chainCompatible(a.chain_id, b.chain_id)) return false;
  if (!scopeCompatible(a.scope, b.scope)) return false;
  if (!valueCompatible(a.discount_value, b.discount_value)) return false;
  if (!windowsOverlap(a.valid_from, a.valid_to, b.valid_from, b.valid_to)) return false;
  const bothValued = a.discount_value != null && b.discount_value != null;
  const threshold = bothValued ? SIM_VALUED : SIM_NULL_VALUE;
  return similarity(normHeadline(a.headline), normHeadline(b.headline)) >= threshold;
}

export function findDuplicatesFor(target: DupeRow, pool: DupeRow[]): DuplicateHint[] {
  return pool
    .filter((c) => isPossibleDuplicate(target, c))
    .map((c) => ({ id: c.id, headline: c.headline ?? "" }));
}
