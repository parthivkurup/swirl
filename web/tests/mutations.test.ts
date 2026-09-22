import assert from "node:assert";
import test from "node:test";

import { Pool } from "pg";

import { APPROVE_SQL, EDIT_SQL, REJECT_SQL, SUPERSEDE_SQL, UNSUPERSEDE_SQL } from "../lib/mutations.ts";

// Execute each review-queue write against the live schema in a rolled-back
// transaction. id -1 matches no row, but the statement is still parsed and
// planned, so parameter-type and column bugs (like the status/last_verified
// ambiguity that reached runtime) fail here. Skips without DATABASE_URL.
const url = process.env.DATABASE_URL;

// Representative params for EDIT_SQL: $1 id, then the editable fields, $14 status
// (deal_status), $15 approved (boolean), $16 scope (checked text).
const editParams = [
  -1, "headline", "percent_off", 10, "percent", "conditions", 500, 200,
  ["dine_in", "takeaway"], [2, 3], "2026-08-05", "2026-08-05", true, "approved", true,
  "melbourne",
];

test("review mutation SQL executes against the schema", { skip: url ? false : "no DATABASE_URL" }, async () => {
  const pool = new Pool({ connectionString: url });
  const client = await pool.connect();
  try {
    await client.query("begin");
    await client.query(APPROVE_SQL, [-1]);
    await client.query(REJECT_SQL, [-1]);
    // edit-and-approve ($14 approved, $15 true) and save ($14 pending, $15 false)
    // share EDIT_SQL; exercise both param combinations.
    await client.query(EDIT_SQL, editParams);
    await client.query(EDIT_SQL, [...editParams.slice(0, 13), "pending", false, "other"]);
    // Every scope value must satisfy the column's check constraint. A value the
    // constraint rejects would only surface when a reviewer picked it.
    for (const scope of ["melbourne", "other", "unknown"]) {
      await client.query(EDIT_SQL, [...editParams.slice(0, 15), scope]);
    }
    await client.query(UNSUPERSEDE_SQL, [-1]);
    await client.query(SUPERSEDE_SQL, [-1, -1]); // id -1 matches nothing; parses/plans
    assert.ok(true);
  } finally {
    await client.query("rollback").catch(() => {});
    client.release();
    await pool.end();
  }
});

test("mutations are no-ops (0 rows -> 409) when the deal state changed", { skip: url ? false : "no DATABASE_URL" }, async () => {
  const pool = new Pool({ connectionString: url });
  const c = await pool.connect();
  try {
    await c.query("begin");
    const { rows } = await c.query("select id from deals order by id limit 2");
    if (rows.length < 2) {
      assert.ok(true); // not enough data to exercise; the -1 test still covers parsing
      return;
    }
    const [a, b] = rows.map((r) => r.id);
    // Put `a` in the state the queue renders: pending and not superseded.
    await c.query("update deals set status='pending', superseded_by=null where id=$1", [a]);
    assert.equal((await c.query(APPROVE_SQL, [a])).rowCount, 1); // precondition holds -> applies

    // Already actioned (now 'approved'): approving again must NOT silently apply.
    assert.equal((await c.query(APPROVE_SQL, [a])).rowCount, 0);

    // Superseded by the merge job (status stays pending): every queue action is a
    // no-op -> the route turns 0 rows into a 409.
    await c.query("update deals set status='pending', superseded_by=$2 where id=$1", [a, b]);
    assert.equal((await c.query(APPROVE_SQL, [a])).rowCount, 0);
    assert.equal((await c.query(REJECT_SQL, [a])).rowCount, 0);
    assert.equal((await c.query(SUPERSEDE_SQL, [a, b])).rowCount, 0);
    assert.equal((await c.query(EDIT_SQL, [a, ...editParams.slice(1)])).rowCount, 0);
  } finally {
    await c.query("rollback").catch(() => {});
    c.release();
    await pool.end();
  }
});
