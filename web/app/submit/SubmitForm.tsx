"use client";

import { useEffect, useRef, useState } from "react";

// Mirrors the server's cap so a 40MB HEIC is not pushed over mobile data only to
// be refused. The route stays the authority; this is a courtesy, not validation.
const MAX_BYTES = 10 * 1024 * 1024;

const FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-live/70 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-bg";

// 18px, not 14px: iOS Safari zooms the viewport on focus for any field under
// 16px, which throws a one-handed user out of position mid-form.
const FIELD =
  `w-full rounded-md border border-ink-line bg-transparent px-3 py-2.5 text-[18px] text-ink-hi placeholder:text-ink-low transition-colors hover:border-ink-lineStrong ${FOCUS}`;

// The example sits under the label, never in the field. A placeholder holding an
// example is a value-shaped thing in a value-shaped slot, and on a dark ground at
// 18px it reads as text already entered.
function Label({
  htmlFor, children, optional, hint,
}: {
  htmlFor: string; children: React.ReactNode; optional?: boolean; hint?: string;
}) {
  return (
    <>
      <label htmlFor={htmlFor} className="block text-[14px] text-ink-hi">
        {children}
        {optional ? <span className="text-ink-low"> (optional)</span> : null}
      </label>
      {hint ? <p id={`${htmlFor}-hint`} className="mt-0.5 text-[12.5px] text-ink-low">{hint}</p> : null}
    </>
  );
}

function fileSize(bytes: number) {
  const mb = bytes / 1024 / 1024;
  return mb >= 1 ? `${mb.toFixed(1)}MB` : `${Math.max(1, Math.round(bytes / 1024))}KB`;
}

export default function SubmitForm() {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // The camera roll is full of near-identical shots, so the picked photo is
  // shown back. It never leaves the browser: an object URL over the local file.
  useEffect(() => {
    if (!photo || !photo.type.startsWith("image/")) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setError(f && f.size > MAX_BYTES ? "That photo is over 10MB. Try a smaller one." : null);
    setPhoto(f);
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!photo) {
      setError("Add a photo first.");
      return;
    }
    if (photo.size > MAX_BYTES) {
      setError("That photo is over 10MB. Try a smaller one.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/submit", { method: "POST", body: new FormData(e.currentTarget) });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setDone(true);
      } else {
        setError(data.error ?? `Something went wrong (${res.status}). Nothing was sent.`);
      }
    } catch {
      setError("That did not send. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setDone(false);
    setPhoto(null);
    setError(null);
    formRef.current?.reset();
  }

  if (done) {
    return (
      <section className="mt-6">
        <h2 className="text-[18px] font-semibold tracking-[-0.015em] text-ink-hi">Received.</h2>
        <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-mid">
          It is in the queue to be read by a person. There is no notification and no way to follow it up, because
          nothing here identifies you.
        </p>
        {/* Only one onward action here. "Back to the deals" already sits in the
            footer on every state, and printing it twice on one screen is noise. */}
        <button
          onClick={reset}
          className={`mt-5 rounded-md px-1 text-[12.5px] text-ink-mid underline decoration-ink-lineStrong underline-offset-4 transition-colors hover:text-ink-hi ${FOCUS}`}
        >
          Send another
        </button>
      </section>
    );
  }

  return (
    <form ref={formRef} onSubmit={onSubmit} className="mt-1.5">
      <p className="mb-8 text-[12.5px] leading-relaxed text-ink-mid">
        One photo of a promo sign. A person reads every submission before it appears anywhere, and not everything
        gets used.
      </p>

      <div>
        <Label htmlFor="photo">Photo of the sign</Label>
        <label htmlFor="photo" className="mt-2 block cursor-pointer">
          <input
            id="photo"
            type="file"
            name="photo"
            // No `required`: the input is visually hidden, so a native validation
            // bubble would anchor to a 1px box. The JS guard below owns this,
            // and reports it in the page's own error line.
            accept="image/jpeg,image/png,image/heic,image/heif,.jpg,.jpeg,.png,.heic"
            onChange={onPick}
            className="peer sr-only"
            aria-describedby="photo-hint"
          />
          <span
            className={`flex items-center justify-between gap-3 rounded-md border border-ink-line px-3 py-3 transition-colors hover:border-ink-lineStrong peer-focus-visible:ring-2 peer-focus-visible:ring-live/70 peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-ink-bg`}
          >
            <span className="min-w-0">
              <span className="block truncate text-[14px] text-ink-hi">
                {photo ? photo.name : "Take or choose a photo"}
              </span>
              <span id="photo-hint" className="mt-0.5 block text-[12.5px] tabular-nums text-ink-low">
                {photo ? `${fileSize(photo.size)} · tap to replace` : "jpg, png or heic · up to 10MB"}
              </span>
            </span>
            {preview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={preview}
                alt=""
                className="h-12 w-12 shrink-0 rounded-md object-cover"
              />
            ) : null}
          </span>
        </label>
      </div>

      <div className="mt-6">
        <Label htmlFor="store" optional hint="For example, Yo-Chi Glen Waverley">Which shop</Label>
        <input id="store" name="store" aria-describedby="store-hint" className={`mt-2 ${FIELD}`} />
      </div>

      <div className="mt-6">
        <Label htmlFor="text" optional hint="Dates, limits, or what the sign says">
          Anything the photo does not show
        </Label>
        <textarea id="text" name="text" rows={3} aria-describedby="text-hint" className={`mt-2 resize-y ${FIELD}`} />
      </div>

      {error ? (
        <p role="alert" className="mt-6 text-[12.5px] leading-relaxed text-ink-hi">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={busy}
        className={`mt-6 w-full rounded-md bg-ink-hi px-4 py-3 text-[14px] font-medium text-ink-bg transition-colors hover:bg-white disabled:bg-white/[0.07] disabled:text-ink-low ${FOCUS}`}
      >
        {busy ? "Sending..." : "Send it in"}
      </button>
    </form>
  );
}
