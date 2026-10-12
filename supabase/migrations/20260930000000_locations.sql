-- v2 (30/9): slot layout from data/layout_mbk.csv, front-store quantity, time clock, CV results

-- products know which packaging class the small CV model should see
alter table products add column packaging text
  check (packaging in ('bottle', 'pouch', 'bag', 'box', 'book'));

-- slots replace the old free-form shelves: code = <L|R><storey:02><position:02>, x = shelf unit
create table locations (
  code       text primary key,
  side       text not null check (side in ('L', 'R')),
  storey     int  not null check (storey > 0),
  position   int  not null check (position > 0),
  shelf      int  not null default 1 check (shelf > 0),
  cv_enabled boolean not null default true
);

-- one slot per product (the layout loader rejects a product placed twice)
create table product_locations (
  sku           text primary key references products(sku) on update cascade on delete cascade,
  location_code text not null references locations(code) on update cascade on delete cascade
);

drop table shelf_products;
drop table shelves;

-- the pilot checks the front-store (หน้าร้าน) quantity
alter table stock_snapshots add column front_qty int not null default 0;

-- time clock: started_at .. ended_at, and who counted
alter table count_sessions rename column opened_at to started_at;
alter table count_sessions rename column closed_at to ended_at;
alter table count_sessions add column line_user_id text;

-- counts belong to a slot (no FK: history must survive layout changes)
alter table counts rename column shelf_code to location_code;
alter table counts add column input_method text not null default 'type'
  check (input_method in ('type', 'voice'));

-- CV cross-check results live next to each photo (= the phase 2–3 dataset)
alter table shelf_photos rename column shelf_code to location_code;
alter table shelf_photos add column cv_counts    jsonb;
alter table shelf_photos add column human_counts jsonb;
alter table shelf_photos add column cv_status    text not null default 'skipped'
  check (cv_status in ('ok', 'flagged', 'skipped'));
alter table shelf_photos add column brightness   real;

-- the web UI carries the slot in its URL, so per-user chat state is gone
drop table user_state;

-- RLS on with no policies: only the service key (server side) can read/write
alter table locations         enable row level security;
alter table product_locations enable row level security;
