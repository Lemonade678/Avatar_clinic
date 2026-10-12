"""Weekly stock report: top 1–2–3 fast movers + summary numbers. Pure: no I/O.

"Moved" is an estimate: every decrease between two counts is counted, increases are
treated as restocks. Back-store stock also moves to the front store, so read it as a trend.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class CountRecord:
    count_date: date
    sku: str
    counted: int
    expected: int


@dataclass(frozen=True)
class SessionInfo:
    count_date: date
    started_at: datetime
    ended_at: datetime | None


@dataclass(frozen=True)
class Mover:
    sku: str
    name: str
    moved: int


@dataclass(frozen=True)
class Mismatch:
    sku: str
    name: str
    times: int


@dataclass(frozen=True)
class WeeklyReport:
    week: str
    start: date
    end: date
    top_movers: tuple[Mover, ...]
    sessions: int
    avg_minutes: float | None
    mismatches: tuple[Mismatch, ...]
    cv_checked: int
    cv_ok: int
    latest: dict[str, int] = field(default_factory=dict)


def week_of(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def week_bounds(week: str) -> tuple[date, date]:
    year, number = week.split("-W")
    start = date.fromisocalendar(int(year), int(number), 1)
    return start, start + timedelta(days=6)


def fast_movers(records: list[CountRecord], names: dict[str, str], top: int = 3, since: date | None = None) -> list[Mover]:
    by_sku: dict[str, list[CountRecord]] = defaultdict(list)
    for r in sorted(records, key=lambda r: r.count_date):
        by_sku[r.sku].append(r)
    movers = []
    for sku, recs in by_sku.items():
        moved = sum(
            max(0, before.counted - after.counted)
            for before, after in zip(recs, recs[1:])
            if since is None or after.count_date >= since
        )
        if moved > 0:
            movers.append(Mover(sku, names.get(sku, sku), moved))
    movers.sort(key=lambda m: (-m.moved, m.name))
    return movers[:top]


def build_weekly_report(
    week: str,
    records: list[CountRecord],
    sessions: list[SessionInfo],
    cv_statuses: list[str],
    names: dict[str, str],
) -> WeeklyReport:
    start, end = week_bounds(week)
    in_week = sorted((r for r in records if start <= r.count_date <= end), key=lambda r: r.count_date)
    # counts before the week are kept as the baseline for the first decrease of the week
    top = fast_movers([r for r in records if r.count_date <= end], names, since=start)

    durations = [
        (s.ended_at - s.started_at).total_seconds() / 60
        for s in sessions
        if start <= s.count_date <= end and s.ended_at is not None
    ]
    off = Counter(r.sku for r in in_week if r.counted != r.expected)
    return WeeklyReport(
        week=week,
        start=start,
        end=end,
        top_movers=tuple(top),
        sessions=sum(1 for s in sessions if start <= s.count_date <= end),
        avg_minutes=round(sum(durations) / len(durations), 1) if durations else None,
        mismatches=tuple(Mismatch(sku, names.get(sku, sku), n) for sku, n in off.most_common(5)),
        cv_checked=sum(1 for s in cv_statuses if s != "skipped"),
        cv_ok=sum(1 for s in cv_statuses if s == "ok"),
        latest={r.sku: r.counted for r in in_week},
    )
