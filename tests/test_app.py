from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from stockcount.app import build_default_app, create_app
from stockcount.auth import AuthError
from stockcount.config import parse_config
from stockcount.repo import InMemoryRepo
from stockcount.service import CountingService

ROOT = Path(__file__).parents[1]
UTC = timezone.utc
TODAY = date(2026, 10, 1)


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)

    def __call__(self):
        return self.t


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def push(self, user_id, text):
        self.sent.append((user_id, text))


class FakeVerifier:
    def verify(self, token):
        if token == "good":
            return "U-nutt"
        if token == "stranger":
            return "U-other"
        raise AuthError("bad token")


def make_service(notifier=None, allow=()):
    repo = InMemoryRepo.from_files(ROOT / "data" / "stock_2026-09-28.csv", ROOT / "data" / "layout_mbk.csv", date(2026, 9, 28))
    config = parse_config({"branch": "mbk", "allowed_line_user_ids": list(allow)})
    return CountingService(config, repo, Clock(), notifier=notifier)


def dev_client(notifier=None, **kw):
    svc = make_service(notifier=notifier)
    app = create_app(svc, session_secret="test-secret", dev_user_id="U-dev", https_only=False, **kw)
    return TestClient(app), svc


def form_for(svc, code, override=None):
    data = {f"qty_{i.sku}": str(i.expected) for i in svc.slot(code).items}
    data.update(override or {})
    return data


def jpeg():
    buf = BytesIO()
    Image.new("RGB", (40, 30), (150, 150, 150)).save(buf, format="JPEG")
    return buf.getvalue()


def test_health_needs_no_login():
    client, _ = dev_client()
    assert client.get("/health").json() == {"ok": True}


def test_pages_ask_for_line_login_outside_dev_mode():
    app = create_app(make_service(), session_secret="s", verifier=FakeVerifier(), https_only=False)
    r = TestClient(app).get("/map")
    assert r.status_code == 401 and "เข้าสู่ระบบ" in r.text


def test_liff_login_then_pages_open():
    client = TestClient(create_app(make_service(), session_secret="s", verifier=FakeVerifier(), https_only=False))
    assert client.post("/auth/liff", json={"id_token": "good"}).status_code == 200
    assert client.get("/map").status_code == 200


def test_fake_token_is_refused():
    client = TestClient(create_app(make_service(), session_secret="s", verifier=FakeVerifier(), https_only=False))
    assert client.post("/auth/liff", json={"id_token": "forged"}).status_code == 401
    assert client.get("/map").status_code == 401


def test_user_outside_allowlist_is_refused():
    svc = make_service(allow=["U-nutt"])
    client = TestClient(create_app(svc, session_secret="s", verifier=FakeVerifier(), https_only=False))
    assert client.post("/auth/liff", json={"id_token": "stranger"}).status_code == 403


def test_map_page_is_utf8_with_links_to_slots():
    client, _ = dev_client()
    r = client.get("/map")
    assert r.status_code == 200
    assert "charset=utf-8" in r.headers["content-type"]
    assert 'href="/loc/L0301"' in r.text and "อุระกาวาท" in r.text
    assert "เริ่มนับ" in r.text


def test_qr_link_redirects_to_the_slot():
    client, _ = dev_client()
    r = client.get("/?loc=l0301", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/loc/L0301"


def test_slot_page_prefills_the_system_value():
    client, _ = dev_client()
    r = client.get("/loc/R0101")
    assert 'name="qty_HB0001"' in r.text and 'value="9"' in r.text


def test_unknown_slot_is_404():
    client, _ = dev_client()
    assert client.get("/loc/L0909").status_code == 404


def test_save_moves_to_the_next_slot_and_shows_the_result():
    client, svc = dev_client()
    r = client.post("/loc/L0301", data=form_for(svc, "L0301"), follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/loc/L0201"
    assert "บันทึกช่อง L0301 แล้ว" in client.get("/loc/L0201").text
    assert svc.repo.session_for(TODAY) is not None  # the first save started the clock


def test_bad_value_shows_the_form_again():
    client, svc = dev_client()
    r = client.post("/loc/R0101", data=form_for(svc, "R0101", {"qty_HB0001": "abc"}))
    assert r.status_code == 422 and "ต้องเป็นจำนวนเต็ม" in r.text and 'value="abc"' in r.text


def test_photo_is_stored_with_the_counts():
    client, svc = dev_client()
    r = client.post("/loc/R0101", data=form_for(svc, "R0101"), files={"photo": ("shelf.jpg", jpeg(), "image/jpeg")},
                    follow_redirects=False)
    assert r.status_code == 303
    assert len(svc.repo.photos(svc.repo.session_for(TODAY).id)) == 1


def test_empty_photo_field_means_no_photo():
    client, svc = dev_client()
    client.post("/loc/R0101", data=form_for(svc, "R0101"), files={"photo": ("", b"", "application/octet-stream")})
    assert svc.repo.photos(svc.repo.session_for(TODAY).id) == []


def test_huge_photo_is_refused():
    client, svc = dev_client(max_photo_bytes=100)
    r = client.post("/loc/R0101", data=form_for(svc, "R0101"), files={"photo": ("shelf.jpg", jpeg(), "image/jpeg")})
    assert r.status_code == 413


def test_voice_text_becomes_counts():
    client, _ = dev_client()
    r = client.post("/loc/R0101/voice", json={"text": "อุระกาวาท เก้า อังมะ สิบเอ็ด"})
    assert r.json() == {"ok": True, "counts": {"HB0001": 9, "HB0011": 11}}


def test_full_round_start_save_submit():
    notifier = FakeNotifier()
    client, svc = dev_client(notifier=notifier)
    assert client.post("/session/start", follow_redirects=False).headers["location"] == "/map"
    client.post("/loc/R0101", data=form_for(svc, "R0101", {"qty_HB0001": "7"}))
    r = client.post("/session/submit", follow_redirects=False)
    assert r.headers["location"] == "/summary"
    summary = client.get("/summary").text
    assert "อุระกาวาท" in summary and "-2" in summary
    assert notifier.sent and notifier.sent[0][0] == "U-dev"
    assert client.post("/loc/R0101", data=form_for(svc, "R0101")).status_code == 409


def test_scanner_page_and_vendored_jsqr():
    client, _ = dev_client()
    assert "/static/vendor/jsQR.js" in client.get("/scan").text
    assert client.get("/static/vendor/jsQR.js").status_code == 200


def test_report_page():
    client, _ = dev_client()
    assert "ของไหลออกเร็ว" in client.get("/report?week=2026-W40").text
    assert client.get("/report?week=garbage").status_code == 404


@pytest.fixture
def no_dotenv(monkeypatch):
    # a real .env on ณัฑฒ์'s machine must not leak into these tests
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)


def test_production_needs_a_session_secret(monkeypatch, no_dotenv):
    monkeypatch.chdir(ROOT)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        build_default_app()


def test_dev_mode_builds_from_the_csv_files(monkeypatch, no_dotenv):
    monkeypatch.chdir(ROOT)
    for var in ("SESSION_SECRET", "SUPABASE_URL", "ROBOFLOW_API_KEY", "LINE_CHANNEL_ACCESS_TOKEN", "LINE_LIFF_CHANNEL_ID"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("DEV_USER_ID", "U-dev")
    client = TestClient(build_default_app())
    assert client.get("/map").status_code == 200
