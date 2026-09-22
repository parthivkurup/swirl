/*
 * DIRECTION CONTRACT (surface: / , mode: Operate, seed 2512e4a3, roll 3 of 3)
 *
 * THESIS: One ranked column that answers "is any froyo deal worth acting on
 *   today" in a glance. It refuses the deal-card grid, the discount badge and
 *   the filter bar, and after three re-rolls it refuses metaphor as well: the
 *   user took the standing exit, so convention is the commitment, executed at
 *   the craft level of Linear, Vercel and Raycast, with no smuggled quirk.
 * OWN-WORLD: Near-black ground (#0A0A0B), three ink tones (#F2F2F3 subject,
 *   #A1A1A8 meaning, #85858E supporting), hairline dividers, five type steps
 *   (22/18/14/12.5/11), Geist self-hosted, and one accent (#43D9A3) that means
 *   "available today" and, as the focus ring, "you are here".
 * STORY: The visitor reads sticky band heads, finds what is live now, compares
 *   offers written at equal weight, sees the date each was last checked, and
 *   leaves knowing which chain to walk to.
 * FIRST VIEWPORT: Wordmark, a one-line count, the froyo/everything toggle,
 *   then straight into "Available today, ending soon". No hero, no imagery,
 *   no primary action beyond the quiet submit link.
 * FORM: Convention played straight (the standing exit), after The A-Frame,
 *   The Panel and Unit Price were each re-rolled away. Ranking is availability
 *   first, urgency second, and no invented value score. Motion is interaction
 *   feedback only: an entrance animation on a page whose thesis is "in a
 *   glance" delays the one thing the page exists to do.
 * FINISH: unreviewed and undocumented is unfinished; this build ends with the
 *   finish review, the verdict, and DESIGN.md.
 *
 * Note on placement: React drops JSX comments from the emitted HTML, and the
 * brief scopes this work to / only, so this contract cannot live in the shared
 * root layout without changing /review and /submit. It lives here instead.
 */
import { GeistSans } from "geist/font/sans";

import { ActiveDeal, getActiveDeals } from "@/lib/deals";

export const dynamic = "force-dynamic";

// Route-scoped, so /review and /submit keep the layout's own title and chrome.
export const metadata = {
  title: "Melbourne froyo deals",
  description: "Froyo deals around Melbourne, each showing the date it was last checked.",
};
export const viewport = { themeColor: "#0A0A0B" };

const TZ = "Australia/Melbourne";
const STALE_DAYS = 14;
const ENDING_SOON_DAYS = 7;

const DAY_PLURAL: Record<number, string> = {
  1: "Mondays", 2: "Tuesdays", 3: "Wednesdays", 4: "Thursdays",
  5: "Fridays", 6: "Saturdays", 7: "Sundays",
};
const DAY_SHORT: Record<number, string> = {
  1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun",
};
const CHANNEL_LABEL: Record<string, string> = {
  instore: "in store",
  app: "in the app",
  ubereats: "Uber Eats",
  doordash: "DoorDash",
  menulog: "Menulog",
};
const CATEGORY_LABEL: Record<string, string> = {
  adjacent: "adjacent dessert",
  other: "not froyo",
};

function plain(value: string) {
  return value.replace(/_/g, " ");
}

// Every store and every reader is in Melbourne, so "today" is Melbourne's today
// and not the server's.
function melbourneToday(): { iso: string; dow: number } {
  const now = new Date();
  const iso = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit",
  }).format(now);
  const short = new Intl.DateTimeFormat("en-US", { timeZone: TZ, weekday: "short" }).format(now);
  const dow = ({ Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 7 } as Record<string, number>)[short] ?? 1;
  return { iso, dow };
}

function dayNumber(iso: string) {
  return Date.parse(`${iso}T00:00:00Z`) / 86_400_000;
}

function daysBetween(fromIso: string, toIso: string) {
  return dayNumber(toIso) - dayNumber(fromIso);
}

function shortDate(iso: string) {
  return new Intl.DateTimeFormat("en-AU", { timeZone: "UTC", day: "numeric", month: "short" })
    .format(new Date(`${iso}T00:00:00Z`));
}

// The basis slot carries a real unit basis or nothing at all. It is never given
// a stand-in word: a reader who sees "bundle" there learns the slot means "kind
// of deal", and would then read a later "/ 100g" as a category rather than as
// the thing that makes the price mean anything.
// The enum is ('flat', 'per_100g', 'per_kg') per db/migrations/0004. 'flat' means
// the price has no unit basis, so it correctly returns null and renders bare.
// (SPEC's each/per_serve belong to the prices table, not to deals.unit_basis.)
function basisLabel(unit: string | null): string | null {
  switch (unit) {
    case "per_100g": return "/ 100g";
    case "per_kg": return "/ kg";
    default: return null;
  }
}

// Dollar figures keep their cents: 18.9 out of the numeric column is $18.90,
// not $18.9. Percentages drop the trailing zeros instead.
function dollars(raw: string | null): string | null {
  const n = raw != null ? Number(raw) : null;
  if (n == null || !Number.isFinite(n)) return null;
  return Number.isInteger(n) ? String(n) : n.toFixed(2);
}

function percent(raw: string | null): string | null {
  const n = raw != null ? Number(raw) : null;
  if (n == null || !Number.isFinite(n)) return null;
  return String(n);
}

// The offer, written at equal weight across incomparable deal types. The basis
// is returned beside the figure and rendered with it, never appended later, so
// a per-100g price cannot reach the page looking like a flat price.
//
// `states` is whether this string is the offer or merely names its kind. "50%
// off", "Free" and "Buy one, get one" say what you get; "Loyalty", and the
// fallbacks for a type whose figure came back null, do not. Where it is false
// the row gives its largest type to the deal's own words instead, because the
// most prominent text on a row must be the informative one.
function offer(d: ActiveDeal): { value: string; basis: string | null; states: boolean } {
  const basis = basisLabel(d.unit_basis);
  const d$ = dollars(d.discount_value);
  const p = percent(d.discount_value);
  switch (d.deal_type) {
    case "percent_off": return { value: p != null ? `${p}% off` : "percent off", basis, states: p != null };
    case "dollar_off": return { value: d$ != null ? `$${d$} off` : "dollars off", basis, states: d$ != null };
    case "fixed_price": return { value: d$ != null ? `$${d$}` : "set price", basis, states: d$ != null };
    case "bundle": return { value: d$ != null ? `$${d$}` : "bundle", basis, states: d$ != null };
    case "bogo": return { value: "Buy one, get one", basis, states: true };
    case "freebie": return { value: "Free", basis, states: true };
    case "loyalty": return { value: "loyalty", basis, states: false };
    default: return { value: plain(d.deal_type), basis, states: false };
  }
}

// Conditions that only restate the headline are printed twice for no gain. This
// suppresses a strict restatement (shorter than the headline, and almost all of
// its words already in it), never an elaboration: anything that adds a term,
// a limit or an exclusion keeps its own line.
function restatesHeadline(headline: string, conditions: string) {
  const tokens = (s: string) => s.toLowerCase().replace(/[^a-z0-9 ]+/g, " ").split(/\s+/).filter(Boolean);
  const head = new Set(tokens(headline));
  const cond = tokens(conditions);
  if (cond.length === 0 || cond.length > head.size) return false;
  return cond.filter((t) => head.has(t)).length / cond.length >= 0.8;
}

// What is actually known about a deal's freshness, and the honest word for it.
//
// A deal reverify can re-fetch was genuinely re-checked on its last_verified
// date. A deal it cannot touch (no source_url, which is every user submission)
// was seen once, on the day the photo was taken. Its last_verified is only the
// day the operator got round to approving it, and the queue sits for an unbounded
// time, so using it would overstate freshness by an arbitrary amount. That error
// reads as normal and gives the visitor nothing to be suspicious of, which is
// exactly the class of mistake this page exists to refuse.
function evidence(d: ActiveDeal): { date: string | null; label: string } {
  if (d.recheckable) {
    return {
      date: d.last_verified,
      label: d.last_verified ? `checked ${shortDate(d.last_verified)}` : "never checked",
    };
  }
  if (d.seen_at) return { date: d.seen_at, label: `seen ${shortDate(d.seen_at)}` };
  // No capture to date it by. Say what the date actually is rather than calling
  // an approval a sighting.
  return {
    date: d.last_verified,
    label: d.last_verified ? `added ${shortDate(d.last_verified)}` : "date unknown",
  };
}

function money(cents: number) {
  const amount = cents / 100;
  return `$${Number.isInteger(amount) ? amount : amount.toFixed(2)}`;
}

function details(d: ActiveDeal, runsToday: boolean): string[] {
  const out: string[] = [];
  const days = d.days_of_week ?? [];
  if (runsToday && days.length > 0 && days.length < 7) {
    out.push(days.map((n) => DAY_SHORT[n] ?? String(n)).join(", "));
  }
  if (d.recurring) out.push("recurring");
  if (d.min_spend_cents != null) out.push(`min spend ${money(d.min_spend_cents)}`);
  if (d.max_grams != null) out.push(`up to ${d.max_grams}g`);
  for (const c of d.channels ?? []) out.push(CHANNEL_LABEL[c] ?? plain(c));
  return out;
}

type Band = 0 | 1 | 2 | 3 | 4 | 5;

type Row = {
  deal: ActiveDeal;
  band: Band;
  sort: number;
  status: string | null;
  statusDim: boolean;
  runsToday: boolean;
};

const BAND_TITLE: Record<Band, string> = {
  0: "Available today, ending soon",
  1: "Available today",
  2: "Other days",
  3: "City not stated",
  4: "Unconfirmed for two weeks",
  5: "Ended",
};

const BAND_NOTE: Record<Band, string | null> = {
  0: null,
  1: null,
  2: "Live deals that do not run today.",
  // Covers both ways a deal lands here: a chain that posts beyond Melbourne, and
  // a post that could not be tied to a shop at all. Naming only the first would
  // assert something untrue of the second, which is the exact class of error
  // this band was built to stop.
  3: "The source did not say which city. These come from accounts that also post for stores outside Melbourne, or from posts that could not be tied to a shop at all. They may well be Melbourne — nothing here confirms it, so they are not counted as available today.",
  4: "Nothing has confirmed these in a fortnight. The ones marked seen are a single visitor's photo, and there is no page to re-check them against, so they will not move back up.",
  5: "The end date has passed. Shown so a deal never vanishes without saying why.",
};

// Availability first, urgency second, freshness third. Deal types are never
// ranked against each other: there is no true exchange rate between 50% off,
// $3 per 100g and a free bowl for the first 300, so the page does not invent one.
function band(d: ActiveDeal, todayIso: string, dow: number): Row {
  const days = d.days_of_week ?? [];
  const runsToday = days.length === 0 || days.includes(dow);
  const started = !d.valid_from || d.valid_from <= todayIso;
  // Age is measured from the evidence, not from the approval. See evidence().
  const ev = evidence(d);
  const stale = !ev.date || daysBetween(ev.date, todayIso) > STALE_DAYS;
  const endsIn = d.valid_to ? daysBetween(todayIso, d.valid_to) : null;
  const checkedAgo = ev.date ? daysBetween(ev.date, todayIso) : Number.MAX_SAFE_INTEGER;
  const base = { deal: d, statusDim: false, runsToday };

  const endLabel =
    endsIn == null ? null
      : endsIn === 0 ? "ends today"
        : endsIn === 1 ? "ends tomorrow"
          : `ends ${shortDate(d.valid_to as string)}`;

  // An approved deal whose window has already passed is not "available today".
  // expire_deals clears these at 03:35, so between the end date and that run
  // they are still approved, and the page must not claim they are live.
  if (endsIn != null && endsIn < 0) {
    return { ...base, band: 5, sort: -endsIn, status: `ended ${shortDate(d.valid_to as string)}` };
  }
  // Scope outranks staleness, and everything below it, because "this might not
  // be Melbourne" answers the page's actual question - where should I go - more
  // decisively than "this might be out of date". It does NOT outrank Ended: a
  // finished deal is useless in every city. Deals here are never counted as
  // available today, so the headline claim stays a Melbourne claim.
  // ('other' never reaches this page at all; getActiveDeals drops it.)
  if (d.scope !== "melbourne") {
    return { ...base, band: 3, sort: checkedAgo, status: endLabel };
  }
  if (stale) {
    return { ...base, band: 4, sort: checkedAgo, status: endLabel };
  }
  if (!started) {
    return {
      ...base, band: 2,
      sort: daysBetween(todayIso, d.valid_from as string),
      status: `from ${shortDate(d.valid_from as string)}`,
    };
  }
  if (!runsToday) {
    const wait = Math.min(...days.map((n) => ((n - dow + 7) % 7) || 7));
    const label = days.length === 1
      ? DAY_PLURAL[days[0]] ?? DAY_SHORT[days[0]]
      : days.map((n) => DAY_SHORT[n] ?? String(n)).join(", ");
    return { ...base, band: 2, sort: wait, status: label ?? null };
  }
  if (endsIn != null && endsIn <= ENDING_SOON_DAYS) {
    return { ...base, band: 0, sort: endsIn, status: endLabel };
  }
  // "given" matters: this reports what the source did not say, rather than
  // asserting the deal runs forever.
  return {
    ...base, band: 1, sort: checkedAgo,
    status: endLabel ?? "no end date given",
    statusDim: endLabel == null,
  };
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[11px] font-semibold uppercase tracking-[0.07em] text-ink-mid">{children}</span>
  );
}

function DealRow({ row }: { row: Row }) {
  const d = row.deal;
  const { value, basis, states } = offer(d);
  const stale = row.band === 4 || row.band === 5;
  const meta = details(d, row.runsToday);
  const offCategory = d.category && d.category !== "froyo"
    ? CATEGORY_LABEL[d.category] ?? plain(d.category)
    : null;
  const lead = stale ? "text-ink-mid" : "text-ink-hi";
  const checked = evidence(d).label;
  const statusTone = stale || row.statusDim ? "text-ink-low" : "text-ink-mid";

  // Only the first two lines carry right-hand information. Everything below them
  // runs the full width of the row, so the deal's own words get the whole measure
  // instead of the ~226px a fixed provenance column used to leave them.
  return (
    <li className="border-b border-ink-line py-3.5 last:border-b-0">
      <div className="flex items-baseline justify-between gap-3">
        {states ? (
          <p className="flex min-w-0 flex-wrap items-baseline gap-x-2">
            <span className={`text-[18px] font-semibold tabular-nums tracking-[-0.015em] ${lead}`}>{value}</span>
            {basis ? <span className="text-[12.5px] font-medium text-ink-low">{basis}</span> : null}
          </p>
        ) : (
          <p className={`min-w-0 text-[18px] font-semibold leading-[1.28] tracking-[-0.015em] ${lead}`}>
            {d.headline}
          </p>
        )}
        {states && row.status ? (
          <p className={`shrink-0 text-right text-[12.5px] leading-[1.4] tabular-nums ${statusTone}`}>{row.status}</p>
        ) : null}
      </div>

      <div className="mt-1 flex flex-wrap items-baseline justify-between gap-x-3">
        <p className="flex flex-wrap items-baseline gap-x-2 text-[14px] text-ink-low">
          {offCategory ? <Tag>{offCategory}</Tag> : null}
          {!states ? <Tag>{value}</Tag> : null}
          {/* Store-level data does not exist, so a deal with a chain is chain-wide
              and a deal without one says nothing rather than guessing. */}
          {d.chain_name ? (
            <span>
              All <span className={lead}>{d.chain_name}</span> locations
            </span>
          ) : null}
        </p>
        {/* ml-auto so provenance still sits on the right edge when a long
            location line pushes it onto its own row. */}
        <p className="ml-auto text-[12.5px] leading-[1.4] tabular-nums text-ink-low">
          {!states && row.status ? <span className={statusTone}>{row.status} · </span> : null}
          {checked}
        </p>
      </div>

      {states ? <p className="mt-1.5 text-[12.5px] leading-[1.5] text-ink-mid">{d.headline}</p> : null}

      {meta.length > 0 ? (
        <p className="mt-1 text-[12.5px] tabular-nums text-ink-low">{meta.join(" · ")}</p>
      ) : null}

      {/* An ended deal's terms are not actionable, so they do not earn the space. */}
      {d.conditions && row.band !== 5 && !restatesHeadline(d.headline, d.conditions) ? (
        <p className="mt-1 text-[12.5px] leading-[1.5] text-ink-low">{d.conditions}</p>
      ) : null}
    </li>
  );
}

const LINK_FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-live/70 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-bg";

function Toggle({ active }: { active: "froyo" | "all" | null }) {
  const base = `rounded-md px-2.5 py-1 text-[12.5px] transition-colors ${LINK_FOCUS}`;
  const on = "bg-white/[0.07] font-medium text-ink-hi";
  const off = "text-ink-low hover:text-ink-mid";
  return (
    <div className="flex items-center gap-1">
      <a href="/" className={`${base} ${active === "froyo" ? on : off}`}>Froyo</a>
      <a href="/?category=all" className={`${base} ${active === "all" ? on : off}`}>Everything</a>
    </div>
  );
}

export default async function Home({
  searchParams,
}: {
  searchParams: { category?: string };
}) {
  const category = searchParams.category ?? "froyo";
  const deals = await getActiveDeals({ category });
  const { iso: todayIso, dow } = melbourneToday();

  const rows = deals
    .map((d) => band(d, todayIso, dow))
    .sort((a, b) => a.band - b.band || a.sort - b.sort || b.deal.id - a.deal.id);

  const bands: Band[] = [0, 1, 2, 3, 4, 5];
  const today = rows.filter((r) => r.band === 0 || r.band === 1);
  const todayChains = new Set(today.map((r) => r.deal.chain_name).filter(Boolean)).size;
  // The newest piece of information on the page, whether that came from a
  // re-check or a sighting. Calling a sighting a check would be the same
  // overstatement the row-level wording exists to avoid.
  const dated = deals.map((d) => evidence(d).date).filter(Boolean) as string[];
  const lastCheck = dated.length > 0 ? dated.sort().at(-1) : null;

  // The count excludes the Ended band: a deal the page itself labels ended must
  // not sit inside the denominator of what is on offer.
  const listed = rows.filter((r) => r.band !== 5).length;
  const summary = deals.length === 0
    ? "Nothing is live right now."
    : listed === 0
      ? "Nothing is currently on offer. Every deal below has ended."
      : today.length === 0
        ? `None of the ${listed} deals listed run today.`
        : `${today.length} of ${listed} deals are available today, from ${todayChains} ${todayChains === 1 ? "chain" : "chains"}.`;

  return (
    <div className={`froyo min-h-dvh bg-ink-bg font-froyo antialiased ${GeistSans.variable}`}>
      <div className="mx-auto max-w-[600px] px-5 pb-16 pt-8 sm:px-7 sm:pt-12">
        <header>
          <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-ink-hi">Melbourne froyo</h1>
          <p className="mt-1.5 text-[12.5px] leading-relaxed tabular-nums text-ink-mid">
            {summary}
            {lastCheck ? ` Most recent update ${shortDate(lastCheck)}.` : ""}
          </p>
          <div className="mt-4 flex items-center justify-between gap-4">
            <Toggle active={category === "froyo" ? "froyo" : category === "all" ? "all" : null} />
            <a
              href="/submit"
              className={`rounded-md px-1 text-[12.5px] text-ink-low underline decoration-ink-lineStrong underline-offset-4 transition-colors hover:text-ink-mid ${LINK_FOCUS}`}
            >
              Seen one? Send it in
            </a>
          </div>
        </header>

        {rows.length === 0 ? (
          <p className="mt-10 text-[12.5px] leading-relaxed text-ink-mid">
            No {category === "all" ? "" : "froyo "}deals are live at the moment. Nothing is being hidden: the list
            is empty because nothing has been confirmed.
          </p>
        ) : (
          <div className="mt-6">
            {bands.map((b) => {
              const group = rows.filter((r) => r.band === b);
              if (group.length === 0) return null;
              return (
                <section key={b} className="mt-7 first:mt-0">
                  <div className="sticky top-0 z-10 -mx-5 bg-ink-bg px-5 pb-2 pt-3 sm:-mx-7 sm:px-7">
                    <div className="flex items-baseline gap-2">
                      {b <= 1 ? <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-live" /> : null}
                      <h2 className="text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-mid">
                        {BAND_TITLE[b]}
                      </h2>
                      <span className="text-[11px] tabular-nums text-ink-low">{group.length}</span>
                    </div>
                  </div>
                  {BAND_NOTE[b] ? (
                    <p className="mb-1 mt-1 text-[12.5px] leading-relaxed text-ink-low">{BAND_NOTE[b]}</p>
                  ) : null}
                  <ul className="mt-1">
                    {group.map((r) => (
                      <DealRow key={r.deal.id} row={r} />
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>
        )}

        <footer className="mt-12 border-t border-ink-line pt-6">
          <p className="text-[12.5px] leading-relaxed text-ink-low">
            Sources: 16 Instagram accounts and 2 websites. Not every Melbourne froyo shop is covered.
          </p>
          <p className="mt-2 text-[12.5px] leading-relaxed text-ink-low">
            Every deal is dated. <span className="text-ink-mid">Checked</span> means the source page was read
            again on that date. <span className="text-ink-mid">Seen</span> means one person photographed it that
            day and there is no page to re-read, so it will never say checked.
          </p>
          <p className="mt-2 text-[12.5px] leading-relaxed text-ink-low">
            Nothing here is inferred: if a source did not say it, it is not on the page.
          </p>
        </footer>
      </div>
    </div>
  );
}
