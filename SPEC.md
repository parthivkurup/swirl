# Melbourne Froyo Deal Tracker

Tracks frozen yoghurt promotions across Melbourne. Deals are the product.
Prices and store data are supporting features, built last.

## Stack
Python 3.11 ingestion, Postgres 16, Next.js 14 (app router) + Tailwind.
Single repo. docker-compose for local Postgres. No ORM, raw SQL migrations
under db/migrations, applied by a simple runner script.

## Build order

Build in phases. STOP at the end of each phase, run the stated check, and
report before continuing. Do not skip ahead. Do not build phase N+1 scaffolding
while in phase N.

### Phase 1: schema
Migrations for the tables below, plus a seed script reading chains from
config/chains.yaml.
CHECK: psql shows all five tables, chains populated.

### Phase 2: manual ingestion
CLI `python -m ingest.manual --text "..."` and `--image path/to.jpg`.
Writes one raw_captures row. Dedupe on content_hash.
CHECK: same caption twice produces one row.

### Phase 3: extractor
Gemini client, reads unprocessed raw_captures, writes deals as pending.
CHECK: run against tests/fixtures/captions/, inspect output manually.

### Phase 4: tests
pytest over fixture captions with expected JSON, plus negatives returning [].
CHECK: green, and deliberately corrupting the prompt file turns it red.

### Phase 5: review queue
/review in the dashboard. THIS IS THE MILESTONE. Build it properly.
CHECK: 20 deals approved through the UI end to end.

### Phase 6: website scraper
Config-driven, writes to raw_captures only. Daily cron.
CHECK: unattended overnight run leaves new pending items.

### Phase 7: public dashboard
/ with filters and staleness greying.

### Phase 8: jobs
expire_deals nightly, reverify weekly.

### Phase 9: stores and prices
Google Places grid sweep. Aggregator menu prices. Last on purpose.

## Schema

chains(id, name unique, website, instagram_handle, has_loyalty_app)

stores(id, google_place_id unique, name, chain_id fk, address, suburb,
lat, lng, active default true, last_seen)

prices(id bigserial, store_id fk, item_name, unit [per_100g|each|per_serve],
amount_cents int, channel [instore|ubereats|doordash|menulog], source_url,
observed_at default now()) index (store_id, observed_at desc)

raw_captures(id bigserial, source_type, source_url, content_text, image_path,
content_hash unique, processed bool default false, captured_at default now())

deals(id bigserial, chain_id fk null, store_id fk null,
deal_type [percent_off|dollar_off|fixed_price|bogo|freebie|loyalty|bundle],
headline not null, discount_value numeric, discount_unit [percent|aud],
conditions text, min_spend_cents int, max_grams int, channels text[],
days_of_week int[], valid_from date, valid_to date, recurring bool default false,
source_type, source_url, source_hash unique, confidence numeric,
status [pending|approved|rejected|expired] default pending,
first_seen default now(), last_verified) index (status, valid_to)

chain_id null means store-specific. store_id null means chain-wide.

## Ingestion architecture

Strictly two stage. Scrapers write to raw_captures and never touch deals.
The extractor reads raw_captures and writes deals. This separation exists
so extraction can be re-run over history when the prompt changes.

Provide `python -m ingest.extract --reprocess-since YYYY-MM-DD`.

Scrapers live in ingest/scrapers/, share one interface returning
list[RawCapture]:
- manual.py: text blob or local image path
- website.py (phase 6): fetches chain promo pages from config/scrapers.yaml
  containing url and CSS selectors per chain. Config-driven, nothing hardcoded.
- instagram.py, aggregator.py: stub the interface, raise NotImplementedError

content_hash = sha256 of normalised text: lowercase, collapse whitespace,
strip emoji and URLs.

## Extractor

google-genai SDK, model gemini-flash-latest, fall back to flash-lite on 429.
GEMINI_API_KEY in .env.

Use native structured output: responseMimeType application/json plus an
explicit responseSchema matching the deal object. Do not instruct the model
to return JSON in prose and do not strip code fences, the schema handles it.
Enum fields (deal_type, discount_unit, channels) declared as schema enums so
invalid values are impossible.

Images sent as inline_data base64 in the same request as the text. No separate
OCR step.

Batch up to 10 captures per request to conserve daily quota. Response is an
array of arrays, index-aligned to inputs. Any batch failing validation retries
as individual requests. 429 gets exponential backoff, and unprocessed captures
simply stay unprocessed for the next run.

System prompt lives in ingest/prompts/extract_deal.txt, loaded at runtime,
never inlined in code. Write it to this spec:

- Return [] when there is no genuine customer-facing promotion.
- Ignore: new flavour announcements, store openings, competitions or giveaways
  requiring entry, job ads, general brand advertising.
- Never infer anything not stated. Unknown fields are null.
- Fields: headline, deal_type, discount_value, discount_unit, conditions,
  min_spend_aud, max_grams, channels, days_of_week, valid_from, valid_to,
  recurring, store_hint, confidence.
- CAPTURE_DATE is supplied per request. Resolve relative dates against it.
- "$5 Tuesdays" maps to fixed_price / 5 / aud / days_of_week [2] / recurring true.
- Vague endings ("while stocks last", "this week only") leave valid_to null and
  preserve the exact wording in conditions.
- Weight caps in grams go to max_grams, never conditions.
- store_hint is any location named in the source, verbatim.
- confidence below 0.6 when terms are ambiguous or the image is partly illegible.

Post-processing in Python, not the prompt:
- Resolve store_hint to store_id by fuzzy match on stores.name plus suburb.
  No confident match leaves it null and attaches to chain if identifiable.
- Auto-approve only when confidence >= 0.8 AND source_type == 'website'.
  Everything else stays pending.
- source_hash prevents reposts creating duplicate deals.

## Dashboard

/review (phase 5, the primary operator surface)
Raw capture content on the left, extracted fields on the right, every field
editable. Approve, reject, edit-and-approve. Keyboard shortcuts j k a r.
Show the source image inline when present.

/ (phase 7)
Active approved deals, default sort last_verified desc. Filter by chain,
deal_type, day of week, suburb. Anything not verified in 14 days renders
greyed with the date visible rather than hidden.

/stores (phase 9)
Table with last scrape time per store.

## Jobs
expire_deals: nightly, valid_to < today becomes expired.
reverify: weekly, refetch source_url for approved deals, bump last_verified
or flag stale.

## Constraints
- Config in .env, never committed. Provide .env.example.
  GEMINI_API_KEY, DATABASE_URL, GOOGLE_PLACES_API_KEY.
- Comments only where the reasoning is non-obvious. No docstring padding.
- No em dashes anywhere, in code, prose, or UI copy.
- Structured JSON logging to stdout for every scrape and extract.
- pytest for the extractor. Fixtures live in tests/fixtures/captions/ as
  paired .txt and .expected.json.
