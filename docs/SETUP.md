# Setup and operations

Everything beyond getting the dashboard up locally. The short path is in the
[README](../README.md).

## Schema and seed

Raw SQL migrations under `db/migrations/`, applied by a runner script. Chains are
seeded from `config/chains.yaml`.

```
cp .env.example .env
docker compose up -d
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m db.migrate
python -m db.seed
```

Check it worked:

```
docker compose exec db psql -U froyo -d froyo -c '\dt'
docker compose exec db psql -U froyo -d froyo -c 'select name from chains order by name;'
```

Expect the five tables (chains, stores, prices, raw_captures, deals) and the
seeded chains.

`docker-compose.yml` defaults `POSTGRES_PASSWORD` to `froyo`, a throwaway for a
container bound to localhost. Set `POSTGRES_PASSWORD` in `.env` to override it,
and keep the password in `DATABASE_URL` in step with it.

## Manual ingestion

Ingest a caption into `raw_captures`. For text, **use `--stdin`** (or `--file`).
`--stdin` is the default because it is immune to shell expansion: with `--text`,
an unquoted or double-quoted `$3` is expanded away by the shell before Python
sees it, silently dropping the price.

```
# preferred: stdin (paste text, then Ctrl-D), or pipe / heredoc
python -m ingest.manual --stdin <<'CAPTION'
$3 per 100g self serve froyo, in store only
CAPTION

# from a file
python -m ingest.manual --file caption.txt

# inline: only for text with no $ signs; warns on shell-expansion signatures
python -m ingest.manual --text 'buy 9 get the 10th free'

# an image
python -m ingest.manual --image path/to.jpg
```

Duplicate captions are deduped on a content hash of the normalised text.

## Instagram ingestion

Instagram captures come from a **private ingestion source that is not part of
this repository.** `ingest/scrapers/instagram.py` is the interface stub it
satisfies, and `ingest/scrape_instagram.py` is the public runner that wires it to
the database. A run in this checkout raises `NotImplementedError` and writes
nothing.

Everything around it is here and unchanged: monitored accounts are the non-null
`instagram_handle` values in `config/chains.yaml`, captures land in
`raw_captures` deduped on a content hash, per-account high-water marks live in
`instagram_seen`, and extraction runs separately on its own schedule. Instagram
captures never auto-approve, so every one is reviewed by hand at `/review`.

```
python -m ingest.scrape_instagram
```

## Extraction

```
python -m ingest.extract
```

Reads unprocessed `raw_captures` and writes pending deals. Results are cached per
caption, keyed on `content_hash + prompt_hash`, so a re-run over unchanged
captions costs nothing. That cache is also why a green test suite can be
meaningless; see [HOLDOUT.md](../tests/fixtures/HOLDOUT.md).

## Deployment

**Everything runs on one Mac.** A Cloudflare Tunnel publishes the two public
surfaces and nothing else. There is no cloud host, no managed database, and no
split codebase: Postgres stays in local Docker, media stays under `MEDIA_ROOT`,
and `/api/submit` keeps spawning the local Python venv, all exactly as built.

An earlier plan used a Binary Lane VPS. That is cancelled. A Vercel plus Neon
split was costed and rejected: it would have made `/submit` unreachable for the
people who actually use it, since a serverless function has no Python, no venv
and no writable disk. See DEFERRED.md.

### What the tunnel publishes

The ingress rules in `ops/cloudflared/config.yml` are an **allowlist**. Anything
not named there is served a 404 by cloudflared and never reaches this machine, so
a route added later is private by default rather than public by accident.

| path | on the internet | why |
|---|---|---|
| `/` | yes | the public dashboard |
| `/submit` | yes | friends send in promo signs from their phones |
| `/api/submit` | yes | the only API route that form posts to |
| `/_next/*` | yes | build assets for the two pages above |
| `/review`, `/login` | **no** | operator only, localhost only |
| `/api/image` | **no** | serves submission photos, which are never public |
| `/api/deals/*`, `/api/logout` | **no** | review-queue mutations |

The public list was derived by loading both public pages in a browser and
recording every request they make, not by guessing.

**Path restriction needs a named tunnel with a config file**, which means a
hostname on a domain in your Cloudflare account. A quick tunnel (`cloudflared
tunnel --url ...`, the random `trycloudflare.com` kind that needs no account)
serves a single origin and ignores ingress rules entirely, so it cannot do this.

`web/middleware.ts` is a second, independent guard: any request carrying
Cloudflare's `cf-ray` header for a non-public path is refused by the app itself,
so the private routes stay private even if the tunnel config is wrong or someone
starts a quick tunnel by mistake. Localhost requests carry no such header and are
unaffected.

### Tunnel setup

```
brew install cloudflared
cloudflared tunnel login                 # opens a browser, needs your account
cloudflared tunnel create froyo          # prints the tunnel UUID
cloudflared tunnel route dns froyo <your-hostname>
```

Then copy `ops/cloudflared/config.yml`, replacing `TUNNEL_NAME`, `TUNNEL_UUID`,
`FROYO_HOSTNAME` and the credentials-file path, and check the rules do what they
claim **before** running it:

```
cloudflared tunnel --config ops/cloudflared/config.yml ingress validate
cloudflared tunnel --config ops/cloudflared/config.yml ingress rule https://<your-hostname>/review
```

The second command must print `http_status:404`. Try it for `/login`,
`/api/image` and `/api/deals/search` too. Then:

```
cloudflared tunnel --config ops/cloudflared/config.yml run froyo
```

Run `npm run start` (or `npm run dev`) in `web/` alongside it. To keep the tunnel
up across reboots, `cloudflared service install` or a third LaunchAgent beside
the two in `ops/`.

### The tradeoff

**The site is up only while that Mac is awake and online.** That is not a new
dependency: the scrapes at 08:30 and 18:30 and the jobs at 03:35 already require
it. It does mean friends get nothing while the laptop sleeps. If that turns out
to matter, DEFERRED.md records the follow-up.

## Scheduling on macOS (launchd)

cron does not fire while the laptop is asleep and does not catch up missed runs;
launchd's `StartCalendarInterval` does fire on wake, so it is the macOS path.
`ops/crontab` remains the Linux (always-on server) path.

**The repo must NOT live in `~/Desktop`, `~/Documents` or `~/Downloads`.** macOS
protects those directories (TCC), and launchd cannot read a wrapper script inside
them without granting Full Disk Access; it fails with `Operation not permitted`.
Keep the checkout somewhere unprotected such as `~/froyo`. If you relocate it,
update the absolute paths in `ops/com.froyo.scrape.plist` and
`ops/com.froyo.jobs.plist` (and reload them), and the path in `ops/crontab`; the
wrapper scripts derive the repo from their own location, so they need no change.

Two **LaunchAgents** (user GUI session, because ingestion may need one):

- `com.froyo.scrape` -> `ops/froyo-scrape.sh`: website scrape (**morning run
  only**, since chain promo pages do not change twice a day) plus Instagram
  scrape, then one extract, at **08:30 and 18:30**. The two scrapes are
  independent: a failure in one does not stop the other or the extract.
- `com.froyo.jobs` -> `ops/froyo-jobs.sh`: expire, reverify (**Mondays only**,
  matching the polite weekly cadence; delete the Monday guard in the wrapper for
  nightly), merge_dupes, at **03:35**.

Each wrapper owns its own logging: it creates `logs/`, redirects itself to
`logs/scrape.log` / `logs/jobs.log` (gitignored), prints a timestamped start line
first, and runs Python with `-u`, so output appears immediately and does not
depend on launchd's `StandardOutPath` dir existing. It also logs the interpreter
it is using (`sys.executable | prefix ...`); confirm the prefix is this repo's
`.venv`. Then it verifies the venv can `import psycopg` (aborting loudly if not)
and that Postgres is reachable (if Docker Desktop is down it logs `SKIPPED -
Postgres unreachable` and exits, no stack trace). The plists carry absolute paths
(launchd requires them); set them to your own checkout.

**Verifying the venv, not via ps.** The venv's `python` is a symlink to
Homebrew's framework python, which re-execs itself, so `ps` and Activity Monitor
show the Homebrew path (for example `.../python@3.14/.../Python`) even though the
venv is active. Do not use ps to check the interpreter. Read the wrapper's
`python ... | prefix ...` log line (the prefix is `<repo>/.venv`), or run
`.venv/bin/python -c 'import psycopg, sys; print(sys.prefix, psycopg.__file__)'`.

### Load

```
mkdir -p logs
cp ops/com.froyo.scrape.plist ops/com.froyo.jobs.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.froyo.scrape.plist
launchctl load ~/Library/LaunchAgents/com.froyo.jobs.plist
```

### Unload

```
launchctl unload ~/Library/LaunchAgents/com.froyo.scrape.plist
launchctl unload ~/Library/LaunchAgents/com.froyo.jobs.plist
```

### Trigger a run now (does not wait for the schedule)

```
launchctl start com.froyo.jobs        # by Label
bash ops/froyo-jobs.sh                # or run the wrapper directly
```

### Status and logs

```
launchctl list | grep com.froyo
tail -f logs/jobs.log logs/scrape.log
```

On Big Sur and later, if `load` / `unload` are deprecated on your system, the
equivalents are:

```
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.froyo.jobs.plist
launchctl bootout   gui/$(id -u)/com.froyo.jobs
launchctl kickstart -k gui/$(id -u)/com.froyo.jobs   # trigger now
```
