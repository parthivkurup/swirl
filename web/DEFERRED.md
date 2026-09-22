
## Deployment: options not taken (2026-08-09)

Shipped: Cloudflare Tunnel from the Mac, path-restricted to `/`, `/submit`,
`/api/submit` and `/_next/*`. See docs/SETUP.md, Deployment.

### C. Publish a static `/` from the Mac (the follow-up, if downtime matters)

The tunnel means the site is up only while the laptop is awake. If that turns
out to be a real nuisance rather than a theoretical one, this is the fix, and it
is simpler than moving anything to a cloud host.

`/` is read-only, about 18 rows, and its data changes ONLY when the scheduled
jobs run. It does not need a live database, it needs a rebuild after each job:
the Mac generates `/` as static HTML after each run and pushes it to Cloudflare
Pages (free, CLI deploy). No cloud database, no split codebase, no operator route
ever leaving this machine, and `/` survives sleep.

Two things to solve first:
- `/` is `force-dynamic` and reads Postgres per request, so it needs
  restructuring into a statically generated route, and its two toggle states
  (`/` and `?category=all`) become two routes.
- **The day boundary is the catch.** Band membership depends on today's date in
  Melbourne, so a page built at 18:30 is wrong from midnight until 08:30 when
  "available today" flips. Either add a fourth launchd run at about 00:05, or
  compute the day-dependent part client-side, which would reintroduce JavaScript
  to a page that currently ships 369 bytes of it.

`/submit` would still need the Mac, so the tunnel stays either way.

### A. Vercel for `/` plus Neon, operator surfaces local: REJECTED

Costed and turned down. It buys uptime for `/` and pays for it with the
submission surface:

- **`/submit` becomes unreachable for the people who use it.** It would exist
  only on localhost, and the dashboard's "Seen one? Send it in" link would point
  at something a friend standing in a shop cannot open. `/api/submit` spawns
  `.venv/bin/python`, and a serverless function has no Python, no venv and no
  repo checkout, so it cannot be lifted as-is.
- **It needs a fail-closed switch.** One codebase deployed twice means the
  operator routes must 404 on the public deploy; a wrong flag puts `/review` on
  the internet behind one shared password.
- **Ingestion would gain a network dependency.** The Mac writes to localhost
  Postgres today; against Neon, "no internet, no ingest" becomes a new failure
  mode the existing Docker-down guard does not cover.
- Keeping local Docker for dev plus Neon for real means two schemas that can
  drift; pointing everything at Neon means no offline development.

### D. Rewrite `/api/submit` to be serverless-native: REJECTED

Strip EXIF in TypeScript, put the image in object storage, insert the capture row
directly, no Python in the request path. It is the only shape where everything
works with the Mac asleep, and it was still turned down: EXIF stripping is the
most safety-critical step in the product, and this would create a second
implementation of it in another language. The repo already carries one
cross-language duplication (`ingest/dedupe.py` is a port of `web/lib/dedupe.ts`,
and both must stay in sync). Duplicating the privacy-critical path is a worse
version of a problem we already have.
