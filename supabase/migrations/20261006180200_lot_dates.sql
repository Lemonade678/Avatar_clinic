-- 6/10 round 4 (ณัฑฒ์ chose "A + C"): every product may stay on sale for 2 years (ministry rule).
-- manual  = the date written on the oldest pack, typed in on the lots page (the newest entry wins)
-- receipt = a receiving date + quantity from the old stock system's export; the app estimates the
--           oldest lot still in stock first-in-first-out from the quantity on hand

create table lot_dates (
  id           bigint generated always as identity primary key,
  sku          text not null references products(sku) on update cascade on delete cascade,
  lot_date     date not null,
  source       text not null check (source in ('manual', 'receipt')),
  qty          int  check (qty > 0),
  line_user_id text,
  recorded_at  timestamptz not null default now(),
  constraint lot_dates_receipt_has_qty check (source = 'manual' or qty is not null)
);

create index lot_dates_sku_idx on lot_dates (sku);

-- RLS on with no policies: only the service key (server side) can read/write
alter table lot_dates enable row level security;
