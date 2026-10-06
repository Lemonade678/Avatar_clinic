from pathlib import Path

import pytest

MIGRATIONS = sorted((Path(__file__).parents[1] / "supabase" / "migrations").glob("*.sql"))


@pytest.mark.parametrize("path", MIGRATIONS, ids=lambda p: p.name)
def test_migration_is_valid_postgres_sql(path):
    pglast = pytest.importorskip("pglast")  # Postgres's own parser; syntax only, no database needed
    assert pglast.parse_sql(path.read_text(encoding="utf-8"))


def test_migrations_run_in_name_order():
    names = [p.name for p in MIGRATIONS]
    assert names == sorted(names) and len(names) >= 2


def test_database_packaging_classes_match_the_code():
    # the newest CHECK on products.packaging must list exactly layout.PACKAGING, or imports would fail
    import re

    from stockcount.layout import PACKAGING

    checks = [
        m.group(1)
        for p in MIGRATIONS
        for m in re.finditer(r"check \(packaging in \(([^)]*)\)\)", p.read_text(encoding="utf-8"))
    ]
    assert checks, "no packaging CHECK found"
    assert tuple(re.findall(r"'([a-z_]+)'", checks[-1])) == PACKAGING


def test_database_bag_subclasses_match_the_code():
    import re

    from stockcount.layout import SUBCLASSES

    checks = [
        m.group(1)
        for p in MIGRATIONS
        for m in re.finditer(r"packaging_sub in \(([^)]*)\)", p.read_text(encoding="utf-8"))
    ]
    assert checks and tuple(re.findall(r"'([a-z_]+)'", checks[-1])) == SUBCLASSES["bag"]


def test_locations_drop_the_position_column():
    # 6/10 round 4: the code's last two digits are the shelf, and the seed no longer sends a position;
    # the old NOT NULL column would make every location insert fail
    text = "\n".join(p.read_text(encoding="utf-8") for p in MIGRATIONS)
    assert "alter table locations drop column position" in text
