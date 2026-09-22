import { NextRequest, NextResponse } from "next/server";

import { isAuthed } from "@/lib/auth";
import { pool } from "@/lib/db";
import { APPROVE_SQL, EDIT_SQL, REJECT_SQL, SUPERSEDE_SQL, UNSUPERSEDE_SQL } from "@/lib/mutations";

// Anything not one of these falls back to 'unknown', never to 'melbourne'. A
// malformed or missing scope must not be able to publish a Melbourne claim.
const SCOPES = new Set(["melbourne", "other", "unknown"]);

function emptyToNull(v: unknown) {
  return v === "" || v === undefined ? null : v;
}

function toIntArray(v: unknown): number[] {
  if (!Array.isArray(v)) return [];
  return v.map((x) => parseInt(String(x), 10)).filter((n) => !Number.isNaN(n));
}

function toStrArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.map((x) => String(x).trim()).filter(Boolean);
}

export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  if (!isAuthed()) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const id = Number(params.id);
  if (!Number.isInteger(id)) {
    return NextResponse.json({ error: "bad id" }, { status: 400 });
  }
  const body = await req.json().catch(() => ({}));
  const action = body.action as string;

  try {
    let result: { rowCount: number | null };
    if (action === "reject") {
      result = await pool.query(REJECT_SQL, [id]);
    } else if (action === "approve") {
      result = await pool.query(APPROVE_SQL, [id]);
    } else if (action === "unsupersede") {
      result = await pool.query(UNSUPERSEDE_SQL, [id]);
    } else if (action === "duplicate_of") {
      // Mark this deal a duplicate of another: set superseded_by, not status.
      const targetId = Number(body.superseded_by);
      if (!Number.isInteger(targetId) || targetId === id) {
        return NextResponse.json({ error: "bad duplicate target" }, { status: 400 });
      }
      // Resolve to the target's canonical so superseded_by never points at a deal
      // that is itself superseded (no pointer chains).
      const { rows } = await pool.query(
        `select coalesce(superseded_by, id) as canonical from deals where id = $1`,
        [targetId]
      );
      if (!rows[0]) {
        return NextResponse.json({ error: "duplicate target not found" }, { status: 400 });
      }
      if (Number(rows[0].canonical) === id) {
        return NextResponse.json({ error: "a deal cannot supersede itself" }, { status: 400 });
      }
      result = await pool.query(SUPERSEDE_SQL, [id, rows[0].canonical]);
    } else if (action === "save" || action === "edit_approve") {
      const f = body.fields ?? {};
      const approved = action === "edit_approve";
      const status = approved ? "approved" : "pending";
      result = await pool.query(
        EDIT_SQL,
        [
          id,
          emptyToNull(f.headline),
          f.deal_type,
          emptyToNull(f.discount_value),
          emptyToNull(f.discount_unit),
          emptyToNull(f.conditions),
          emptyToNull(f.min_spend_cents),
          emptyToNull(f.max_grams),
          toStrArray(f.channels),
          toIntArray(f.days_of_week),
          emptyToNull(f.valid_from),
          emptyToNull(f.valid_to),
          Boolean(f.recurring),
          status,
          approved,
          SCOPES.has(String(f.scope)) ? f.scope : "unknown",
        ]
      );
    } else {
      return NextResponse.json({ error: "unknown action" }, { status: 400 });
    }

    // 0 rows means the precondition failed: the deal changed since the queue was
    // rendered (superseded by the merge job, already actioned, or gone). Report a
    // conflict with the current state rather than pretending it applied.
    if (!result.rowCount) {
      const { rows } = await pool.query(
        `select status, superseded_by from deals where id = $1`,
        [id]
      );
      const cur = rows[0];
      const detail = !cur
        ? "it no longer exists"
        : cur.superseded_by
        ? `it was merged into #${cur.superseded_by}`
        : `it is now '${cur.status}'`;
      return NextResponse.json(
        { error: `conflict: this deal changed since you loaded it — ${detail}`, conflict: true, current: cur ?? null },
        { status: 409 }
      );
    }
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }

  const { rows } = await pool.query(`select status, superseded_by from deals where id = $1`, [id]);
  return NextResponse.json({ ok: true, id, status: rows[0]?.status ?? null });
}
