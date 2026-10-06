from datetime import date, datetime, timezone

from fake_supabase import FakeSupabase

from stockcount.lots import ManualLot, Receipt
from stockcount.repo import SupabaseRepo

UTC = timezone.utc
D1 = date(2026, 10, 1)


def session(sid, day):
    return {"id": sid, "count_date": day.isoformat(), "started_at": "2026-10-01T03:00:00+00:00", "ended_at": None}


def test_count_records_read_past_the_1000_row_cap():
    # a month of counting is ~1,800 rows; one request would silently stop at 1,000 and skew the reports
    counts = [
        {"session_id": "s1", "sku": f"P{i:04d}", "location_code": "L0101", "expected_qty": 1, "counted_qty": 1}
        for i in range(2500)
    ]
    repo = SupabaseRepo(FakeSupabase({"count_sessions": [session("s1", D1)], "counts": counts}))
    assert len(repo.count_records(until=D1)) == 2500
    assert len(repo.last_counts(before=date(2026, 10, 2))) == 2500


def test_on_hand_is_back_plus_front_of_the_latest_snapshot():
    snapshots = [
        {"sku": "A", "back_qty": 10, "front_qty": 9, "as_of": "2026-09-28"},
        {"sku": "A", "back_qty": 1, "front_qty": 1, "as_of": "2026-09-01"},
        {"sku": "B", "back_qty": 30, "front_qty": -9, "as_of": "2026-09-28"},
        {"sku": "C", "back_qty": 0, "front_qty": -9, "as_of": "2026-09-28"},
    ]
    repo = SupabaseRepo(FakeSupabase({"stock_snapshots": snapshots}))
    assert repo.on_hand() == {"A": 19, "B": 21, "C": 0}  # a negative system record means nothing on hand


def test_typed_lot_dates_round_trip():
    db = FakeSupabase()
    repo = SupabaseRepo(db)
    now = datetime(2026, 10, 6, 5, 0, tzinfo=UTC)
    repo.add_manual_lot("HB0001", date(2026, 6, 17), "U1", now)
    assert db.tables["lot_dates"][0]["source"] == "manual"
    assert repo.manual_lots() == [ManualLot("HB0001", date(2026, 6, 17), now)]
    assert repo.receipts() == []


def test_receipts_read_past_the_1000_row_cap():
    rows = [
        {"id": i + 1, "sku": f"P{i % 105:04d}", "lot_date": "2026-06-17", "source": "receipt", "qty": 2,
         "recorded_at": "2026-10-06T05:00:00+00:00"}
        for i in range(2300)
    ]
    repo = SupabaseRepo(FakeSupabase({"lot_dates": rows}))
    receipts = repo.receipts()
    assert len(receipts) == 2300 and receipts[0] == Receipt("P0000", date(2026, 6, 17), 2)


def test_replacing_receipts_keeps_typed_dates():
    db = FakeSupabase({"lot_dates": [
        {"id": 1, "sku": "A", "lot_date": "2026-01-01", "source": "manual", "qty": None,
         "recorded_at": "2026-10-01T03:00:00+00:00"},
        {"id": 2, "sku": "A", "lot_date": "2025-01-01", "source": "receipt", "qty": 3,
         "recorded_at": "2026-10-01T03:00:00+00:00"},
    ]})
    repo = SupabaseRepo(db)
    repo.replace_receipts([Receipt("A", date(2026, 6, 17), 4)])
    assert repo.receipts() == [Receipt("A", date(2026, 6, 17), 4)]
    assert [m.lot_date for m in repo.manual_lots()] == [date(2026, 1, 1)]


def test_replacing_receipts_inserts_in_batches():
    db = FakeSupabase()
    SupabaseRepo(db).replace_receipts([Receipt(f"P{i:04d}", date(2026, 6, 17), 1) for i in range(1200)])
    assert len(db.tables["lot_dates"]) == 1200
    assert db.requests == 1 + 3  # one delete, then batches of 500
