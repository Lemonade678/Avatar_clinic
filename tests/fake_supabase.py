"""A small in-memory stand-in for supabase-py's query builder — only what SupabaseRepo calls.

Like the real API it answers at most `max_rows` rows per request (Supabase's default is 1000), so code
that forgets to page loses rows here too. Like postgrest-py, range() adds parameters instead of replacing
them, so a query object may take only one range().
"""
from __future__ import annotations

from types import SimpleNamespace


class FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]] | None = None, max_rows: int = 1000):
        self.tables = {name: [dict(r) for r in rows] for name, rows in (tables or {}).items()}
        self.max_rows = max_rows
        self.requests = 0

    def table(self, name: str) -> "_Query":
        return _Query(self, name)


class _Query:
    def __init__(self, db: FakeSupabase, name: str):
        self.db, self.name = db, name
        self.columns: list[str] | None = None
        self.filters = []
        self.orders: list[tuple[str, bool]] = []
        self.window: tuple[int, int] | None = None
        self.action, self.payload = "select", None

    def select(self, columns: str = "*") -> "_Query":
        self.columns = None if columns == "*" else [c.strip() for c in columns.split(",")]
        return self

    def eq(self, column, value):
        self.filters.append(lambda r: r.get(column) == value)
        return self

    def in_(self, column, values):
        values = list(values)
        self.filters.append(lambda r: r.get(column) in values)
        return self

    def order(self, column, *, desc=False):
        self.orders.append((column, desc))
        return self

    def range(self, start, end):
        assert self.window is None, "range() twice on one query: postgrest-py would send offset/limit twice"
        self.window = (start, end - start + 1)
        return self

    def limit(self, n):
        assert self.window is None, "limit() after range(): postgrest-py would send limit twice"
        self.window = (0, n)
        return self

    def insert(self, rows):
        self.action, self.payload = "insert", rows if isinstance(rows, list) else [rows]
        return self

    def delete(self):
        self.action = "delete"
        return self

    def execute(self):
        self.db.requests += 1
        table = self.db.tables.setdefault(self.name, [])
        if self.action == "insert":
            for row in self.payload:
                table.append({"id": len(table) + 1, **row})
            return SimpleNamespace(data=list(self.payload))
        matched = [r for r in table if all(f(r) for f in self.filters)]
        if self.action == "delete":
            self.db.tables[self.name] = [r for r in table if r not in matched]
            return SimpleNamespace(data=matched)
        for column, desc in reversed(self.orders):  # stable sorts, last key first
            matched.sort(key=lambda r: r[column], reverse=desc)
        if self.window:
            offset, limit = self.window
            matched = matched[offset : offset + limit]
        page = matched[: self.db.max_rows]
        if self.columns:
            page = [{c: r.get(c) for c in self.columns} for r in page]
        return SimpleNamespace(data=page)
