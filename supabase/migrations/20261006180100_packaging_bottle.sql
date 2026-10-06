-- 6/10 round 4 (ณัฑฒ์): CABA and banana juice are plain bottles — a ninth class next to the spray bottle.

alter table products drop constraint if exists products_packaging_check;

alter table products add constraint products_packaging_check
  check (packaging in ('book', 'jar', 'paper_wrap', 'bag', 'bottle', 'spray_bottle', 'box', 'tote_bag', 'tin'));
