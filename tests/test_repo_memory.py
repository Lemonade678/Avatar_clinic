from datetime import date, datetime, timezone
from pathlib import Path

from stockcount.cv import CvCheck
from stockcount.repo import CountRow, InMemoryRepo, Product

ROOT = Path(__file__).parents[1]
UTC = timezone.utc
T0 = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
D1, D2 = date(2026, 10, 1), date(2026, 10, 2)


def repo():
    return InMemoryRepo(
        products={"A": Product("A", "อุระกาวาท", "ผง", "bottle"), "B": Product("B", "อโธ", "ผง", "bottle")},
        placements=[],
        stock_as_of=date(2026, 9, 28),
        front_qty={"A": 9, "B": 9},
    )


def test_start_session_is_idempotent_per_day():
    r = repo()
    s1 = r.start_session(D1, T0, "U1")
    s2 = r.start_session(D1, T0.replace(hour=4), "U1")
    assert s1 == s2 and s1.started_at == T0 and not s1.submitted
    assert r.session_for(D2) is None


def test_end_session_only_once():
    r = repo()
    s = r.start_session(D1, T0, "U1")
    r.end_session(s.id, T0.replace(minute=8))
    r.end_session(s.id, T0.replace(minute=30))  # a second submit does not move the end time
    assert r.session_for(D1).ended_at == T0.replace(minute=8)


def test_save_counts_overwrites_per_sku():
    r = repo()
    s = r.start_session(D1, T0, "U1")
    r.save_counts(s.id, [CountRow("R0101", "A", 9, 7)], "U1", T0)
    r.save_counts(s.id, [CountRow("R0101", "A", 9, 9, "voice")], "U1", T0)
    assert r.counts(s.id) == [CountRow("R0101", "A", 9, 9, "voice")]


def test_last_counts_come_from_earlier_days_only():
    r = repo()
    s1 = r.start_session(D1, T0, "U1")
    r.save_counts(s1.id, [CountRow("R0101", "A", 9, 8)], "U1", T0)
    s2 = r.start_session(D2, T0, "U1")
    r.save_counts(s2.id, [CountRow("R0101", "A", 9, 6)], "U1", T0)
    assert r.last_counts(before=D2) == {"A": (D1, 8)}


def test_photos_and_report_inputs():
    r = repo()
    s = r.start_session(D1, T0, "U1")
    r.save_counts(s.id, [CountRow("R0101", "A", 9, 8)], "U1", T0)
    path = r.save_photo(s.id, "R0101", "U1", b"jpg", CvCheck("ok"), {"bottle": 8}, 120.0, T0)
    assert path.startswith(f"{s.id}/R0101/")
    [photo] = r.photos(s.id)
    assert (photo.cv_status, photo.human_counts, photo.brightness) == ("ok", {"bottle": 8}, 120.0)
    assert [(x.sku, x.counted, x.expected) for x in r.count_records(until=D1)] == [("A", 8, 9)]
    assert [x.count_date for x in r.sessions()] == [D1]
    assert r.cv_statuses(D1, D2) == ["ok"]


def test_from_files_loads_the_repo_data():
    r = InMemoryRepo.from_files(ROOT / "data" / "stock_2026-09-28.csv", ROOT / "data" / "layout_mbk.csv", date(2026, 9, 28))
    assert len(r.products()) == 105
    assert r.products()["HB0001"].packaging == "jar"
    assert len(r.placements()) == 27
    as_of, front = r.stock()
    assert as_of == date(2026, 9, 28) and front["NA0032"] == -9
