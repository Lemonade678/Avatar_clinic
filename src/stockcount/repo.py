"""Storage behind one interface: InMemoryRepo for tests and dev mode, SupabaseRepo for the pilot."""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from .cv import CvCheck
from .layout import Placement, load_layout_csv, load_packaging_csv, load_packaging_subclasses
from .location import parse_location
from .report import CountRecord, SessionInfo
from .stock_csv import load_stock_csv


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    packaging: str | None
    packaging_sub: str | None = None


@dataclass(frozen=True)
class Session:
    id: str
    count_date: date
    started_at: datetime
    ended_at: datetime | None = None

    @property
    def submitted(self) -> bool:
        return self.ended_at is not None


@dataclass(frozen=True)
class CountRow:
    location_code: str
    sku: str
    expected_qty: int
    counted_qty: int
    input_method: str = "type"


@dataclass(frozen=True)
class PhotoRecord:
    session_id: str
    location_code: str
    storage_path: str
    cv_status: str
    cv_counts: dict = field(default_factory=dict)
    human_counts: dict = field(default_factory=dict)
    brightness: float | None = None


class Repo(Protocol):
    def products(self) -> dict[str, Product]: ...
    def placements(self) -> list[Placement]: ...
    def stock(self) -> tuple[date | None, dict[str, int]]: ...
    def session_for(self, count_date: date) -> Session | None: ...
    def start_session(self, count_date: date, now: datetime, user_id: str) -> Session: ...
    def end_session(self, session_id: str, now: datetime) -> None: ...
    def save_counts(self, session_id: str, rows: list[CountRow], user_id: str, now: datetime) -> None: ...
    def counts(self, session_id: str) -> list[CountRow]: ...
    def last_counts(self, before: date) -> dict[str, tuple[date, int]]: ...
    def save_photo(self, session_id: str, location_code: str, user_id: str, content: bytes, check: CvCheck,
                   human_counts: dict[str, int], brightness: float | None, now: datetime) -> str: ...
    def photos(self, session_id: str) -> list[PhotoRecord]: ...
    def count_records(self, until: date) -> list[CountRecord]: ...
    def sessions(self) -> list[SessionInfo]: ...
    def cv_statuses(self, start: date, end: date) -> list[str]: ...


def _cv_counts(check: CvCheck) -> dict[str, int]:
    return {c.packaging: c.cv for c in check.classes}


class InMemoryRepo:
    def __init__(self, products: dict[str, Product], placements: list[Placement],
                 stock_as_of: date | None, front_qty: dict[str, int]):
        self._products = dict(products)
        self._placements = list(placements)
        self._stock_as_of = stock_as_of
        self._front = dict(front_qty)
        self._sessions: dict[date, Session] = {}
        self._counts: dict[tuple[str, str], CountRow] = {}
        self._photos: list[PhotoRecord] = []
        self.photo_bytes: dict[str, bytes] = {}

    @classmethod
    def from_files(cls, stock_csv: str | Path, layout_csv: str | Path, as_of: date) -> "InMemoryRepo":
        rows = load_stock_csv(stock_csv)
        packaging = load_packaging_csv(layout_csv)
        subclasses = load_packaging_subclasses(layout_csv)
        return cls(
            products={
                r.sku: Product(r.sku, r.name, r.category, packaging.get(r.sku), subclasses.get(r.sku)) for r in rows
            },
            placements=load_layout_csv(layout_csv),
            stock_as_of=as_of,
            front_qty={r.sku: r.front_qty for r in rows},
        )

    def products(self) -> dict[str, Product]:
        return dict(self._products)

    def placements(self) -> list[Placement]:
        return list(self._placements)

    def stock(self) -> tuple[date | None, dict[str, int]]:
        return self._stock_as_of, dict(self._front)

    def session_for(self, count_date: date) -> Session | None:
        return self._sessions.get(count_date)

    def start_session(self, count_date: date, now: datetime, user_id: str) -> Session:
        if count_date not in self._sessions:
            self._sessions[count_date] = Session(f"s-{count_date.isoformat()}", count_date, now)
        return self._sessions[count_date]

    def end_session(self, session_id: str, now: datetime) -> None:
        for day, s in self._sessions.items():
            if s.id == session_id and s.ended_at is None:
                self._sessions[day] = replace(s, ended_at=now)

    def save_counts(self, session_id: str, rows: list[CountRow], user_id: str, now: datetime) -> None:
        for row in rows:
            self._counts[(session_id, row.sku)] = row

    def counts(self, session_id: str) -> list[CountRow]:
        return [row for (sid, _), row in self._counts.items() if sid == session_id]

    def _day_of(self, session_id: str) -> date:
        return next(day for day, s in self._sessions.items() if s.id == session_id)

    def last_counts(self, before: date) -> dict[str, tuple[date, int]]:
        latest: dict[str, tuple[date, int]] = {}
        for (sid, sku), row in self._counts.items():
            day = self._day_of(sid)
            if day < before and (sku not in latest or latest[sku][0] < day):
                latest[sku] = (day, row.counted_qty)
        return latest

    def save_photo(self, session_id: str, location_code: str, user_id: str, content: bytes, check: CvCheck,
                   human_counts: dict[str, int], brightness: float | None, now: datetime) -> str:
        path = f"{session_id}/{location_code}/{now:%H%M%S}-{len(self._photos) + 1}.jpg"
        self.photo_bytes[path] = content
        self._photos.append(
            PhotoRecord(session_id, location_code, path, check.status, _cv_counts(check), dict(human_counts), brightness)
        )
        return path

    def photos(self, session_id: str) -> list[PhotoRecord]:
        return [p for p in self._photos if p.session_id == session_id]

    def count_records(self, until: date) -> list[CountRecord]:
        return [
            CountRecord(self._day_of(sid), row.sku, row.counted_qty, row.expected_qty)
            for (sid, _), row in self._counts.items()
            if self._day_of(sid) <= until
        ]

    def sessions(self) -> list[SessionInfo]:
        return [SessionInfo(s.count_date, s.started_at, s.ended_at) for s in sorted(self._sessions.values(), key=lambda s: s.count_date)]

    def cv_statuses(self, start: date, end: date) -> list[str]:
        return [p.cv_status for p in self._photos if start <= self._day_of(p.session_id) <= end]


class SupabaseRepo:
    """Same interface on Supabase. Verified against a real project by scripts/smoke_supabase.py."""

    BUCKET = "shelf-photos"

    def __init__(self, client):
        self.db = client

    @classmethod
    def from_env(cls) -> "SupabaseRepo":
        from supabase import create_client

        return cls(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]))

    def _rows(self, query) -> list[dict]:
        return query.execute().data or []

    def products(self) -> dict[str, Product]:
        rows = self._rows(self.db.table("products").select("sku,name,category,packaging,packaging_sub"))
        return {
            r["sku"]: Product(r["sku"], r["name"], r["category"], r["packaging"], r.get("packaging_sub")) for r in rows
        }

    def placements(self) -> list[Placement]:
        locations = {r["code"]: r for r in self._rows(self.db.table("locations").select("code,shelf"))}
        links = self._rows(self.db.table("product_locations").select("sku,location_code"))
        return [
            Placement(l["sku"], parse_location(l["location_code"], locations[l["location_code"]]["shelf"]))
            for l in links
        ]

    def stock(self) -> tuple[date | None, dict[str, int]]:
        rows = self._rows(self.db.table("stock_snapshots").select("sku,front_qty,as_of").order("as_of", desc=True))
        front: dict[str, int] = {}
        for r in rows:
            front.setdefault(r["sku"], r["front_qty"])
        return (date.fromisoformat(rows[0]["as_of"]) if rows else None), front

    @staticmethod
    def _session(row: dict) -> Session:
        return Session(
            row["id"],
            date.fromisoformat(row["count_date"]),
            datetime.fromisoformat(row["started_at"]),
            datetime.fromisoformat(row["ended_at"]) if row.get("ended_at") else None,
        )

    def session_for(self, count_date: date) -> Session | None:
        rows = self._rows(self.db.table("count_sessions").select("*").eq("count_date", count_date.isoformat()))
        return self._session(rows[0]) if rows else None

    def start_session(self, count_date: date, now: datetime, user_id: str) -> Session:
        self.db.table("count_sessions").upsert(
            {"count_date": count_date.isoformat(), "started_at": now.isoformat(), "line_user_id": user_id},
            on_conflict="count_date",
            ignore_duplicates=True,
        ).execute()
        return self.session_for(count_date)

    def end_session(self, session_id: str, now: datetime) -> None:
        self.db.table("count_sessions").update({"ended_at": now.isoformat()}).eq("id", session_id).is_(
            "ended_at", "null"
        ).execute()

    def save_counts(self, session_id: str, rows: list[CountRow], user_id: str, now: datetime) -> None:
        # one upsert statement = the whole slot or nothing
        payload = [
            {
                "session_id": session_id,
                "location_code": r.location_code,
                "sku": r.sku,
                "expected_qty": r.expected_qty,
                "counted_qty": r.counted_qty,
                "input_method": r.input_method,
                "line_user_id": user_id,
                "updated_at": now.isoformat(),
            }
            for r in rows
        ]
        self.db.table("counts").upsert(payload, on_conflict="session_id,sku").execute()

    def counts(self, session_id: str) -> list[CountRow]:
        rows = self._rows(
            self.db.table("counts")
            .select("location_code,sku,expected_qty,counted_qty,input_method")
            .eq("session_id", session_id)
        )
        return [CountRow(r["location_code"], r["sku"], r["expected_qty"], r["counted_qty"], r["input_method"]) for r in rows]

    def _session_days(self) -> dict[str, date]:
        rows = self._rows(self.db.table("count_sessions").select("id,count_date"))
        return {r["id"]: date.fromisoformat(r["count_date"]) for r in rows}

    def _all_counts(self, session_ids: list[str]) -> list[dict]:
        if not session_ids:
            return []
        return self._rows(
            self.db.table("counts").select("session_id,sku,expected_qty,counted_qty").in_("session_id", session_ids)
        )

    def last_counts(self, before: date) -> dict[str, tuple[date, int]]:
        days = {sid: d for sid, d in self._session_days().items() if d < before}
        latest: dict[str, tuple[date, int]] = {}
        for r in self._all_counts(list(days)):
            day = days[r["session_id"]]
            if r["sku"] not in latest or latest[r["sku"]][0] < day:
                latest[r["sku"]] = (day, r["counted_qty"])
        return latest

    def save_photo(self, session_id: str, location_code: str, user_id: str, content: bytes, check: CvCheck,
                   human_counts: dict[str, int], brightness: float | None, now: datetime) -> str:
        path = f"{session_id}/{location_code}/{now:%H%M%S}-{uuid.uuid4().hex[:8]}.jpg"
        self.db.storage.from_(self.BUCKET).upload(path, content, {"content-type": "image/jpeg"})
        self.db.table("shelf_photos").insert(
            {
                "session_id": session_id,
                "location_code": location_code,
                "storage_path": path,
                "line_user_id": user_id,
                "cv_status": check.status,
                "cv_counts": _cv_counts(check),
                "human_counts": human_counts,
                "brightness": brightness,
            }
        ).execute()
        return path

    def photos(self, session_id: str) -> list[PhotoRecord]:
        rows = self._rows(
            self.db.table("shelf_photos")
            .select("session_id,location_code,storage_path,cv_status,cv_counts,human_counts,brightness")
            .eq("session_id", session_id)
        )
        return [
            PhotoRecord(r["session_id"], r["location_code"], r["storage_path"], r["cv_status"],
                        r["cv_counts"] or {}, r["human_counts"] or {}, r["brightness"])
            for r in rows
        ]

    def count_records(self, until: date) -> list[CountRecord]:
        days = {sid: d for sid, d in self._session_days().items() if d <= until}
        return [
            CountRecord(days[r["session_id"]], r["sku"], r["counted_qty"], r["expected_qty"])
            for r in self._all_counts(list(days))
        ]

    def sessions(self) -> list[SessionInfo]:
        rows = self._rows(self.db.table("count_sessions").select("*").order("count_date"))
        return [SessionInfo(s.count_date, s.started_at, s.ended_at) for s in map(self._session, rows)]

    def cv_statuses(self, start: date, end: date) -> list[str]:
        ids = [sid for sid, d in self._session_days().items() if start <= d <= end]
        if not ids:
            return []
        rows = self._rows(self.db.table("shelf_photos").select("cv_status").in_("session_id", ids))
        return [r["cv_status"] for r in rows]
