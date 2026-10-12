-- 6/10: packaging classes from ณัฑฒ์ — paper medicine bag, plastic medicine bag, plastic bottle,
-- box, tote bag, inhaler tin. Old guesses (bottle/pouch/bag/book) are cleared; run import_csv.py again.

alter table products drop constraint if exists products_packaging_check;

update products set packaging = null
where packaging is not null
  and packaging not in ('paper_bag', 'plastic_bag', 'plastic_bottle', 'box', 'tote_bag', 'tin');

alter table products add constraint products_packaging_check
  check (packaging in ('paper_bag', 'plastic_bag', 'plastic_bottle', 'box', 'tote_bag', 'tin'));
