"""Thai text the server sends or shows outside the HTML templates (form errors, the LINE summary)."""
from __future__ import annotations

FIELD_REQUIRED = "กรอกตัวเลข"
FIELD_INVALID = "ต้องเป็นจำนวนเต็ม 0 ขึ้นไป"
TARGET_MINUTES = 10


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
    return "\n".join(lines)
