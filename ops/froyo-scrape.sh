#!/bin/bash
# Froyo scrape + extract, run by launchd (com.froyo.scrape) at 08:30 and 18:30.
# The two sources are scraped INDEPENDENTLY, then a single extract processes
# whatever new captures landed. The website scrape runs on the MORNING run only
# (chain promo pages do not change twice a day), gated the way reverify is gated to
# Mondays. Instagram runs both times. No set -e and each scrape is guarded with ||,
# so a failure in one source never stops the other or the extract. launchd fires
# missed runs on wake, unlike cron. A LaunchAgent rather than a daemon, because
# ingestion may need a GUI session.
#
# Logging: the wrapper owns its own log (creates logs/, redirects itself, prints a
# start line first, runs python with -u) so output appears immediately and does not
# depend on launchd's StandardOutPath dir existing. Note: PY is the venv python,
# which is a symlink to Homebrew's framework python, so ps / Activity Monitor show
# the Homebrew path even though the venv is active - verify via the "python ..."
# line below (sys.prefix must be this repo's .venv), not via ps.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
PY="$REPO/.venv/bin/python"
ts() { date "+%Y-%m-%dT%H:%M:%S%z"; }

mkdir -p "$REPO/logs"
exec >> "$REPO/logs/scrape.log" 2>&1
echo "$(ts) scrape: run starting (pid $$)"
echo "$(ts) scrape: python $("$PY" -c 'import sys; print(sys.executable, "| prefix", sys.prefix)' 2>&1)"

# Fail loudly if the venv python cannot import our deps, instead of the misleading
# "Postgres unreachable" the DB check would otherwise report.
if ! "$PY" -c "import psycopg" >/dev/null 2>&1; then
  echo "$(ts) scrape: ABORT - $PY cannot import psycopg (venv broken?)"
  exit 1
fi
# Postgres must be reachable. If Docker Desktop is not running, log one clear line
# and skip instead of a stack trace, so a missed run is identifiable in the log.
if ! "$PY" -c "from ingest.db import connect; connect().close()" >/dev/null 2>&1; then
  echo "$(ts) scrape: SKIPPED - Postgres unreachable (is Docker Desktop running?)"
  exit 0
fi

# Website scrape: morning run only. The "08" here must match the morning
# StartCalendarInterval hour in com.froyo.scrape.plist.
if [ "$(date +%H)" = "08" ]; then
  echo "$(ts) website: scrape starting"
  "$PY" -u -m ingest.scrape || echo "$(ts) website: scrape FAILED (rc=$?), continuing"
else
  echo "$(ts) website: skipped (not the morning run)"
fi

# Instagram scrape: both runs. Independent of the website scrape above; its
# failure does not stop the extract below. The capture source is private and not
# included in this repository, so in this checkout the runner exits non-zero
# without writing anything and the || branch below logs it and carries on.
echo "$(ts) instagram: scrape starting"
"$PY" -u -m ingest.scrape_instagram || echo "$(ts) instagram: scrape FAILED (rc=$?), continuing"

# One extract for whatever new captures either scrape produced. Runs regardless of
# the scrape outcomes; cheap no-op when there is nothing new.
echo "$(ts) extract: starting"
"$PY" -u -m ingest.extract || echo "$(ts) extract: FAILED (rc=$?)"
echo "$(ts) scrape: done"
