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
