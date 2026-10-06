"""Exercise SupabaseRepo against the real project, then clean up.

Uses the date 2000-01-01, product SMOKE-1 and slot R9999 so real data is never touched.
Usage: .venv/Scripts/python scripts/smoke_supabase.py
"""
from datetime import date, datetime, timezone

from dotenv import load_dotenv

from stockcount.cv import CvCheck
from stockcount.repo import CountRow, SupabaseRepo

DAY = date(2000, 1, 1)


def main() -> None:
    load_dotenv()
    repo = SupabaseRepo.from_env()
    db = repo.db
    now = datetime.now(timezone.utc)
    db.table("products").upsert({"sku": "SMOKE-1", "name": "smoke", "category": "test", "packaging": "plastic_bottle"}).execute()
    db.table("locations").upsert({"code": "R9999", "side": "R", "storey": 99, "position": 99}).execute()
    db.table("product_locations").upsert({"sku": "SMOKE-1", "location_code": "R9999"}).execute()
    db.table("stock_snapshots").upsert({"sku": "SMOKE-1", "back_qty": 0, "front_qty": 4, "as_of": DAY.isoformat()}).execute()
    path = None
    try:
        assert repo.products()["SMOKE-1"].packaging == "plastic_bottle"
        assert any(p.sku == "SMOKE-1" and p.location.code == "R9999" for p in repo.placements())
        s = repo.start_session(DAY, now, "U-smoke")
        assert repo.start_session(DAY, now, "U-smoke").id == s.id, "second start must reuse the session"
        repo.save_counts(s.id, [CountRow("R9999", "SMOKE-1", 4, 3)], "U-smoke", now)
        repo.save_counts(s.id, [CountRow("R9999", "SMOKE-1", 4, 4, "voice")], "U-smoke", now)
        assert repo.counts(s.id) == [CountRow("R9999", "SMOKE-1", 4, 4, "voice")], "recount must overwrite"
        path = repo.save_photo(s.id, "R9999", "U-smoke", b"\xff\xd8smoke", CvCheck("skipped"), {"plastic_bottle": 4}, 99.0, now)
        assert repo.photos(s.id)[0].human_counts == {"plastic_bottle": 4}
        # correcting a product code must cascade into counts and layout
        db.table("products").update({"sku": "SMOKE-2"}).eq("sku", "SMOKE-1").execute()
        assert repo.counts(s.id)[0].sku == "SMOKE-2", "on update cascade missing"
        repo.end_session(s.id, now)
        assert repo.session_for(DAY).submitted
        print("SMOKE OK")
    finally:
        if path:
            db.storage.from_(repo.BUCKET).remove([path])
        db.table("count_sessions").delete().eq("count_date", DAY.isoformat()).execute()
        db.table("stock_snapshots").delete().in_("sku", ["SMOKE-1", "SMOKE-2"]).execute()
        db.table("product_locations").delete().in_("sku", ["SMOKE-1", "SMOKE-2"]).execute()
        db.table("locations").delete().eq("code", "R9999").execute()
        db.table("products").delete().in_("sku", ["SMOKE-1", "SMOKE-2"]).execute()


if __name__ == "__main__":
    main()
