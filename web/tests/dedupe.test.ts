import assert from "node:assert";
import test from "node:test";

import {
  type DupeRow,
  findDuplicatesFor,
  isPossibleDuplicate,
  similarity,
  windowsOverlap,
} from "../lib/dedupe.ts";

function row(o: Partial<DupeRow>): DupeRow {
  return {
    id: 0,
    chain_id: null,
    deal_type: "percent_off",
    discount_value: null,
    valid_from: null,
    valid_to: null,
    headline: "",
    raw_capture_id: null,
    ...o,
  };
}

const fiftyOff = (id: number, cap: number) =>
  row({
    id,
    deal_type: "percent_off",
    discount_value: 50,
    headline: "50% off Frozen Yogurt",
    valid_from: "2026-07-20",
    valid_to: "2026-08-10",
    raw_capture_id: cap,
  });

test("identical valued deals from different posts are duplicates", () => {
  assert.equal(isPossibleDuplicate(fiftyOff(119, 72), fiftyOff(120, 75)), true);
});

test("a deal is never a duplicate of itself", () => {
  assert.equal(isPossibleDuplicate(fiftyOff(119, 72), fiftyOff(119, 72)), false);
});

test("two offers from the SAME post are not duplicates of each other", () => {
  const a = row({ id: 129, deal_type: "bogo", raw_capture_id: 500, headline: "BOGO for 10k steps" });
  const b = row({ id: 130, deal_type: "bogo", raw_capture_id: 500, headline: "BOGO for 10k steps" });
  assert.equal(isPossibleDuplicate(a, b), false);
});

test("null chain_id is a wildcard; different chains never match", () => {
  const a = row({ id: 131, deal_type: "fixed_price", discount_value: 3, chain_id: 4,
    headline: "$3 per 100 grams frozen yogurt", valid_from: "2026-08-05", valid_to: "2026-08-05", raw_capture_id: 129 });
  const bNull = row({ ...a, id: 132, chain_id: null, headline: "Frozen yogurt for $3 per 100g", raw_capture_id: 130 });
  const bOther = row({ ...bNull, chain_id: 9 });
  assert.equal(isPossibleDuplicate(a, bNull), true);   // null wildcard + valued
  assert.equal(isPossibleDuplicate(a, bOther), false); // chain 4 vs 9
});

test("value mismatch and non-overlapping windows both block", () => {
  assert.equal(isPossibleDuplicate(fiftyOff(1, 1), row({ ...fiftyOff(2, 2), discount_value: 40 })), false);
  const jun = row({ id: 117, deal_type: "freebie", headline: "First 30 bowls free", valid_from: "2026-06-20", valid_to: "2026-06-20", raw_capture_id: 63 });
  const aug = row({ id: 114, deal_type: "freebie", headline: "First 30 bowls free", valid_from: "2026-08-08", valid_to: "2026-08-08", raw_capture_id: 42 });
  assert.equal(isPossibleDuplicate(jun, aug), false); // identical text, disjoint windows
});

test("null-value pair needs a strong headline match", () => {
  const a = row({ id: 114, deal_type: "freebie", headline: "Free bowl for the first 300 customers in line", valid_from: "2026-08-08", valid_to: "2026-08-08", raw_capture_id: 42 });
  const b = row({ id: 115, deal_type: "freebie", headline: "Free froyo bowl for the first 300 customers", valid_from: "2026-08-08", valid_to: "2026-08-08", raw_capture_id: 45 });
  assert.equal(isPossibleDuplicate(a, b), true);
  // A different freebie in an overlapping window is not a duplicate.
  const other = row({ id: 124, deal_type: "freebie", headline: "Free cupcake with any purchase over $10", valid_from: null, valid_to: null, raw_capture_id: 99 });
  assert.equal(isPossibleDuplicate(a, other), false);
});

test("valued pair matches on weaker headline agreement", () => {
  const a = row({ id: 131, deal_type: "fixed_price", discount_value: 3, headline: "$3 per 100 grams frozen yogurt", valid_from: "2026-08-05", valid_to: "2026-08-05", raw_capture_id: 129 });
  const b = row({ id: 132, deal_type: "fixed_price", discount_value: 3, headline: "Frozen yogurt for $3 per 100g", valid_from: "2026-08-05", valid_to: "2026-08-05", raw_capture_id: 130 });
  assert.equal(isPossibleDuplicate(a, b), true);
});

test("windowsOverlap treats nulls as open-ended", () => {
  assert.equal(windowsOverlap(null, null, "2026-01-01", "2026-01-01"), true); // fully open vs a day
  assert.equal(windowsOverlap("2026-07-20", "2026-08-10", "2026-08-08", "2026-08-08"), true);
  assert.equal(windowsOverlap("2026-06-01", "2026-06-30", "2026-08-01", "2026-08-31"), false);
});

test("findDuplicatesFor returns every other 50%-off row", () => {
  const pool = [fiftyOff(119, 72), fiftyOff(120, 75), fiftyOff(121, 76), fiftyOff(122, 77)];
  const hits = findDuplicatesFor(pool[0], pool);
  assert.deepEqual(hits.map((h) => h.id).sort(), [120, 121, 122]);
});

test("similarity is 1 for identical, low for unrelated", () => {
  assert.equal(similarity("50 off frozen yogurt", "50 off frozen yogurt"), 1);
  assert.ok(similarity("free cupcake", "50 percent off") < 0.3);
});
