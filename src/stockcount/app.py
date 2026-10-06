"""The web app ณัฑฒ์ taps inside LINE: minimap, slot pages, QR scanner, summary, weekly report."""
from __future__ import annotations

import logging
import os
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import messages
from .auth import AuthError
from .location import LocationError, parse_location
from .render import render_page
from .report import week_bounds, week_of
from .service import CountError, CountingService, SessionClosed, SlotNotFound

STATIC_DIR = Path(__file__).parent / "static"
PACKAGING_TH = {
    "paper_bag": "ถุงยากระดาษ", "plastic_bag": "ถุงยาพลาสติก", "plastic_bottle": "ขวดยาพลาสติก",
    "box": "กล่อง", "tote_bag": "ถุงผ้า (tote bag)", "tin": "กระป๋องยาดม",
}

log = logging.getLogger(__name__)


def create_app(
    service: CountingService,
    *,
    session_secret: str,
    verifier=None,
    dev_user_id: str | None = None,
    liff_id: str = "",
    max_photo_bytes: int = 8_000_000,
    https_only: bool = True,
) -> FastAPI:
    config = service.config
    app = FastAPI(title="stock-count", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        same_site="lax",  # a form on another site cannot post with ณัฑฒ์'s cookie
        https_only=https_only,
        max_age=12 * 60 * 60,
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def page(name: str, status: int = 200, **ctx) -> HTMLResponse:
        html = render_page(
            name,
            branch_label=config.branch.upper(),
            camera_default=config.camera_default,
            packaging_th=PACKAGING_TH,
            minutes_text=messages.minutes_text,
            **ctx,
        )
        return HTMLResponse(html, status_code=status)

    def error(status: int, title: str, detail: str = "") -> HTMLResponse:
        return page("error.html", status=status, title=title, detail=detail, nav="")

    def current_user(request: Request) -> str | Response:
        user = dev_user_id or request.session.get("user")
        if not user:
            return page("login.html", status=401, liff_id=liff_id, next=str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""), nav="")
        if not config.is_allowed(user):
            log.warning("blocked user outside the allowlist: %s", user)
            return error(403, "ไม่มีสิทธิ์ใช้ระบบนี้", "ขอให้เจ้าของระบบเพิ่ม LINE user ID ของคุณ")
        return user

    def take_flash(request: Request) -> dict | None:
        return request.session.pop("flash", None)

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.post("/auth/liff")
    async def auth_liff(request: Request):
        if verifier is None:
            return JSONResponse({"ok": False, "error": "LIFF is not configured"}, status_code=503)
        body = await request.json()
        try:
            user = await run_in_threadpool(verifier.verify, str(body.get("id_token", "")))
        except AuthError as e:
            log.warning("LIFF login failed: %s", e)
            return JSONResponse({"ok": False}, status_code=401)
        if not config.is_allowed(user):
            return JSONResponse({"ok": False}, status_code=403)
        request.session["user"] = user
        return {"ok": True}

    @app.get("/")
    def home(request: Request, loc: str | None = None):
        # a QR opened through LIFF arrives here as /?loc=L0301
        if loc:
            try:
                return RedirectResponse(f"/loc/{parse_location(loc).code}", status_code=303)
            except LocationError:
                return error(404, f"ไม่พบช่อง {loc}")
        return RedirectResponse("/map", status_code=303)

    @app.get("/map")
    def map_page(request: Request):
        user = current_user(request)
        if isinstance(user, Response):
            return user
        minimap = service.minimap()
        as_of, _ = service.repo.stock()
        return page(
            "map.html",
            nav="map",
            m=minimap,
            left=[w for w in minimap.walls if w.side == "L"],
            right=[w for w in minimap.walls if w.side == "R"],
            session=service.repo.session_for(service.today()),
            next_slot=service.next_slot(),
            today=service.today().strftime("%d/%m/%Y"),
            as_of=as_of.strftime("%d/%m/%Y") if as_of else "—",
            flash=take_flash(request),
        )

    @app.post("/session/start")
    def session_start(request: Request):
        user = current_user(request)
        if isinstance(user, Response):
            return user
        service.start(user)
        return RedirectResponse("/map", status_code=303)

    @app.post("/session/submit")
    def session_submit(request: Request):
        user = current_user(request)
        if isinstance(user, Response):
            return user
        service.submit(user)
        return RedirectResponse("/summary", status_code=303)

    @app.get("/summary")
    def summary_page(request: Request):
        user = current_user(request)
        if isinstance(user, Response):
            return user
        return page("summary.html", nav="map", s=service.summary())

    def slot_response(request: Request, code: str, status: int = 200, errors=None, values=None) -> Response:
        try:
            view = service.slot(code)
        except SlotNotFound:
            return error(404, f"ไม่พบช่อง {code.upper()}", "ลองสแกนใหม่ หรือแตะช่องบนแผนผัง")
        return page(
            "slot.html", status=status, nav="map", view=view, errors=errors or {}, values=values or {},
            flash=take_flash(request),
        )

    @app.get("/loc/{code}")
    def slot_page(request: Request, code: str):
        user = current_user(request)
        if isinstance(user, Response):
            return user
        return slot_response(request, code)

    @app.post("/loc/{code}")
    async def slot_save(request: Request, code: str):
        user = current_user(request)
        if isinstance(user, Response):
            return user
        form = await request.form()
        raw = {k[4:]: str(v) for k, v in form.items() if k.startswith("qty_")}
        method = "voice" if form.get("input_method") == "voice" else "type"
        photo_bytes = None
        upload = form.get("photo")
        if upload is not None and hasattr(upload, "read"):
            photo_bytes = await upload.read(max_photo_bytes + 1)
            if len(photo_bytes) > max_photo_bytes:
                return error(413, "รูปใหญ่เกินไป", f"ไม่เกิน {max_photo_bytes // 1_000_000} MB")
            photo_bytes = photo_bytes or None  # an empty file input means "no photo"
        try:
            result = await run_in_threadpool(service.save_slot, code, user, raw, method, photo_bytes)
        except SlotNotFound:
            return error(404, f"ไม่พบช่อง {code.upper()}")
        except SessionClosed:
            return error(409, "ส่งยอดวันนี้ไปแล้ว", "แก้ยอดไม่ได้หลังส่ง — พรุ่งนี้นับรอบใหม่")
        except CountError as e:
            return slot_response(request, code, status=422, errors=e.errors, values=raw)

        request.session["flash"] = {
            "code": code.upper(),
            "mismatches": [asdict(m) for m in result.mismatches],
            "cv": result.cv.status if result.cv else None,
            "classes": [asdict(c) for c in result.cv.classes] if result.cv else [],
            "too_dark": result.too_dark,
            "photo_error": bool(result.photo_error),
        }
        flagged = result.cv is not None and result.cv.status == "flagged"
        target = service.next_slot()
        if flagged or target is None:
            # stay to recount when CV disagrees; go back to the map when every slot is done
            return RedirectResponse(f"/loc/{code.upper()}" if flagged else "/map", status_code=303)
        return RedirectResponse(f"/loc/{target}", status_code=303)

    @app.post("/loc/{code}/voice")
    async def slot_voice(request: Request, code: str):
        user = current_user(request)
        if isinstance(user, Response):
            return JSONResponse({"ok": False}, status_code=user.status_code)
        body = await request.json()
        try:
            counts = await run_in_threadpool(service.recognise, code, str(body.get("text", ""))[:500])
        except SlotNotFound:
            return JSONResponse({"ok": False}, status_code=404)
        return {"ok": True, "counts": counts}

    @app.get("/scan")
    def scan_page(request: Request):
        user = current_user(request)
        if isinstance(user, Response):
            return user
        return page("scan.html", nav="scan")

    @app.get("/report")
    def report_page(request: Request, week: str | None = None):
        user = current_user(request)
        if isinstance(user, Response):
            return user
        week = week or week_of(service.today())
        try:
            start, _ = week_bounds(week)
        except ValueError:
            return error(404, f"ไม่รู้จักสัปดาห์ {week}")
        prev_week = week_of(date.fromordinal(start.toordinal() - 7))
        next_week = week_of(date.fromordinal(start.toordinal() + 7))
        return page("report.html", nav="report", r=service.report(week), prev_week=prev_week, next_week=next_week)

    return app


def build_default_app() -> FastAPI:
    """Wire the real app from .env + config.yaml. Dev mode (APP_ENV=dev) runs on the PC without LINE."""
    from dotenv import load_dotenv

    from .config import load_config
    from .repo import InMemoryRepo, SupabaseRepo

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    # httpx logs every request URL at INFO — Roboflow's key travels in the URL, so keep it out of the logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    dev = os.environ.get("APP_ENV") == "dev"
    if dev and any(name.startswith("RAILWAY_") for name in os.environ):
        raise RuntimeError("APP_ENV=dev skips the LINE login — never use it on Railway")
    config = load_config(os.environ.get("STOCKCOUNT_CONFIG", "config.yaml"))

    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        if not dev:
            raise RuntimeError("SESSION_SECRET must be set outside dev mode")
        secret = "dev-only-not-secret"

    if os.environ.get("SUPABASE_URL"):
        repo = SupabaseRepo.from_env()
    else:
        stock_csv = os.environ.get("DEV_STOCK_CSV", "data/stock_2026-09-28.csv")
        repo = InMemoryRepo.from_files(stock_csv, config.layout_file, date(2026, 9, 28))
        log.warning("no SUPABASE_URL: using in-memory data from %s (lost on restart)", stock_csv)

    cv_client = None
    if config.cv.enabled and config.cv.model and os.environ.get("ROBOFLOW_API_KEY"):
        from .roboflow import DEFAULT_URL, RoboflowClient

        cv_client = RoboflowClient(
            config.cv.model, os.environ["ROBOFLOW_API_KEY"], base_url=os.environ.get("ROBOFLOW_API_URL", DEFAULT_URL)
        )

    notifier = None
    if os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"):
        from .line_push import LinePushNotifier

        notifier = LinePushNotifier(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])

    verifier = None
    if os.environ.get("LINE_LIFF_CHANNEL_ID"):
        from .auth import LineTokenVerifier

        verifier = LineTokenVerifier(os.environ["LINE_LIFF_CHANNEL_ID"])

    service = CountingService(
        config, repo, clock=lambda: datetime.now(timezone.utc), cv_client=cv_client, notifier=notifier
    )
    return create_app(
        service,
        session_secret=secret,
        verifier=verifier,
        dev_user_id=os.environ.get("DEV_USER_ID") if dev else None,
        liff_id=config.liff_id,
        https_only=not dev,
    )
