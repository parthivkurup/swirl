---
name: Melbourne Froyo
description: A near-black, single-column deal record read in a glance on a phone, with one green accent that means "available today".
colors:
  ink-bg: "#0A0A0B"
  ink-hi: "#F2F2F3"
  ink-mid: "#A1A1A8"
  ink-low: "#85858E"
  ink-line: "#212125"
  ink-lineStrong: "#2E2E34"
  live: "#43D9A3"
  surface-raised: "rgba(255,255,255,0.07)"
typography:
  display:
    fontFamily: "Geist Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: "normal"
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Geist Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: "normal"
    letterSpacing: "-0.015em"
    fontFeature: "tabular-nums"
  title:
    fontFamily: "Geist Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "normal"
    letterSpacing: "normal"
  body:
    fontFamily: "Geist Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: "1.5"
    letterSpacing: "normal"
  label:
    fontFamily: "Geist Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: "normal"
    letterSpacing: "0.09em"
  tag:
    fontFamily: "Geist Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: "normal"
    letterSpacing: "0.07em"
rounded:
  md: "6px"
  full: "9999px"
spacing:
  hair: "2px"
  step: "4px"
  gap: "6px"
  band-pad: "8px"
  row-pad: "14px"
  column-gap: "16px"
  gutter: "20px"
  gutter-wide: "28px"
  section-gap: "28px"
  footer-gap: "48px"
components:
  toggle-on:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink-hi}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "4px 10px"
  toggle-off:
    backgroundColor: "transparent"
    textColor: "{colors.ink-low}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "4px 10px"
  toggle-off-hover:
    textColor: "{colors.ink-mid}"
  link-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink-low}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "0 4px"
  link-quiet-hover:
    textColor: "{colors.ink-mid}"
  band-head:
    backgroundColor: "{colors.ink-bg}"
    textColor: "{colors.ink-mid}"
    typography: "{typography.label}"
    padding: "12px 20px 8px"
  band-count:
    textColor: "{colors.ink-low}"
    typography: "{typography.label}"
  live-dot:
    backgroundColor: "{colors.live}"
    rounded: "{rounded.full}"
    height: "6px"
    width: "6px"
  deal-row:
    backgroundColor: "transparent"
    textColor: "{colors.ink-mid}"
    typography: "{typography.body}"
    padding: "14px 0"
  deal-row-offer:
    textColor: "{colors.ink-hi}"
    typography: "{typography.headline}"
  deal-row-offer-dimmed:
    textColor: "{colors.ink-mid}"
    typography: "{typography.headline}"
  deal-row-meta:
    textColor: "{colors.ink-low}"
    typography: "{typography.body}"
  off-category-tag:
    backgroundColor: "transparent"
    textColor: "{colors.ink-mid}"
    typography: "{typography.tag}"
---

# Design System: Melbourne Froyo

> Scope: this file documents the two public surfaces, the dashboard at `/` and the submission page at `/submit`, and the tokens introduced for them. The operator surfaces `/review` and `/login` run on unstyled Tailwind defaults with a light body; they were deliberately not part of this work and are **undocumented and out of scope**. They are not a second system to be consistent with. The `ink` scale, the `live` accent and the `froyo` font family are additive Tailwind extensions, and `fontFamily.sans` is deliberately left unoverridden so preflight never touches the operator surfaces.
>
> The public surfaces share a ground: both opt in with a `.froyo` root, which `body:has(.froyo)` uses to pull `ink-bg` up to the body. `/submit` is dark because the way in is the dashboard's own "Seen one? Send it in" link, and a light flash on that navigation reads as leaving the site.

## Overview

**Creative North Star: "The Record, Not the Pitch"**

The page is read at arm's length, on a phone, in the evening, by someone deciding within seconds which Melbourne froyo chain is worth walking to. Everything follows from that: one ranked column on a near-black ground, band heads that say what state a deal is in, offers written at equal typographic weight because there is no honest exchange rate between "50% off" and "$3 / 100g", and a date on every row saying when a human last confirmed it. Nothing sells. The surface's only job is to be true and instantly legible.

The visual world is **convention executed at the craft level of Linear, Vercel and Raycast**. This is a commitment, not a fallback. The owner was dealt three authored directions (The A-Frame, The Panel, Unit Price), re-rolled all three, and took the standing exit to convention: no metaphor, no borrowed world, no clever naming, no smuggled quirk. PRODUCT.md records it as a standing preference under Brand Commitments. A future run that "improves" this surface with a concept is re-proposing something already declined three times.

Motion is interaction feedback only. **There is deliberately no entrance animation**, and the reasoning is recorded in `web/app/globals.css`: content that fades in is content that is not yet readable, on a page whose entire thesis is legibility in a glance. This departs from the usual expectation of one authored motion moment per surface. It is an open disagreement held on purpose, not an oversight; if a future run wants an entrance moment it has to argue against the thesis, not just add a keyframe.

**Key Characteristics:**
- Near-black ground (`ink-bg`), never pure black, never a lighter card surface behind rows
- Exactly three ink tones for text, each with a fixed job
- Exactly one accent, meaning "available today" and, as the focus ring, "you are here"
- Five hard type steps: 22 / 18 / 14 / 12.5 / 11
- Hairline dividers instead of shadows, cards, or panels
- Absence and staleness are printed, never hidden
- No imagery, no icons, no badges, no filter bar, no hero

## Colors

A near-black neutral ground carrying three ink tones and a single mint-green accent; nothing else is coloured.

### Primary
- **Live Mint** (`live`): The only chromatic value on the page. It appears in exactly two roles: a 6px dot beside the "Available today, ending soon" and "Available today" band heads, and the focus ring on every interactive element. In the first role it means *available today*; in the second it means *you are here*. It is deliberately never used for value, urgency, branding, or emphasis.

### Neutral
- **Ground** (`ink-bg`): The page ground, and the opaque paint behind sticky band heads. Also the `themeColor` for browser chrome, so the phone's status bar matches the page. Pulled up to `<body>` only via `body:has(.froyo)`, so operator surfaces keep their light body.
- **Subject Ink** (`ink-hi`): The offer value and the chain name. What the reader is scanning for. 17.69:1 on ground.
- **Meaning Ink** (`ink-mid`): The deal's own wording (headline, conditions when they add a term), real dates and statuses, band-head titles, the summary line. 7.71:1 on ground.
- **Supporting Ink** (`ink-low`): Unit basis, day and channel metadata, counts, band notes, footer, inactive toggle, absent facts ("no end date given", "never checked"), and every dimmed state. 5.41:1 on ground.
- **Hairline** (`ink-line`): Row dividers and the footer rule. Reads as separation, not as a box.
- **Hairline Strong** (`ink-lineStrong`): Underline decoration on the quiet submit link, where a divider-weight line would disappear under text.
- **Raised** (`surface-raised`): A 7% white wash, used once, as the selected state of the froyo/everything toggle. It is a state, not a surface family; do not start building cards out of it.

All five text-bearing values clear WCAG AA on `ink-bg`, including the accent at 11.02:1.

### Named Rules

**The Live-Only Rule.** `#43D9A3` may appear in exactly two places on any surface: as the availability dot on a band that is live today, and as the focus ring. It never carries value, urgency, savings, a call to action, or brand identity. If a new element "wants" the accent, that element wants hierarchy it has not earned.

**The Three Inks Rule.** Ink is assigned by role, not by taste. `ink-hi` = the subject (the offer value, or the headline when it leads the row, plus the chain name). `ink-mid` = the deal's own words and any date that is real. `ink-low` = supporting detail, absent facts, and dimmed states. These roles were corrected during review; getting them wrong is the fastest way to make the page lie about what matters.

**The Dim, Never Hide Rule.** A stale (unverified for 14+ days) or ended deal demotes one ink step (`ink-hi` becomes `ink-mid`, `ink-mid` becomes `ink-low`) and keeps its date visible. It is never removed, greyed to illegibility, or collapsed behind a disclosure. A visitor outside a shop needs to tell "no deal" apart from "we have not checked lately".

## Typography

**Body Font:** Geist Sans, self-hosted via the `geist` package (fallbacks: `ui-sans-serif`, `system-ui`, `sans-serif`). Exposed as the `froyo` family so operator surfaces keep Tailwind's default stack.

**Character:** One family, one voice. Geist is a neutral grotesque with real tabular figures, which is the whole reason it is here: the page is mostly prices, percentages and dates, and those have to sit in columns without jitter. Rendered antialiased.

### Hierarchy
- **Display** (600, 22px, tracking -0.02em): The wordmark line, once per page.
- **Headline** (600, 18px, tracking -0.015em, tabular figures): The offer value. Every deal type renders here at identical weight and size.
- **Title** (400, 14px): The location line ("All *Chain* locations"), with the chain name lifted to `ink-hi` inside it.
- **Body** (400, 12.5px, line-height 1.5): The deal's own wording, conditions, status, provenance dates, band notes, footer. Line-height relaxes to 1.625 for multi-line prose (summary, band notes, footer) and tightens to 1.4 in the right-hand provenance column. A 500-weight variant carries the unit basis beside the price.
- **Label** (600, 11px, uppercase, tracking 0.09em): Band heads and their counts.
- **Tag** (600, 11px, uppercase, tracking 0.07em): The off-category marker ("adjacent dessert", "not froyo") inline beside the offer value. `ink-mid`, no pill, no background, no border.

### Named Rules

**The Five Steps Rule.** 22, 18, 14, 12.5, 11. There is no sixth step and no intermediate size. A new element takes the nearest existing step or a different weight, never a new number.

**The Equal Weight Rule.** Every offer renders at the same 18px/600, whatever its type. "50% off", "$4.99", "Buy one, get one" and "Free" are not ranked against each other typographically, because the page has no honest way to rank them. Nothing in the type system may imply one deal is worth more than another.

**The Informative Lead Rule.** The largest text on a row must be the text that tells you what you get. Some deal types name themselves without stating an offer: "loyalty" is a category, not a deal, and a `percent_off` whose `discount_value` came back null degrades to the bare word "percent off". Where the offer string only names the kind of deal, the row gives its 18px slot to the deal's own headline instead, and the type name drops to an 11px uppercase tag on the location line. The rule is not "prices are big"; it is "the informative string is big". Check it by covering everything on a row except the largest line and asking whether you could still decide.

**The Tabular Rule.** Any run of digits — prices, percentages, dates, counts, minimum spends, gram limits — is set with tabular figures so the numeric column and the provenance column stay in vertical register while rows change.

**The Sentence Case Rule.** Uppercase is reserved for the two 11px roles (band label, off-category tag). Headings, links, buttons and body copy are sentence case. No em dashes anywhere, per PRODUCT.md's voice rule; the metadata list uses a middle dot separator instead.

## Layout

One centred column, `max-width: 600px`, gutters 20px rising to 28px at `sm` (640px). Top padding 32px rising to 48px; bottom padding 64px. Full viewport height via `min-h-dvh`, so the ground survives a short list on mobile. Reading measure at the widest is roughly 70 characters at 12.5px — long enough for a condition, short enough to scan. The column does not widen on desktop: the desktop case is the same reading task with more air around it, not a denser one.

**Row structure.** A deal row is a vertical stack, not a two-column split. Only its first two lines carry right-hand information, each as its own baseline-aligned `justify-between` pair: line one is the offer with the status opposite it, line two is the location with "checked *date*" opposite it. Every line below them — headline, metadata, conditions — runs the full width of the column.

This replaced a fixed 104px provenance rail. The rail held two short lines and then left a dead rectangle down the height of the row, while cutting the measure for the longest text on the page from 350px to 226px on a 390px phone. Per-line pairing keeps provenance on the right edge where it can be scanned down the column, and gives the deal's own words the whole measure. The right-hand element carries `ml-auto`, so when a long location line pushes it onto its own row it still sits on the right edge instead of falling back to the left.

**Vertical rhythm inside a row.** 4px between the offer line and the location line, 6px before the headline, 4px between each subsequent supporting line, 14px of padding above and below the row, and a hairline between rows (suppressed on the last).

**Band structure.** Deals group into five ordered bands: available today ending soon, available today, other days, not checked in 14 days, ended. Sections sit 28px apart. Each band head is sticky at the top of the viewport, bleeds to the full page width by negative gutter margins, and paints solid `ink-bg` behind itself with 12px above and 8px below. Bands 2 through 4 carry an explanatory note in `ink-low` directly under the head, saying in plain words what the band means.

**Footer.** Separated by a hairline rule 48px below the list, 24px of padding above the text.

### Named Rules

**The One Column Rule.** One ranked column, top to bottom, always. No card grid, no side-by-side comparison, no filter rail. Ranking is availability first, urgency second, freshness third, and the page never invents a value score.

**The Opaque Band Head Rule.** A sticky head must be fully opaque and must bleed past the content gutters. A translucent or inset head lets rows ghost through it, and the head is the reader's only orientation cue about what state they are looking at.

## Elevation & Depth

There is no elevation. No box-shadows, no cards, no panels, no borders around content, no backdrop blur, no gradient. Depth is carried entirely by ink contrast and 1px hairlines: the reader perceives a hierarchy of *importance*, not a stack of *surfaces*. The single exception is the 7% white wash on the selected toggle, which is a selected state on a control, not a raised plane.

### Named Rules

**The Hairline Rule.** Separation is a 1px `ink-line` rule and nothing else. If two things need distinguishing, change ink or add space before you reach for a border box, and never reach for a shadow.

**The No Container Rule.** Deals are list items, not cards. The moment a row gets a background, a border and a radius, it becomes a product tile competing for attention, and the ranked column stops reading as a single ordered answer.

## Shapes

Almost everything is unshaped: text on ground, separated by straight hairlines. Radius appears only on interactive surfaces and one indicator. Controls use a gentle 6px radius (`rounded-md`) — the toggle segments and the focus/hover target of the submit link. The availability indicator is a 6px circle. There are no pills, no chips with backgrounds, no badges, no icon system; the off-category marker and the band counts are bare text. Rules are 1px and full-bleed within the column.

## Components

The page has five components and no component library. Do not invent a sixth to hold something text can say.

### Toggle (froyo / everything)

Two anchors, not buttons — the category is a URL, so the control is navigation and stays shareable and back-button-correct.

- **Shape:** 6px radius, 10px horizontal and 4px vertical padding, 4px between segments.
- **Selected:** 7% white wash, `ink-hi` text, 500 weight.
- **Unselected:** transparent, `ink-low`, 400 weight; hover lifts to `ink-mid`.
- **Transition:** colour only, 150ms. No size, position or background-size animation.

### Quiet Link (submit)

The only outbound action on the page, deliberately not a button.

- **Style:** `ink-low` text, underlined in `ink-lineStrong` with a 4px offset, 4px horizontal padding so the focus ring has room.
- **Hover:** text lifts to `ink-mid`; the underline does not change.
- **Character:** an available exit, never a call to action. Nothing on this page competes with reading the list.

### Band Head

- **Style:** optional 6px live dot, then an 11px uppercase title in `ink-mid`, then the group count in `ink-low`, all baseline-aligned with an 8px gap.
- **Behaviour:** sticky to the top of the viewport, opaque `ink-bg`, bleeding to the page gutters.
- **Dot:** present only on bands 0 and 1 (live today), marked `aria-hidden` since the band title already carries the meaning in words.

### Deal Row

The signature component and the reason the system exists.

- **Line one, left:** the offer at 18px/600 in `ink-hi` (`ink-mid` when stale or ended), with the unit basis inline beside it at 12.5px/500 in `ink-low`. When the offer string only names a deal type, this slot carries the deal's headline instead, at the same 18px/600 with `leading-[1.28]`, and it spans the full width with no status opposite it. See The Informative Lead Rule.
- **Line one, right:** status in `ink-mid`, dropping to `ink-low` when the status reports an absence ("no end date given") or the deal is stale. Omitted here on a headline-led row, where it moves to line two.
- **Line two, left:** the off-category tag, then the deal-type tag on a headline-led row, then "All *chain* locations" at 14px with the chain in `ink-hi`. Tags precede the location so a category flag can never be misread as part of it.
- **Line two, right:** "checked *date*" in `ink-low`, always present, preceded by the status on a headline-led row.
- **Below, full width:** the headline at 12.5px in `ink-mid` (suppressed when it has been promoted to line one), then metadata joined by middle dots, then conditions.
- **Suppressed content:** conditions are omitted on an ended deal, whose terms are no longer actionable, and when they merely restate the headline — a strict restatement only, shorter than the headline with at least 80% of its words already in it. Anything that adds a term, a limit or an exclusion keeps its own line.
- **Divider:** 1px `ink-line` below, suppressed on the last row of a band.

**The Honest Slot Rules.** These are data-integrity rules that show up as visual rules, and they bind every future surface:

1. **Unit basis renders as part of the price or not at all.** It is never given a stand-in word. A reader who sees "bundle" in that slot learns the slot means "kind of deal", and would then read a later "/ 100g" as a category rather than as the thing that makes the price mean anything.

   **This path is unexercised by live data, and must be visually verified the first time it is not.** Every price currently on the page is a bare figure, and that is correct: every live approved deal is genuinely flat-priced. The extractor does produce `per_100g` — deal #79 carries it but is expired, and #131 and #132 carry it but were rejected as duplicates — so none of them reach `getActiveDeals`. The consequence is that `basisLabel` and its rendering have never run against a deal a visitor can see.

   When the first live `per_100g` deal is approved, open the page and look at it. Do not infer from the code that it worked. This is the one constraint on this surface where a failure is invisible to the person it harms: a per-100g price rendered as a flat price looks completely normal, reads as a bargain, and gives the visitor nothing to be suspicious of. Every other honesty rule here fails loudly — a missing date, an empty location, a wrong count. This one fails silently, so it is the one that gets checked by eye.
2. **A stale or ended deal is dimmed and dated, never hidden.** Ended deals are excluded from the "on offer" count but stay on the page with their end date, so a deal never vanishes without saying why.
3. **Location is "All *chain* locations" or nothing.** Store-level data does not exist. No placeholder, no "Melbourne", no guess.
4. **The coverage claim is exactly "16 Instagram accounts and 2 websites."** It is a fact about `chains.yaml`, not a marketing number, and it changes only when the source list does.
5. **Absence is printed.** "no end date given", "never checked", and the empty state's "Nothing is being hidden" all say what is missing rather than leaving a gap the reader has to interpret.

## Submission Controls

**These are additions, proposed rather than assumed.** The dashboard is a reading surface and needed no input of any kind, so the system had no field, no button and no error treatment. `/submit` cannot exist without them. They introduce **no new tokens**: every value below already exists. If a later surface needs something these do not cover, add it here deliberately rather than inventing a local variant.

### Field Label

14px `ink-hi`, sentence case, with "(optional)" appended in `ink-low` so required and optional are distinguishable without an asterisk legend. An example or constraint goes on a 12.5px `ink-low` hint line directly beneath, wired to the input with `aria-describedby`.

### Text Field and Textarea

- **Shape:** transparent background, 1px `ink-line` border, 6px radius, 12px horizontal and 10px vertical padding. Never a filled surface: `surface-raised` is a state, not a surface family.
- **Text:** 18px `ink-hi`. Not 14px. See The 16px Floor Rule.
- **Hover:** border lifts to `ink-lineStrong`. **Focus:** the system focus ring.
- The textarea is `resize-y` only; horizontal resize breaks the column.

### Photo Picker

A visually hidden (`sr-only`) file input paired with a styled label, so the target is large and in-system while the control stays a real input. `peer-focus-visible` carries the focus ring to the visible box. Empty it reads "Take or choose a photo" (14px `ink-hi`) over "jpg, png or heic · up to 10MB" (12.5px `ink-low`). Filled it swaps to the file name, truncated, over size and "tap to replace", with a 48px 6px-radius thumbnail of the chosen file on the right.

The thumbnail is the one place imagery appears in this system. It is the submitter's own local file via an object URL, never uploaded content served back, and it exists because a camera roll is full of near-identical shots and picking the wrong one is the likeliest error in the scene. It does not license imagery anywhere else.

**No `required` attribute.** The input is visually hidden, so a native validation bubble anchors to a 1px box. The guard lives in the submit handler and reports through the error line.

### Primary Action

The system's only button. Full width, 6px radius, `ink-hi` background with `ink-bg` text (17.69:1), 14px/500 label. Disabled and busy take `surface-raised` with `ink-low` text. It is an inversion of the ground, not a coloured button: the accent is not available for calls to action under The Live-Only Rule.

### Error Line

12.5px `ink-hi`, `role="alert"`, sitting directly above the primary action. **Errors get no colour.** On a surface where almost everything is `ink-mid` or `ink-low`, promoting a line to `ink-hi` already makes it the brightest thing on screen, and the message names the problem and the recovery in words. A red token was considered and deliberately not added; if one is ever introduced it must be for a state that words cannot carry.

### Received State

Replaces the form in place: an 18px heading, a 12.5px `ink-mid` explanation, and one quiet action. It never reports an extraction result, a timeframe, or an outcome, because the extractor runs on a schedule and nothing on this surface identifies the submitter.

### Named Rules

**The 16px Floor Rule.** Any field a person types into is 18px, never the 14px step. iOS Safari zooms the viewport on focus for any input under 16px, which throws a one-handed user out of position mid-form. This is the one place the type scale is chosen by a platform behaviour rather than by hierarchy.

**The Example Under The Label Rule.** Examples and constraints go on a hint line under the label, never in a placeholder. A placeholder holding an example is value-shaped text in a value-shaped slot; at 18px on a dark ground it reads as something already entered, and it disappears exactly when the user needs it.

**The Told Once Rule.** Every claim on `/submit` is verified against what the code actually does before it ships. EXIF stripping is stated because `ingest/submit.py` calls `sanitize_image`; review before appearing is stated because user submissions never auto-approve. No timeframe is promised, no outcome is implied, and no language suggests a reply, because there is no stored identity to reply to.

### Focus Ring (system-wide)

Every interactive element shares one treatment: the native outline is removed and replaced with a 2px ring in `live` at 70% opacity, offset 2px against `ink-bg`, on `:focus-visible` only. This is the accent's second and last job. Keyboard users get an unmistakable green marker; mouse users never see it.

## Do's and Don'ts

### Do:
- **Do** hold the palette at one accent on a neutral ground. `#43D9A3` for availability and focus; everything else is ink.
- **Do** assign ink by role: `ink-hi` subject, `ink-mid` the deal's own words and real dates, `ink-low` supporting detail, absent facts and dimmed states.
- **Do** stay inside the five type steps (22 / 18 / 14 / 12.5 / 11) and reach for weight or ink before a new size.
- **Do** set every digit with tabular figures.
- **Do** keep the provenance column ("checked *date*") on every row, at fixed width, right-aligned.
- **Do** print absence in words: "no end date given", "never checked", "Nothing is being hidden".
- **Do** dim and date a stale or ended deal instead of removing it, and keep ended deals out of any "on offer" count.
- **Do** separate with 1px `ink-line` hairlines and space.
- **Do** make sticky band heads fully opaque and bleed them to the gutters.
- **Do** use `:focus-visible` with the 2px `live` ring at 70%, offset 2px on `ink-bg`, on every interactive element.
- **Do** keep motion to colour transitions on interaction, around 150ms.

### Don't:
- **Don't** use the accent for value, savings, urgency, branding, or a call to action. Availability and focus only.
- **Don't** add a sixth type step, or set body copy above 12.5px to "make it more readable" — the size ladder is what makes the scan work.
- **Don't** rank deal types typographically. Every offer value is 18px/600 regardless of type.
- **Don't** invent a value score, a "best deal" marker, a savings badge, or a discount percentage the source did not state.
- **Don't** put a stand-in word in the unit-basis slot. Real basis or empty.
- **Don't** name a store or a suburb. "All *chain* locations" or nothing.
- **Don't** add box-shadows, card backgrounds, borders around rows, gradients, or backdrop blur. The ground is flat.
- **Don't** add a hero, imagery, an icon set, a badge system, a filter bar, or a deal-card grid. Each of these was refused by name in the direction contract.
- **Don't** add an entrance animation, a stagger, a skeleton shimmer, or a scroll-triggered reveal. Content that fades in is content that is not yet readable.
- **Don't** hide anything behind a disclosure, an accordion, or a "show more". Everything the page knows is on the page.
- **Don't** override Tailwind's `fontFamily.sans` or apply the `ink` scale globally. The dark ground is scoped to the `.froyo` subtree on purpose.
- **Don't** treat `/review`, `/submit` or `/login` as precedent. They are unstyled defaults and out of scope; if one of them is ever designed, it inherits this system rather than the reverse.
- **Don't** propose a metaphor, a borrowed visual world, or a clever name. Convention is the chosen commitment, recorded in PRODUCT.md, after three re-rolls.
