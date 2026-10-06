from datetime import date, datetime, timedelta, timezone
from io import BytesIO

import pytest
from PIL import Image

from stockcount.config import parse_config
from stockcount.cv import CvUnavailable
from stockcount.layout import Placement
from stockcount.location import parse_location
from stockcount.repo import InMemoryRepo, Product
from stockcount.service import CountError, CountingService, SessionClosed, SlotNotFound

UTC = timezone.utc
PRODUCTS = {
    "A": Product("A", "อุระกาวาท", "ผง", "jar"),
    "B": Product("B", "อโธ", "ผง", "jar"),
    "C": Product("C", "อังมะ", "ผง", "jar"),
    "D": Product("D", "มัตถะ", "ผง", "jar"),
    "E": Product("E", "แพนดอร่าทู", "อาหารเสริม", "jar"),
    "F": Product("F", "ยาธาตุ", "ชง", "bag"),
}
FRONT = {"A": 9, "B": 9, "C": 11, "D": 0, "E": -9, "F": 12}


def place(sku, code):
    return Placement(sku, parse_location(code))


PLACEMENTS = [place("A", "R0101"), place("B", "R0101"), place("D", "R0101"), place("E", "R0301"), place("F", "L0101")]


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


class FakeCv:
    def __init__(self, bottles=0, pouches=0, fail=False):
        self.calls, self.bottles, self.pouches, self.fail = 0, bottles, pouches, fail

    def predict(self, image: bytes) -> list[dict]:
        self.calls += 1
        if self.fail:
            raise CvUnavailable("timeout")
        return [{"class": "jar", "confidence": 0.9}] * self.bottles + [{"class": "bag", "confidence": 0.9}] * self.pouches


class FakeNotifier:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def push(self, user_id, text):
        if self.fail:
            raise RuntimeError("LINE down")
        self.sent.append((user_id, text))


def jpeg(grey=150):
    buf = BytesIO()
    Image.new("RGB", (32, 32), (grey, grey, grey)).save(buf, format="JPEG")
    return buf.getvalue()


def make(cv=None, notifier=None, raw_config=None, t=datetime(2026, 10, 1, 3, 0, tzinfo=UTC)):
    repo = InMemoryRepo(PRODUCTS, PLACEMENTS, date(2026, 9, 28), FRONT)
    clock = Clock(t)
    config = parse_config({"branch": "mbk", **(raw_config or {})})
    return CountingService(config, repo, clock, cv_client=cv, notifier=notifier), repo, clock


def test_slot_shows_only_products_to_check():
    svc, _, _ = make()
    view = svc.slot("R0101")
    assert [(i.sku, i.expected, i.status) for i in view.items] == [("A", 9, "check"), ("B", 9, "check")]
    assert view.hidden_empty == 1  # มัตถะ has 0 → nothing to check
    assert not view.read_only


def test_problem_items_are_shown_too():
    svc, _, _ = make()
    assert [(i.sku, i.status) for i in svc.slot("R0301").items] == [("E", "problem")]


def test_unknown_slot():
    svc, _, _ = make()
    with pytest.raises(SlotNotFound):
        svc.slot("L0909")


def test_saving_starts_the_clock_and_reports_mismatches():
    svc, repo, clock = make()
    result = svc.save_slot("R0101", "U1", {"A": "9", "B": "7"})
    assert repo.session_for(date(2026, 10, 1)).started_at == clock.t
    assert [(m.sku, m.expected, m.counted) for m in result.mismatches] == [("B", 9, 7)]


def test_bad_input_saves_nothing():
    svc, repo, _ = make()
    with pytest.raises(CountError) as err:
        svc.save_slot("R0101", "U1", {"A": "9", "B": "-1"})
    assert set(err.value.errors) == {"B"}
    session = repo.session_for(date(2026, 10, 1))
    assert session is None or repo.counts(session.id) == []


def test_missing_field_is_an_error():
    svc, _, _ = make()
    with pytest.raises(CountError) as err:
        svc.save_slot("R0101", "U1", {"A": "9"})
    assert set(err.value.errors) == {"B"}


def test_thai_digits_are_accepted():
    svc, _, _ = make()
    result = svc.save_slot("R0101", "U1", {"A": "๙", "B": "๙"})
    assert result.mismatches == ()


def test_photo_within_tolerance_is_ok():
    svc, repo, _ = make(cv=FakeCv(bottles=17))
    result = svc.save_slot("R0101", "U1", {"A": "9", "B": "9"}, photo=jpeg())
    assert result.cv.status == "ok"
    [photo] = repo.photos(repo.session_for(date(2026, 10, 1)).id)
    assert photo.human_counts == {"jar": 18} and photo.cv_counts == {"jar": 17}


def test_photo_far_off_is_flagged():
    svc, _, _ = make(cv=FakeCv(bottles=10))
    assert svc.save_slot("R0101", "U1", {"A": "9", "B": "9"}, photo=jpeg()).cv.status == "flagged"


def test_cv_down_still_saves_the_counts():
    svc, repo, _ = make(cv=FakeCv(fail=True))
    result = svc.save_slot("R0101", "U1", {"A": "9", "B": "9"}, photo=jpeg())
    assert result.cv.status == "skipped"
    assert len(repo.counts(repo.session_for(date(2026, 10, 1)).id)) == 2


def test_cv_can_be_off_for_a_slot():
    cv = FakeCv(bottles=18)
    svc, _, _ = make(cv=cv, raw_config={"cv": {"disabled_locations": ["R0101"]}})
    assert svc.save_slot("R0101", "U1", {"A": "9", "B": "9"}, photo=jpeg()).cv.status == "skipped"
    assert cv.calls == 0


def test_dark_photo_is_flagged_but_kept():
    svc, repo, _ = make()
    result = svc.save_slot("R0101", "U1", {"A": "9", "B": "9"}, photo=jpeg(grey=15))
    assert result.too_dark
    assert len(repo.photos(repo.session_for(date(2026, 10, 1)).id)) == 1


def test_not_an_image_keeps_the_counts():
    svc, repo, _ = make()
    result = svc.save_slot("R0101", "U1", {"A": "9", "B": "9"}, photo=b"not an image")
    assert result.photo_error
    sid = repo.session_for(date(2026, 10, 1)).id
    assert len(repo.counts(sid)) == 2 and repo.photos(sid) == []


def test_submit_closes_the_day_and_pushes_a_summary():
    notifier = FakeNotifier()
    svc, repo, clock = make(notifier=notifier)
    svc.start("U1")
    svc.save_slot("R0101", "U1", {"A": "9", "B": "7"})
    clock.advance(minutes=8)
    summary = svc.submit("U1")
    assert summary.minutes == 8
    assert summary.missing_slots == ("L0101", "R0301")
    assert [(m.sku, m.counted) for m in summary.mismatches] == [("B", 7)]
    assert notifier.sent and notifier.sent[0][0] == "U1" and "8 นาที" in notifier.sent[0][1]
    with pytest.raises(SessionClosed):
        svc.save_slot("R0101", "U1", {"A": "9", "B": "9"})
    assert svc.slot("R0101").read_only


def test_push_failure_does_not_break_submit():
    svc, repo, _ = make(notifier=FakeNotifier(fail=True))
    svc.save_slot("R0101", "U1", {"A": "9", "B": "9"})
    svc.submit("U1")
    assert repo.session_for(date(2026, 10, 1)).submitted


def test_day_follows_bangkok_time():
    svc, _, _ = make(t=datetime(2026, 10, 1, 18, 30, tzinfo=UTC))  # 01:30 on 2 Oct in Bangkok
    assert svc.today() == date(2026, 10, 2)


def test_minimap_shows_progress():
    svc, _, _ = make()
    svc.save_slot("R0101", "U1", {"A": "9", "B": "7"})
    right = next(w for w in svc.minimap().walls if w.side == "R")
    cell = next(c for row in right.rows for c in row if c.code == "R0101")
    assert {i.sku: i.status for i in cell.items} == {"A": "done", "B": "diff", "D": "empty"}
    assert cell.status == "diff"


def test_last_count_is_shown_the_next_day():
    svc, _, clock = make()
    svc.save_slot("R0101", "U1", {"A": "8", "B": "9"})
    clock.advance(days=1)
    items = {i.sku: i for i in svc.slot("R0101").items}
    assert items["A"].last == (date(2026, 10, 1), 8)


def test_voice_text_fills_only_this_slot():
    svc, _, _ = make()
    assert svc.recognise("R0101", "อุระกาวาท เก้า อโธ แปด ยาธาตุ สิบ") == {"A": 9, "B": 8}


def test_weekly_report():
    svc, _, clock = make()
    svc.save_slot("R0101", "U1", {"A": "9", "B": "9"})
    clock.advance(days=1)
    svc.save_slot("R0101", "U1", {"A": "5", "B": "9"})
    report = svc.report("2026-W40")
    assert [(m.sku, m.moved) for m in report.top_movers] == [("A", 4)]


def test_walk_order_is_left_then_right_top_storey_first():
    svc, _, _ = make()
    assert svc.walk_order() == ["L0101", "R0301", "R0101"]


def test_next_slot_skips_what_is_done():
    svc, _, _ = make()
    assert svc.next_slot() == "L0101"
    svc.save_slot("L0101", "U1", {"F": "12"})
    assert svc.next_slot() == "R0301"
    svc.save_slot("R0301", "U1", {"E": "3"})
    svc.save_slot("R0101", "U1", {"A": "9", "B": "9"})
    assert svc.next_slot() is None


def test_stored_photo_is_shrunk_before_saving_and_cv():
    cv = FakeCv(bottles=18)
    svc, repo, _ = make(cv=cv)
    buf = BytesIO()
    Image.effect_noise((1600, 1200), 64).convert("RGB").save(buf, format="JPEG", quality=95)
    svc.save_slot("R0101", "U1", {"A": "9", "B": "9"}, photo=buf.getvalue())
    [stored] = repo.photo_bytes.values()
    with Image.open(BytesIO(stored)) as img:
        assert max(img.size) == 1280
    assert len(stored) < len(buf.getvalue())
