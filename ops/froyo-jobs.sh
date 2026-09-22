#!/bin/bash
# Froyo maintenance jobs, run by launchd (com.froyo.jobs) at 03:35: expire past
# deals, reverify sources (weekly), merge duplicates. launchd fires a missed run
# on wake, unlike cron.
#
# Logging: the wrapper owns its own log (creates logs/, redirects itself, prints a
# start line first, runs python with -u) so output appears immediately and does not
# depend on launchd's StandardOutPath dir existing. PY is the venv python (a symlink
# to Homebrew's framework python, so ps shows the Homebrew path though the venv is
# active - verify via the "python ..." line below, not ps).
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
PY="$REPO/.venv/bin/python"
ts() { date "+%Y-%m-%dT%H:%M:%S%z"; }

mkdir -p "$REPO/logs"
exec >> "$REPO/logs/jobs.log" 2>&1
echo "$(ts) jobs: run starting (pid $$)"
echo "$(ts) jobs: python $("$PY" -c 'import sys; print(sys.executable, "| prefix", sys.prefix)' 2>&1)"

if ! "$PY" -c "import psycopg" >/dev/null 2>&1; then
  echo "$(ts) jobs: ABORT - $PY cannot import psycopg (venv broken?)"
  exit 1
fi
if ! "$PY" -c "from ingest.db import connect; connect().close()" >/dev/null 2>&1; then
  echo "$(ts) jobs: SKIPPED - Postgres unreachable (is Docker Desktop running?)"
  exit 0
fi

echo "$(ts) jobs: expire_deals"
"$PY" -u -m ingest.expire_deals

# reverify hits each approved deal's source with a polite fetch, so keep it WEEKLY
# (Mondays), matching the original cron cadence, rather than nightly. To run it
# every night instead, delete this Monday guard.
if [ "$(date +%u)" = "1" ]; then
  echo "$(ts) jobs: reverify (weekly, Monday)"
  "$PY" -u -m ingest.reverify
fi

echo "$(ts) jobs: merge_dupes --commit"
"$PY" -u -m ingest.merge_dupes --commit
echo "$(ts) jobs: done"
