from datetime import date, datetime, timezone

from stockcount.report import CountRecord, SessionInfo, build_weekly_report, fast_movers, week_bounds, week_of

UTC = timezone.utc
NAMES = {"A": "อุระกาวาท", "B": "อโธ", "C": "อังมะ", "D": "KOVIA"}


def rec(day, sku, counted, expected=None):
    return CountRecord(date(2026, 10, day), sku, counted, counted if expected is None else expected)


def test_week_helpers():
    assert week_of(date(2026, 9, 30)) == "2026-W40"
    assert week_bounds("2026-W40") == (date(2026, 9, 28), date(2026, 10, 4))


def test_fast_movers_add_up_decreases_and_ignore_restocks():
    records = [
        rec(5, "A", 10), rec(6, "A", 7), rec(7, "A", 12), rec(8, "A", 9),  # -3, +5 restock, -3 → 6
        rec(5, "B", 5), rec(8, "B", 1),  # -4
        rec(5, "C", 3), rec(8, "C", 3),  # no movement → not listed
    ]
    assert [(m.sku, m.moved) for m in fast_movers(records, NAMES)] == [("A", 6), ("B", 4)]


def test_fast_movers_keeps_top_three():
    records = [rec(5, s, 10) for s in "ABCD"] + [rec(6, "A", 9), rec(6, "B", 5), rec(6, "C", 7), rec(6, "D", 1)]
    assert [m.sku for m in fast_movers(records, NAMES)] == ["D", "B", "C"]


def test_weekly_report_counts_only_the_week_but_uses_the_count_before_it_as_baseline():
    records = [
        rec(2, "A", 20),  # last week: baseline only
        rec(6, "A", 14, expected=15),
        rec(7, "B", 3, expected=3),
    ]
    sessions = [
        SessionInfo(date(2026, 10, 6), datetime(2026, 10, 6, 3, 0, tzinfo=UTC), datetime(2026, 10, 6, 3, 8, tzinfo=UTC)),
        SessionInfo(date(2026, 10, 7), datetime(2026, 10, 7, 3, 0, tzinfo=UTC), datetime(2026, 10, 7, 3, 12, tzinfo=UTC)),
    ]
    report = build_weekly_report("2026-W41", records, sessions, ["ok", "flagged", "ok", "skipped"], NAMES)
    assert (report.start, report.end) == (date(2026, 10, 5), date(2026, 10, 11))
    assert [(m.sku, m.moved) for m in report.top_movers] == [("A", 6)]
    assert report.sessions == 2
    assert report.avg_minutes == 10
    assert [(m.sku, m.times) for m in report.mismatches] == [("A", 1)]
    assert (report.cv_checked, report.cv_ok) == (3, 2)
    assert report.latest == {"A": 14, "B": 3}


def test_empty_week_is_fine():
    report = build_weekly_report("2026-W41", [], [], [], NAMES)
    assert report.top_movers == () and report.avg_minutes is None and report.cv_checked == 0
