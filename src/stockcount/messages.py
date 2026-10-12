"""Thai text the server sends or shows outside the HTML templates (form errors, the LINE summary)."""
from __future__ import annotations

from datetime import date

FIELD_REQUIRED = "กรอกตัวเลข"
FIELD_INVALID = "ต้องเป็นจำนวนเต็ม 0 ขึ้นไป"
LOT_DATE_INVALID = "อ่านวันที่ไม่ออก — พิมพ์ วัน/เดือน/ปี เช่น 17/6/69"
LOT_DATE_FUTURE = "วันที่ยังมาไม่ถึง — ใส่วันที่บนถุงที่เก่าที่สุด"
TARGET_MINUTES = 10
LINE_NAMES = 5  # names per shelf-life line in the LINE summary


def lot_date_text(d: date) -> str:
    """17/6/69 — the short Buddhist-era form written on the packs."""
    return f"{d.day}/{d.month}/{(d.year + 543) % 100:02d}"


def shelf_life_text(months: int) -> str:
    return f"{months // 12} ปี" if months % 12 == 0 else f"{months} เดือน"


def _names(lots) -> str:
    names = [v.name for v in lots]
    more = f" +{len(names) - LINE_NAMES}" if len(names) > LINE_NAMES else ""
    return ", ".join(names[:LINE_NAMES]) + more


def minutes_text(minutes: float) -> str:
    return f"{minutes:g} นาที"


def summary_text(summary, branch: str) -> str:
    """The shift summary pushed to LINE after "ส่งยอดจบกะ"."""
    lines = [f"📦 สรุปนับสต็อก {branch.upper()} — {summary.count_date:%d/%m/%Y}"]
    if summary.minutes is not None:
        verdict = "✅" if summary.minutes < TARGET_MINUTES else f"(เป้า < {TARGET_MINUTES} นาที)"
        lines.append(f"⏱️ ใช้เวลา {minutes_text(summary.minutes)} {verdict}")
    lines.append(f"นับแล้ว {summary.slots_done}/{summary.slots_total} ช่อง")
    if summary.missing_slots:
        lines.append("ยังไม่นับ: " + ", ".join(summary.missing_slots))
    if summary.mismatches:
        lines.append(f"ไม่ตรงกับระบบ {len(summary.mismatches)} รายการ:")
        lines += [f"• {m.name} ({m.code}) ระบบ {m.expected} / นับ {m.counted}" for m in summary.mismatches]
    else:
        lines.append("ตรงกับระบบทุกรายการ ✅")
    if summary.cv_flagged_slots:
        lines.append("⚠️ CV ขอให้นับซ้ำ: " + ", ".join(summary.cv_flagged_slots))
    life = shelf_life_text(summary.shelf_life_months)
    expired = [v for v in summary.expiring if v.status == "expired"]
    soon = [v for v in summary.expiring if v.status == "soon"]
    if expired:
        lines.append(f"🔴 ครบ {life}แล้ว: {_names(expired)}")
    if soon:
        lines.append(f"🟡 ใกล้ครบ {life}: {_names(soon)}")
    return "\n".join(lines)
