"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { SupersededDeal } from "@/lib/deals";

// Superseded (auto-merged) deals, shown under a collapsed filter so a merge can be
// inspected and undone. Undo clears superseded_by and returns the deal to the live
// set. Excluded from the public dashboard either way.
export default function SupersededList({ deals }: { deals: SupersededDeal[] }) {
  const router = useRouter();
  const [rows, setRows] = useState(deals);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);

  // Sync to fresh server data (after a router.refresh() or navigation) so this
  // list does not go stale in an open tab as the merge job supersedes new deals.
  const ids = deals.map((d) => d.id).join(",");
  useEffect(() => {
    setRows(deals);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids]);

  async function undo(id: number) {
    setBusy(id);
    try {
      const res = await fetch(`/api/deals/${id}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action: "unsupersede" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (res.status === 409) {
          alert(err.error ?? "This deal changed since you loaded it.");
          router.refresh();
        } else {
          alert(`Undo failed: ${err.error ?? res.status}`);
        }
        return;
      }
      setRows((r) => r.filter((d) => d.id !== id));
      // Restored deal returns to the live set; refresh so the pending queue picks
      // it up (and this list stays in sync).
      router.refresh();
    } finally {
      setBusy(null);
    }
  }

  if (!rows.length) return null;

  return (
    <section className="mt-10 border-t border-neutral-200 pt-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-sm font-medium text-neutral-600 hover:text-neutral-900"
      >
        {open ? "▾" : "▸"} Superseded / auto-merged ({rows.length})
      </button>
      {open ? (
        <div className="mt-3 space-y-2">
          {rows.length === 0 ? (
            <p className="text-sm text-neutral-500">None (all undone this session).</p>
          ) : (
            rows.map((d) => (
              <div key={d.id} className="flex items-center justify-between gap-3 rounded border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm">
                <div className="min-w-0">
                  <p className="truncate">
                    <span className="text-neutral-400">#{d.id}</span> {d.headline}{" "}
                    <span className="text-neutral-400">
                      · {d.chain_name ?? "—"} · {d.deal_type}
                      {d.valid_from || d.valid_to ? ` · ${d.valid_from ?? "—"}..${d.valid_to ?? "—"}` : ""}
                    </span>
                  </p>
                  <p className="truncate text-xs text-neutral-500">
                    merged into #{d.superseded_by} &ldquo;{d.canonical_headline ?? "?"}&rdquo;
                    {d.source_url ? (
                      <>
                        {" · "}
                        <a href={d.source_url} target="_blank" rel="noreferrer" className="underline">source</a>
                      </>
                    ) : null}
                  </p>
                </div>
                <button
                  disabled={busy === d.id}
                  onClick={() => undo(d.id)}
                  className="whitespace-nowrap rounded border border-neutral-400 px-2 py-1 text-xs font-medium disabled:opacity-50"
                >
                  Undo merge
                </button>
              </div>
            ))
          )}
        </div>
      ) : null}
    </section>
  );
}
