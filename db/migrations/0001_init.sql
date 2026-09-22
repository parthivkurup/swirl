create type unit_kind as enum ('per_100g', 'each', 'per_serve');
create type price_channel as enum ('instore', 'ubereats', 'doordash', 'menulog');
create type deal_kind as enum ('percent_off', 'dollar_off', 'fixed_price', 'bogo', 'freebie', 'loyalty', 'bundle');
create type discount_unit_kind as enum ('percent', 'aud');
create type deal_status as enum ('pending', 'approved', 'rejected', 'expired');

create table chains (
  id serial primary key,
  name text unique not null,
  website text,
  instagram_handle text,
  has_loyalty_app boolean not null default false
);

create table stores (
  id serial primary key,
  google_place_id text unique,
  name text not null,
  chain_id integer references chains(id),
  address text,
  suburb text,
  lat double precision,
  lng double precision,
  active boolean not null default true,
  last_seen timestamptz
);

create table prices (
  id bigserial primary key,
  store_id integer not null references stores(id),
  item_name text not null,
  unit unit_kind not null,
  amount_cents integer not null,
  channel price_channel not null,
  source_url text,
  observed_at timestamptz not null default now()
);
create index prices_store_observed_idx on prices (store_id, observed_at desc);

create table raw_captures (
  id bigserial primary key,
  source_type text not null,
  source_url text,
  content_text text,
  image_path text,
  content_hash text unique not null,
  processed boolean not null default false,
  captured_at timestamptz not null default now()
);

create table deals (
  id bigserial primary key,
  chain_id integer references chains(id),
  store_id integer references stores(id),
  deal_type deal_kind not null,
  headline text not null,
  discount_value numeric,
  discount_unit discount_unit_kind,
  conditions text,
  min_spend_cents integer,
  max_grams integer,
  channels text[],
  days_of_week integer[],
  valid_from date,
  valid_to date,
  recurring boolean not null default false,
  source_type text,
  source_url text,
  source_hash text unique,
  confidence numeric,
  status deal_status not null default 'pending',
  first_seen timestamptz not null default now(),
  last_verified timestamptz
);
create index deals_status_valid_to_idx on deals (status, valid_to);
