"""One counting round: start the clock, open a slot, save counts, check a photo, submit the shift."""
from __future__ import annotations

import logging
from collections import namedtuple
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Protocol
from zoneinfo import ZoneInfo

from . import messages
from .config import AppConfig
from .cv import SKIPPED, CvCheck, CvClient, CvUnavailable, compare_cv, count_predictions, human_counts_by_class
from .location import Location
from .minimap import Minimap, apply_progress, build_minimap, item_status
from .photo import PhotoError, brightness, is_too_dark, shrink
from .repo import CountRow, PhotoRecord, Repo, Session
from .report import WeeklyReport, build_weekly_report, week_bounds
from .speech import parse_spoken
from .thai_digits import parse_count

BANGKOK = ZoneInfo("Asia/Bangkok")
TO_COUNT = ("check", "problem")  # quantity > 0, or a negative system record that needs a real number

log = logging.getLogger(__name__)
_Line = namedtuple("_Line", "sku name front_qty")


class Notifier(Protocol):
    def push(self, user_id: str, text: str) -> None: ...


class SlotNotFound(LookupError):
    pass


class SessionClosed(RuntimeError):
    pass


class CountError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__(f"invalid counts: {errors}")
        self.errors = errors


@dataclass(frozen=True)
class SlotItem:
    sku: str
    name: str
    packaging: str | None
    expected: int
    status: str
    last: tuple[date, int] | None
    counted: int | None


@dataclass(frozen=True)
class SlotView:
    location: Location
    items: tuple[SlotItem, ...]
    hidden_empty: int
    session: Session | None
    photos: tuple[PhotoRecord, ...]
    read_only: bool
    cv_enabled: bool

    @property
    def code(self) -> str:
        return self.location.code


@dataclass(frozen=True)
class Mismatch:
    sku: str
    name: str
    code: str
    expected: int
    counted: int


@dataclass(frozen=True)
class SaveResult:
    mismatches: tuple[Mismatch, ...]
    cv: CvCheck | None
    too_dark: bool = False
    photo_error: str | None = None


@dataclass(frozen=True)
class ShiftSummary:
    count_date: date
    started_at: datetime | None
    ended_at: datetime | None
    minutes: float | None
    slots_done: int
    slots_total: int
    missing_slots: tuple[str, ...]
    mismatches: tuple[Mismatch, ...]
    cv_flagged_slots: tuple[str, ...]


class CountingService:
    def __init__(self, config: AppConfig, repo: Repo, clock: Callable[[], datetime],
                 cv_client: CvClient | None = None, notifier: Notifier | None = None):
        self.config = config
        self.repo = repo
        self.clock = clock
        self.cv_client = cv_client
        self.notifier = notifier

    def now(self) -> datetime:
        return self.clock()

    def today(self) -> date:
        return self.now().astimezone(BANGKOK).date()

    # --- time clock ---------------------------------------------------------------
    def start(self, user_id: str) -> Session:
        return self.repo.start_session(self.today(), self.now(), user_id)

    def submit(self, user_id: str) -> ShiftSummary:
        session = self.start(user_id)  # submitting with no counts still records the round
        self.repo.end_session(session.id, self.now())
        summary = self.summary()
        if self.notifier is not None:
            try:
                self.notifier.push(user_id, messages.summary_text(summary, self.config.branch))
            except Exception:
                log.exception("pushing the shift summary to LINE failed")  # the round is already saved
        return summary

    # --- slots --------------------------------------------------------------------
    def _location(self, code: str) -> Location:
        wanted = code.strip().upper()
        for p in self.repo.placements():
            if p.location.code == wanted:
                return p.location
        raise SlotNotFound(wanted)

    def _slots_to_count(self) -> dict[str, list[str]]:
        _, front = self.repo.stock()
        slots: dict[str, list[str]] = {}
        for p in self.repo.placements():
            if item_status(front.get(p.sku, 0)) in TO_COUNT:
                slots.setdefault(p.location.code, []).append(p.sku)
        return slots

    def walk_order(self) -> list[str]:
        """Slots with something to count, in the order the minimap shows them: left then right, top storey first."""
        slots = self._slots_to_count()
        locations = {p.location.code: p.location for p in self.repo.placements() if p.location.code in slots}
        order = sorted(locations.values(), key=lambda l: (l.side, l.shelf, -l.storey))
        return [l.code for l in order]

    def next_slot(self) -> str | None:
        """The first slot in walk order that still has an uncounted product today."""
        session = self.repo.session_for(self.today())
        counted = {r.sku for r in self.repo.counts(session.id)} if session else set()
        slots = self._slots_to_count()
        return next((code for code in self.walk_order() if not all(s in counted for s in slots[code])), None)

    def slot(self, code: str) -> SlotView:
        location = self._location(code)
        products = self.repo.products()
        _, front = self.repo.stock()
        session = self.repo.session_for(self.today())
        counted = {r.sku: r.counted_qty for r in self.repo.counts(session.id)} if session else {}
        last = self.repo.last_counts(before=self.today())

        items, hidden = [], 0
        for p in self.repo.placements():
            if p.location.code != location.code:
                continue
            qty = front.get(p.sku, 0)
            status = item_status(qty)
            if status not in TO_COUNT:
                hidden += 1
                continue
            product = products[p.sku]
            items.append(SlotItem(p.sku, product.name, product.packaging, qty, status, last.get(p.sku), counted.get(p.sku)))

        photos = tuple(ph for ph in self.repo.photos(session.id) if ph.location_code == location.code) if session else ()
        return SlotView(
            location=location,
            items=tuple(items),
            hidden_empty=hidden,
            session=session,
            photos=photos,
            read_only=bool(session and session.submitted),
            cv_enabled=self.cv_client is not None and self.config.cv.is_enabled_for(location.code),
        )

    def save_slot(self, code: str, user_id: str, raw: dict[str, str], input_method: str = "type",
                  photo: bytes | None = None) -> SaveResult:
        view = self.slot(code)
        if view.read_only:
            raise SessionClosed(f"today's round was already submitted ({view.session.count_date})")

        errors, values = {}, {}
        for item in view.items:
            text = raw.get(item.sku)
            if text is None or not str(text).strip():
                errors[item.sku] = messages.FIELD_REQUIRED
                continue
            value = parse_count(str(text))
            if value is None:
                errors[item.sku] = messages.FIELD_INVALID
            else:
                values[item.sku] = value
        if errors:
            raise CountError(errors)  # all or nothing: one bad field saves nothing

        session = self.start(user_id)  # forgot to press start? the first save starts the clock
        now = self.now()
        rows = [CountRow(view.code, i.sku, i.expected, values[i.sku], input_method) for i in view.items]
        if rows:
            self.repo.save_counts(session.id, rows, user_id, now)
        mismatches = tuple(
            Mismatch(i.sku, i.name, view.code, i.expected, values[i.sku]) for i in view.items if values[i.sku] != i.expected
        )
        if photo is None:
            return SaveResult(mismatches, None)

        try:
            photo = shrink(photo)  # smaller upload to Roboflow + years of photos inside the free storage
            light = brightness(photo)
        except PhotoError as e:
            log.warning("photo for %s rejected: %s", view.code, e)
            return SaveResult(mismatches, None, photo_error=str(e))
        human = human_counts_by_class(values, {i.sku: i.packaging for i in view.items if i.packaging})
        check = self._cv_check(view.code, photo, human)
        self.repo.save_photo(session.id, view.code, user_id, photo, check, human, light, now)
        return SaveResult(mismatches, check, too_dark=is_too_dark(light, self.config.min_brightness))

    def _cv_check(self, code: str, photo: bytes, human: dict[str, int]) -> CvCheck:
        if self.cv_client is None or not self.config.cv.is_enabled_for(code):
            return SKIPPED
        try:
            predictions = self.cv_client.predict(photo)
        except CvUnavailable as e:
            log.warning("CV not checked for %s: %s", code, e)
            return SKIPPED
        cv = count_predictions(predictions, self.config.cv.min_confidence)
        return compare_cv(human, cv, self.config.cv.tolerance_ratio)

    def recognise(self, code: str, text: str) -> dict[str, int]:
        """Voice (or quick-typed) text -> counts, limited to the products of this slot."""
        view = self.slot(code)
        return parse_spoken(text, [(i.sku, i.name) for i in view.items])

    # --- views over the day / week ------------------------------------------------
    def summary(self, day: date | None = None) -> ShiftSummary:
        day = day or self.today()
        session = self.repo.session_for(day)
        counts = self.repo.counts(session.id) if session else []
        counted = {r.sku for r in counts}
        slots = self._slots_to_count()
        done = [code for code, skus in slots.items() if all(s in counted for s in skus)]
        products = self.repo.products()
        mismatches = tuple(
            Mismatch(r.sku, products[r.sku].name if r.sku in products else r.sku, r.location_code, r.expected_qty, r.counted_qty)
            for r in sorted(counts, key=lambda r: (r.location_code, r.sku))
            if r.counted_qty != r.expected_qty
        )
        flagged = sorted({p.location_code for p in self.repo.photos(session.id) if p.cv_status == "flagged"}) if session else []
        minutes = None
        if session and session.ended_at:
            minutes = round((session.ended_at - session.started_at).total_seconds() / 60, 1)
        return ShiftSummary(
            count_date=day,
            started_at=session.started_at if session else None,
            ended_at=session.ended_at if session else None,
            minutes=minutes,
            slots_done=len(done),
            slots_total=len(slots),
            missing_slots=tuple(sorted(code for code in slots if code not in done)),
            mismatches=mismatches,
            cv_flagged_slots=tuple(flagged),
        )

    def minimap(self) -> Minimap:
        products = self.repo.products()
        _, front = self.repo.stock()
        base = build_minimap(self.repo.placements(), [_Line(s, p.name, front.get(s, 0)) for s, p in products.items()])
        session = self.repo.session_for(self.today())
        if session is None:
            return base
        counted = {r.sku: r.counted_qty for r in self.repo.counts(session.id)}
        flagged = {p.location_code for p in self.repo.photos(session.id) if p.cv_status == "flagged"}
        return apply_progress(base, counted, flagged)

    def report(self, week: str) -> WeeklyReport:
        start, end = week_bounds(week)
        names = {sku: p.name for sku, p in self.repo.products().items()}
        return build_weekly_report(
            week, self.repo.count_records(until=end), self.repo.sessions(), self.repo.cv_statuses(start, end), names
        )
