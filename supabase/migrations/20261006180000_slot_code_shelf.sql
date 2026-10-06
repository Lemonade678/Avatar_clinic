-- 6/10 round 4 (ณัฑฒ์): the last two digits of a slot code name the shelf unit, not a position.
-- L0301 = left side, storey 3, shelf unit 01 — MBK has one shelf unit per side.

update locations set shelf = substring(code from 4 for 2)::int;

alter table locations drop column position;

alter table locations add constraint locations_code_matches_parts
  check (code = side || lpad(storey::text, 2, '0') || lpad(shelf::text, 2, '0'));
