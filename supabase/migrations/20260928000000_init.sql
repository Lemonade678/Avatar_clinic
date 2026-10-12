-- Stock count POC (back store, Ladprao branch)

create table products (
  sku      text primary key,
  name     text not null,
  category text not null
);

create table shelves (
  code  text primary key,
  label text not null
);

-- on update cascade: product codes can be corrected later without breaking history
create table shelf_products (
  shelf_code text not null references shelves(code) on update cascade on delete cascade,
  sku        text not null references products(sku) on update cascade,
  position   int  not null,
  primary key (shelf_code, sku)
);

create table stock_snapshots (
  sku      text not null references products(sku) on update cascade,
  back_qty int  not null,
  as_of    date not null,
  primary key (sku, as_of)
);

create table count_sessions (
  id         uuid primary key default gen_random_uuid(),
  count_date date not null unique,
  opened_at  timestamptz not null default now(),
  closed_at  timestamptz
);

create table counts (
  session_id   uuid not null references count_sessions(id) on delete cascade,
  shelf_code   text not null,
  sku          text not null references products(sku) on update cascade,
  expected_qty int  not null,
  counted_qty  int  not null check (counted_qty >= 0),
  line_user_id text not null,
  updated_at   timestamptz not null default now(),
  primary key (session_id, sku)
);

create table user_state (
  line_user_id text primary key,
  shelf_code   text not null,
  opened_at    timestamptz not null
);

create table shelf_photos (
  id           uuid primary key default gen_random_uuid(),
  session_id   uuid not null references count_sessions(id) on delete cascade,
  shelf_code   text not null,
  storage_path text not null unique,
  line_user_id text not null,
  created_at   timestamptz not null default now()
);

-- RLS on with no policies: only the service key (server side) can read/write
alter table products        enable row level security;
alter table shelves         enable row level security;
alter table shelf_products  enable row level security;
alter table stock_snapshots enable row level security;
alter table count_sessions  enable row level security;
alter table counts          enable row level security;
alter table user_state      enable row level security;
alter table shelf_photos    enable row level security;

insert into storage.buckets (id, name, public)
values ('shelf-photos', 'shelf-photos', false)
on conflict (id) do nothing;
