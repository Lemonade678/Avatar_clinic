-- 6/10 round 3: classes from ณัฑฒ์ — book, jar (glass or plastic), paper wrap (boiled herbs), bag,
-- spray bottle, box, tote bag, inhaler tin. Blue medicine bags and supplement bags are kinds of bag.
-- Old values are cleared; run import_csv.py again to fill them from data/layout_mbk.csv.

alter table products drop constraint if exists products_packaging_check;

update products set packaging = null
where packaging is not null
  and packaging not in ('book', 'jar', 'paper_wrap', 'bag', 'spray_bottle', 'box', 'tote_bag', 'tin');

alter table products add constraint products_packaging_check
  check (packaging in ('book', 'jar', 'paper_wrap', 'bag', 'spray_bottle', 'box', 'tote_bag', 'tin'));

alter table products add column packaging_sub text;
alter table products add constraint products_packaging_sub_check
  check (packaging_sub is null or (packaging = 'bag' and packaging_sub in ('medicine_bag', 'supplement_bag')));
