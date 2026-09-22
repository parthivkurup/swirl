// Review-queue write SQL, kept here (import-free) so both the route handler and
// web/tests/mutations.test.ts use one source of truth and the test can execute
// the exact SQL against the schema.
//
// Every queue action carries a PRECONDITION in its WHERE clause: the deal must
// still be in the state the queue was rendered in (pending and not superseded).
// If a nightly merge, another admin, or an expire changed it since, the UPDATE
// matches 0 rows and the route returns a 409 conflict instead of silently applying
// to a deal that no longer exists in the queue's world. This makes the check and
// the write atomic (no TOCTOU race).

const PENDING_LIVE = `status = 'pending' and superseded_by is null`;

export const APPROVE_SQL = `update deals set status = 'approved', last_verified = now() where id = $1 and ${PENDING_LIVE}`;

export const REJECT_SQL = `update deals set status = 'rejected' where id = $1 and ${PENDING_LIVE}`;

// Undo an auto-merge: clear superseded_by so the deal returns to the live set.
// Precondition: it is actually superseded (else there is nothing to undo).
export const UNSUPERSEDE_SQL = `update deals set superseded_by = null where id = $1 and superseded_by is not null`;

// Mark a deal as a duplicate of a canonical one: set superseded_by (status
// unchanged), the correct action for a duplicate instead of rejecting it. The
// caller resolves $2 to the canonical (never a deal that is itself superseded).
// Precondition: still a live pending deal.
export const SUPERSEDE_SQL = `update deals set superseded_by = $2 where id = $1 and ${PENDING_LIVE}`;

// scope is editable here because the reviewer is the correction mechanism for
// it: "that's the Canberra one" is a two-second call for a human and an
// impossible one for the extractor, which cannot see past the caption.
export const EDIT_SQL = `update deals set
    headline = $2, deal_type = $3, discount_value = $4, discount_unit = $5,
    conditions = $6, min_spend_cents = $7, max_grams = $8, channels = $9,
    days_of_week = $10, valid_from = $11, valid_to = $12, recurring = $13,
    status = $14,
    last_verified = case when $15 then now() else last_verified end,
    scope = $16
  where id = $1 and ${PENDING_LIVE}`;
