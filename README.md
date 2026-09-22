# Swirl

Swirl tracks frozen yoghurt promotions across Melbourne: it captures what shops post,
extracts structured offers with an LLM, and publishes only what a human approved.

## What makes it interesting

- **Two-stage pipeline.** Scrapers write immutable `raw_captures` and never touch
  `deals`, so extraction can be re-run over all of history when the prompt changes
  and every deal traces back to its source text.
- **Human review with pre-review dedupe.** Anything not from a chain's own promo page
  waits for a person, and is first scored against the pending and approved pool so a
  repost surfaces as a review hint, not a second row. A nightly job merges, reversibly.
- **Honesty rules in the schema.** A deal carries a `scope` and the one unattended
  publish path refuses anything not established as Melbourne. Rows say "checked" when
  the source can be re-fetched and "seen" when not, dating staleness from the evidence.
- **A holdout set, and honest measurement.** Scored on in-sample fixtures, on a holdout
  the prompt never saw, and on an ablation set forcing offers out of images. Extractions
  cache per caption, so a green suite can be scoring the cache rather than the model.

## Stack

Python (psycopg, Gemini Flash), Postgres in Docker, Next.js and Tailwind for the web app.

## Running locally

```
cp .env.example .env              # GEMINI_API_KEY needed to extract, not to browse
docker compose up -d
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m db.migrate && python -m db.seed
cd web && npm install && npm run dev
```

Dashboard at `localhost:3000`. Ingestion, extraction, scheduling and deployment are in
[docs/SETUP.md](docs/SETUP.md); [PRODUCT.md](PRODUCT.md), [DESIGN.md](DESIGN.md) and
[tests/fixtures/HOLDOUT.md](tests/fixtures/HOLDOUT.md) for depth. The Instagram source
is private and not in this repository; `ingest/scrapers/instagram.py` is the stub.
