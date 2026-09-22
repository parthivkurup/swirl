/*
 * SURFACE BRIEF (surface: /submit , mode: Operate, seed 1037794c)
 *
 * Built inside the system recorded in DESIGN.md; no new tokens. The roll
 * assigned the classic stacked form: label, field, label, field, action.
 *
 * Dark, following the dashboard, because the main way in is the dashboard's
 * own "Seen one? Send it in" link and a light flash on that navigation reads
 * as leaving the site. body:has(.froyo) exists so a surface can opt in.
 *
 * The submitter is not the operator. They are told what happens to their photo
 * and nothing else: no timeframe, no outcome, no follow-up, because nothing
 * here identifies them and the extractor runs on a schedule.
 *
 * Components this surface needed that the system did not have (field label,
 * text input, textarea, photo picker, primary action, error line, received
 * state) are proposed additions, recorded in DESIGN.md under Submission
 * Controls rather than added quietly.
 */
import SubmitForm from "./SubmitForm";

export const metadata = {
  title: "Send in a froyo deal",
  description: "Photograph a promo sign and send it in. Reviewed before it appears anywhere.",
};
export const viewport = { themeColor: "#0A0A0B" };

export default function SubmitPage() {
  return (
    <div className="froyo min-h-dvh bg-ink-bg font-froyo antialiased">
      <div className="mx-auto max-w-[600px] px-5 pb-16 pt-8 sm:px-7 sm:pt-12">
        <header>
          <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-ink-hi">Send in a deal</h1>
        </header>

        {/* The standfirst lives in the form, not here, so it can stand down once
            the thing it is instructing has already been done. */}
        <SubmitForm />

        <footer className="mt-12 border-t border-ink-line pt-6">
          <p className="text-[12.5px] leading-relaxed text-ink-low">
            The photo&apos;s location data is stripped before it is stored, so where you took it is not kept.
          </p>
          <p className="mt-2 text-[12.5px] leading-relaxed text-ink-low">
            Nothing here identifies you. There is no account, no email field, and no way to reply to you, which
            is also why there is no notification either way.
          </p>
          <p className="mt-4 text-[12.5px] leading-relaxed text-ink-low">
            <a
              href="/"
              className="rounded-md px-1 underline decoration-ink-lineStrong underline-offset-4 transition-colors hover:text-ink-mid focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-live/70 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-bg"
            >
              Back to the deals
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}
