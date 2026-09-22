"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { DealSearchResult, QueueDeal } from "@/lib/deals";

const DEAL_TYPES = [
  "percent_off",
  "dollar_off",
  "fixed_price",
  "bogo",
  "freebie",
  "loyalty",
  "bundle",
];
const DISCOUNT_UNITS = ["", "percent", "aud"];
const SCOPES = ["melbourne", "other", "unknown"];
const CHANNELS = ["dine_in", "takeaway", "app", "delivery"];
const NUMERIC_TYPES = new Set(["percent_off", "dollar_off", "fixed_price", "bundle"]);

// Stable empty array so the keyboard effect does not resubscribe every render on
// a deal with no flagged duplicates.
const NO_HINTS: QueueDeal["possibleDuplicates"] = [];

// Why is this item still pending? It can carry several reasons at once.
function pendingReasons(d: QueueDeal): { reasons: string[]; lowConf: boolean } {
  const conf = d.confidence != null ? Number(d.confidence) : null;
  const lowConf = conf == null || conf < 0.8;
  const priceExpected = d.deal_type != null && NUMERIC_TYPES.has(d.deal_type);
  const incomplete = !d.deal_type || !d.headline || (priceExpected && d.discount_value == null);
  const reasons: string[] = [];
  if (d.capture_source_type === "user_submission") reasons.push("user-submitted");
  if (lowConf) reasons.push(conf != null ? `low confidence (${conf})` : "no confidence");
  if (incomplete) reasons.push("incomplete extraction");
  return { reasons, lowConf };
}

type Draft = {
  headline: string;
  deal_type: string;
  discount_value: string;
  discount_unit: string;
  conditions: string;
  min_spend_cents: string;
  max_grams: string;
  channels: string;
  days_of_week: string;
  valid_from: string;
  valid_to: string;
  recurring: boolean;
  scope: string;
};

function toDraft(d: QueueDeal): Draft {
  return {
    headline: d.headline ?? "",
    deal_type: d.deal_type ?? "",
    discount_value: d.discount_value ?? "",
    discount_unit: d.discount_unit ?? "",
    conditions: d.conditions ?? "",
    min_spend_cents: d.min_spend_cents?.toString() ?? "",
    max_grams: d.max_grams?.toString() ?? "",
    channels: (d.channels ?? []).join(", "),
    days_of_week: (d.days_of_week ?? []).join(", "),
    valid_from: d.valid_from ?? "",
    valid_to: d.valid_to ?? "",
    recurring: d.recurring,
    scope: d.scope ?? "unknown",
  };
}

function draftToFields(draft: Draft) {
  return {
    ...draft,
    channels: draft.channels.split(",").map((s) => s.trim()).filter(Boolean),
    days_of_week: draft.days_of_week.split(",").map((s) => s.trim()).filter(Boolean),
  };
}

// Fold saved edits back into a typed QueueDeal so navigating away and back
// shows the saved values rather than the pre-edit ones.
function applyDraft(d: QueueDeal, draft: Draft): QueueDeal {
  const nums = draft.days_of_week
    .split(",")
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !Number.isNaN(n));
  return {
    ...d,
    headline: draft.headline,
    deal_type: draft.deal_type,
    discount_value: draft.discount_value || null,
    discount_unit: draft.discount_unit || null,
    conditions: draft.conditions || null,
    min_spend_cents: draft.min_spend_cents ? parseInt(draft.min_spend_cents, 10) : null,
    max_grams: draft.max_grams ? parseInt(draft.max_grams, 10) : null,
    channels: draft.channels.split(",").map((s) => s.trim()).filter(Boolean),
    days_of_week: nums,
    valid_from: draft.valid_from || null,
    valid_to: draft.valid_to || null,
    recurring: draft.recurring,
    scope: draft.scope,
  };
}

export default function ReviewQueue({ initialDeals }: { initialDeals: QueueDeal[] }) {
  const router = useRouter();
  const [queue, setQueue] = useState<QueueDeal[]>(initialDeals);
  const [idx, setIdx] = useState(0);
  const [draft, setDraft] = useState<Draft | null>(
    initialDeals[0] ? toDraft(initialDeals[0]) : null
  );
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(0);
  const [dupOpen, setDupOpen] = useState(false);
  const [dupQuery, setDupQuery] = useState("");
  const [dupResults, setDupResults] = useState<DealSearchResult[]>([]);
  const [dupSearching, setDupSearching] = useState(false);

  const current = queue[idx];
  const hints = current?.possibleDuplicates ?? NO_HINTS;

  // Reset the duplicate picker whenever the current deal changes.
  useEffect(() => {
    setDupOpen(false);
    setDupQuery("");
    setDupResults([]);
  }, [current?.id]);

  // Latest idx in a ref so the re-sync effect can clamp without depending on idx
  // (which would make it re-run on every navigation).
  const idxRef = useRef(idx);
  idxRef.current = idx;

  // Re-sync the working queue to fresh server data whenever it changes (after a
  // router.refresh() following an action, or a navigation). Without this an open
  // tab keeps a stale queue indefinitely - we could act on a deal the merge job
  // already superseded, or one that no longer exists. Keyed on the id list so it
  // only fires when the pending set actually changes.
  const serverIds = initialDeals.map((d) => d.id).join(",");
  useEffect(() => {
    const clamped = Math.min(idxRef.current, Math.max(initialDeals.length - 1, 0));
    setQueue(initialDeals);
    setIdx(clamped);
    setDraft(initialDeals[clamped] ? toDraft(initialDeals[clamped]) : null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverIds]);

  const loadDraft = useCallback((i: number, q: QueueDeal[]) => {
    setDraft(q[i] ? toDraft(q[i]) : null);
  }, []);

  const go = useCallback(
    (delta: number) => {
      setIdx((i) => {
        const next = Math.min(Math.max(i + delta, 0), Math.max(queue.length - 1, 0));
        loadDraft(next, queue);
        return next;
      });
    },
    [queue, loadDraft]
  );

  const removeCurrent = useCallback(() => {
    setQueue((q) => {
      const next = q.filter((_, i) => i !== idx);
      setIdx((i) => {
        const clamped = Math.min(i, Math.max(next.length - 1, 0));
        loadDraft(clamped, next);
        return clamped;
      });
      return next;
    });
    setDone((n) => n + 1);
  }, [idx, loadDraft]);

  const act = useCallback(
    async (action: "approve" | "reject" | "edit_approve" | "save") => {
      if (!current || busy) return;
      setBusy(true);
      try {
        // Approving a non-Melbourne deal is a deliberate act, never a rhythm.
        // The dashboard already refuses to publish scope 'other', so this cannot
        // put a Canberra deal in front of the public - it exists so approving one
        // is a decision the reviewer knows they made, rather than a keystroke
        // that looks identical to every other approval.
        if (action === "edit_approve" && draft?.scope === "other") {
          const ok = window.confirm(
            `#${current.id} is scoped "other" — it is not a Melbourne deal.\n\n` +
              "Approving records it as real but it will NOT appear on the dashboard. " +
              "If it is actually Melbourne, cancel and change scope first."
          );
          if (!ok) return;
        }
        const payload: Record<string, unknown> = { action };
        if ((action === "edit_approve" || action === "save") && draft) {
          payload.fields = draftToFields(draft);
        }
        const res = await fetch(`/api/deals/${current.id}`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          if (res.status === 409) {
            alert(err.error ?? "This deal changed since you loaded it. Reloading the queue.");
            router.refresh();
          } else {
            alert(`Failed: ${err.error ?? res.status}`);
          }
          return;
        }
        if (action === "save") {
          // keep it in the queue as edited, but reflect saved values
          setQueue((q) => q.map((d, i) => (i === idx && draft ? applyDraft(d, draft) : d)));
        } else {
          removeCurrent();
        }
        // Pull fresh server data so external changes (merge job, another admin)
        // are reflected; the re-sync effect reconciles the working queue.
        router.refresh();
      } finally {
        setBusy(false);
      }
    },
    [current, busy, draft, idx, removeCurrent, router]
  );

  // Mark the current pending deal a duplicate of `targetId`: sets superseded_by,
  // not status, so it stays pending and hidden (undoable via the superseded
  // filter) rather than being wrongly rejected.
  const markDuplicate = useCallback(
    async (targetId: number) => {
      if (!current || busy) return;
      setBusy(true);
      try {
        const res = await fetch(`/api/deals/${current.id}`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ action: "duplicate_of", superseded_by: targetId }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          if (res.status === 409) {
            alert(err.error ?? "This deal changed since you loaded it. Reloading the queue.");
            router.refresh();
          } else {
            alert(`Failed: ${err.error ?? res.status}`);
          }
          return;
        }
        removeCurrent();
        router.refresh();
      } finally {
        setBusy(false);
      }
    },
    [current, busy, removeCurrent, router]
  );

  const searchDup = useCallback(async () => {
    const q = dupQuery.trim();
    if (!q) return;
    setDupSearching(true);
    try {
      const res = await fetch(`/api/deals/search?q=${encodeURIComponent(q)}`);
      const data = await res.json().catch(() => ({ deals: [] }));
      setDupResults((data.deals ?? []).filter((d: DealSearchResult) => d.id !== current?.id));
    } finally {
      setDupSearching(false);
    }
  }, [dupQuery, current]);

  // 1-9 merge into the correspondingly numbered flagged hint, so marking a
  // duplicate costs exactly what rejecting costs: one keystroke, in the same
  // place, without reaching for the mouse. Before this, reject was `r` while
  // duplicate-of was `d` plus a scroll to a picker below the fold plus a click,
  // and the cheaper action won whenever the reviewer had momentum - which is how
  // six real duplicates ended up in the reject set.
  //
  // A one-key merge sitting behind a guess is deliberate, and it is the safer of
  // the two cheap actions: a wrong merge is undone from the superseded list via
  // `unsupersede`, whereas `r` is equally one keystroke and has no undo in the UI
  // at all. Making the recoverable action as cheap as the unrecoverable one moves
  // the path of least resistance to the right place.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (e.key === "j") go(1);
      else if (e.key === "k") go(-1);
      else if (e.key === "a") act("edit_approve");
      else if (e.key === "r") act("reject");
      else if (e.key === "d") setDupOpen((o) => !o);
      else if (/^[1-9]$/.test(e.key)) {
        const hint = hints[Number(e.key) - 1];
        if (hint) markDuplicate(hint.id);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, act, hints, markDuplicate]);

  const setField = (k: keyof Draft, v: string | boolean) =>
    setDraft((d) => (d ? { ...d, [k]: v } : d));

  const progress = useMemo(
    () => `${done} handled · ${queue.length} left`,
    [done, queue.length]
  );

  if (!current || !draft) {
    return (
      <div className="rounded-lg border border-neutral-300 bg-white p-10 text-center">
        <p className="text-lg font-medium">Queue empty</p>
        <p className="text-sm text-neutral-500">{done} deals handled this session.</p>
      </div>
    );
  }

  const { reasons, lowConf } = pendingReasons(current);

  return (
    <div className={lowConf ? "rounded-xl p-2 ring-2 ring-amber-500" : ""}>
      <div className="mb-3 flex items-center justify-between text-sm text-neutral-500">
        <span>
          deal {idx + 1} of {queue.length} · id {current.id} · confidence{" "}
          {current.confidence ?? "n/a"}
        </span>
        <span>{progress}</span>
      </div>

      {/* Triage banner: why this needs attention. Low confidence is loud so a
          careless rhythm-approve is interrupted. */}
      <div
        className={`mb-3 flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
          lowConf ? "border-amber-500 bg-amber-100 font-medium text-amber-900" : "border-neutral-300 bg-neutral-50 text-neutral-600"
        }`}
      >
        {lowConf ? <span className="text-base">⚠ needs a careful look</span> : <span>needs review</span>}
        {reasons.map((r) => (
          <span
            key={r}
            className={`rounded px-1.5 py-0.5 text-xs ${lowConf ? "bg-amber-200 text-amber-900" : "bg-neutral-200 text-neutral-700"}`}
          >
            {r}
          </span>
        ))}
      </div>

      {/* Not a Melbourne deal. Louder than the low-confidence banner because it
          is a statement of fact about the deal rather than a caution about the
          extraction, and because publishing another city's deal is the one
          failure that makes the dashboard false rather than merely incomplete
          (it happened: #114, #123 and #156 all went live). */}
      {draft.scope === "other" ? (
        <div className="mb-3 rounded-lg border-2 border-red-600 bg-red-100 px-3 py-2 text-sm font-medium text-red-900">
          Not a Melbourne deal{current.store_hint_raw ? ` — the source names ${current.store_hint_raw}` : ""}.
          It will not appear on the dashboard whatever you do here. Approve only to record that it is real;
          change scope above if this is wrong.
        </div>
      ) : null}

      {/* Possible-duplicate hint: surfaced for the reviewer to decide, never
          auto-merged. Distinct from the low-confidence banner.

          The hint IS the action. It used to be inert text naming the very id the
          reviewer then had to go and re-enter in a picker at the bottom of the
          page - the system did the work, displayed the answer, and made you walk
          to another room to use it. Each candidate is now a button, numbered to
          match its keyboard shortcut, so deciding and acting happen in one place
          on the evidence you are reading. */}
      {hints.length ? (
        <div className="mb-3 rounded-lg border border-sky-400 bg-sky-50 px-3 py-2 text-sm text-sky-900">
          <span className="font-medium">possible duplicate of</span>{" "}
          <span className="text-sky-700">
            — press the number to merge into it. It stays hidden, not rejected, and undoes from the superseded list.
          </span>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {hints.map((h, i) => (
              <button
                key={h.id}
                disabled={busy}
                onClick={() => markDuplicate(h.id)}
                title={`Mark #${current.id} a duplicate of #${h.id}`}
                className="rounded border border-sky-400 bg-white px-2 py-1 text-xs hover:bg-sky-100 disabled:opacity-50"
              >
                {i < 9 ? (
                  <span className="mr-1.5 rounded bg-sky-200 px-1 font-mono text-sky-900">{i + 1}</span>
                ) : null}
                #{h.id} {h.headline}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Left: raw capture */}
        <section className="rounded-lg border border-neutral-300 bg-white p-4">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Raw capture
          </h2>
          <p className="text-xs text-neutral-500">
            {current.capture_source_type} · captured {current.captured_at}
          </p>
          {/* The submitter's own answer to "which shop". Since migration 0010 it is
              a column rather than a "Store: X" line inside content_text, so it has
              to be rendered explicitly or the reviewer stops seeing it. */}
          {current.submitted_store ? (
            <p className="mt-3 text-[15px]">
              <span className="text-neutral-500">Submitter says shop is</span>{" "}
              <span className="font-medium">{current.submitted_store}</span>
            </p>
          ) : null}
          {/* The evidence behind `scope`. Shown for every deal, not just the
              non-Melbourne ones, so the reviewer can check the classification
              instead of taking it on trust. */}
          {current.store_hint_raw ? (
            <p className="mt-3 text-[15px]">
              <span className="text-neutral-500">Source names</span>{" "}
              <span className="font-medium">{current.store_hint_raw}</span>
            </p>
          ) : null}
          {current.content_text ? (
            <p className="mt-3 whitespace-pre-wrap text-[15px] leading-relaxed">
              {current.content_text}
            </p>
          ) : null}
          {current.image_path ? (
            <a
              href={`/api/image?path=${encodeURIComponent(current.image_path)}`}
              target="_blank"
              rel="noreferrer"
              className="mt-4 block"
              title="Click to view full size"
            >
              <img
                className="max-h-[36rem] w-full rounded border border-neutral-200 object-contain"
                src={`/api/image?path=${encodeURIComponent(current.image_path)}`}
                alt="submitted sign"
              />
              <span className="mt-1 block text-xs text-neutral-500 underline">click to view full size</span>
            </a>
          ) : null}
        </section>

        {/* Right: editable fields */}
        <section className="rounded-lg border border-neutral-300 bg-white p-4">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Extracted deal (editable)
          </h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="headline" wide>
              <input className={inputCls} value={draft.headline} onChange={(e) => setField("headline", e.target.value)} />
            </Field>
            <Field label="deal_type">
              <select className={inputCls} value={draft.deal_type} onChange={(e) => setField("deal_type", e.target.value)}>
                {DEAL_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </Field>
            <Field label="discount_unit">
              <select className={inputCls} value={draft.discount_unit} onChange={(e) => setField("discount_unit", e.target.value)}>
                {DISCOUNT_UNITS.map((u) => (
                  <option key={u} value={u}>{u || "(null)"}</option>
                ))}
              </select>
            </Field>
            <Field label="discount_value">
              <input className={inputCls} value={draft.discount_value} onChange={(e) => setField("discount_value", e.target.value)} />
            </Field>
            <Field label="min_spend_cents">
              <input className={inputCls} value={draft.min_spend_cents} onChange={(e) => setField("min_spend_cents", e.target.value)} />
            </Field>
            <Field label="max_grams">
              <input className={inputCls} value={draft.max_grams} onChange={(e) => setField("max_grams", e.target.value)} />
            </Field>
            <Field label={`channels (${CHANNELS.join("/")})`}>
              <input className={inputCls} value={draft.channels} onChange={(e) => setField("channels", e.target.value)} />
            </Field>
            <Field label="days_of_week (1-7)">
              <input className={inputCls} value={draft.days_of_week} onChange={(e) => setField("days_of_week", e.target.value)} />
            </Field>
            <Field label="valid_from">
              <input className={inputCls} placeholder="YYYY-MM-DD" value={draft.valid_from} onChange={(e) => setField("valid_from", e.target.value)} />
            </Field>
            <Field label="valid_to">
              <input className={inputCls} placeholder="YYYY-MM-DD" value={draft.valid_to} onChange={(e) => setField("valid_to", e.target.value)} />
            </Field>
            <Field label="scope (which city)">
              <select
                className={`${inputCls} ${draft.scope === "other" ? "border-red-500 bg-red-50 font-medium text-red-800" : ""}`}
                value={draft.scope}
                onChange={(e) => setField("scope", e.target.value)}
              >
                {SCOPES.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </Field>
            <Field label="conditions" wide>
              <textarea className={inputCls} rows={2} value={draft.conditions} onChange={(e) => setField("conditions", e.target.value)} />
            </Field>
            <label className="col-span-2 flex items-center gap-2">
              <input type="checkbox" checked={draft.recurring} onChange={(e) => setField("recurring", e.target.checked)} />
              recurring
            </label>
          </div>
        </section>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button disabled={busy} onClick={() => act("edit_approve")} className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
          Approve (a)
        </button>
        <button disabled={busy} onClick={() => act("reject")} className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
          Reject (r)
        </button>
        <button disabled={busy} onClick={() => act("save")} className="rounded border border-neutral-400 px-4 py-2 text-sm font-medium disabled:opacity-50">
          Save edits
        </button>
        <button disabled={busy} onClick={() => setDupOpen((o) => !o)} className="rounded border border-sky-500 px-4 py-2 text-sm font-medium text-sky-700 disabled:opacity-50">
          Duplicate of another… (d)
        </button>
        <span className="ml-auto text-xs text-neutral-500">
          j/k move · a approve · r reject · 1-9 merge into flagged · d find another
        </span>
      </div>

      {/* Duplicate-of picker: mark this pending deal a duplicate of a canonical
          one (sets superseded_by, keeps it pending+hidden) instead of rejecting.

          This is now only the escape hatch for a canonical the matcher did not
          flag. The flagged candidates used to be repeated here too; they live in
          the banner at the top of the page and are one keystroke away, and
          printing them in both places is what split the reviewer's attention
          between where the hint is read and where it is acted on. */}
      {dupOpen ? (
        <div className="mt-3 rounded-lg border border-sky-300 bg-sky-50 p-3 text-sm">
          <p className="mb-2 font-medium text-sky-900">
            Mark #{current.id} a duplicate of another deal…{" "}
            <span className="font-normal text-sky-700">(it stays pending and hidden; undo under the superseded filter)</span>
          </p>
          <p className="mb-2 text-xs text-neutral-500">
            {hints.length
              ? "Flagged candidates are in the blue banner above — press their number. Search here for one that was not flagged."
              : "Nothing was flagged for this deal. Search by headline or id; approved, pending and expired deals are all valid targets."}
          </p>
          <div className="flex items-center gap-2">
            <input
              className={inputCls}
              placeholder="search other deals by headline or id"
              value={dupQuery}
              onChange={(e) => setDupQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  searchDup();
                }
              }}
            />
            <button disabled={dupSearching} onClick={searchDup} className="rounded border border-neutral-400 px-3 py-1 text-xs disabled:opacity-50">
              {dupSearching ? "…" : "Search"}
            </button>
          </div>
          {dupResults.length ? (
            <div className="mt-2 flex flex-wrap gap-1">
              {dupResults.map((d) => (
                <button
                  key={d.id}
                  disabled={busy}
                  onClick={() => markDuplicate(d.id)}
                  className="rounded border border-neutral-300 bg-white px-2 py-1 text-xs hover:bg-neutral-100 disabled:opacity-50"
                >
                  #{d.id} {d.headline}{" "}
                  <span className="text-neutral-400">· {d.chain_name ?? "—"} · {d.status}</span>
                </button>
              ))}
            </div>
          ) : dupQuery && !dupSearching ? (
            <p className="mt-2 text-xs text-neutral-500">no matches.</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

const inputCls =
  "w-full rounded border border-neutral-300 px-2 py-1 focus:border-neutral-500 focus:outline-none";

function Field({ label, wide, children }: { label: string; wide?: boolean; children: React.ReactNode }) {
  return (
    <label className={`flex flex-col gap-1 ${wide ? "col-span-2" : ""}`}>
      <span className="text-xs text-neutral-500">{label}</span>
      {children}
    </label>
  );
}
