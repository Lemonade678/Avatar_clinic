"""Render HTML pages from Jinja2 templates — UTF-8 and auto-escaped."""
from __future__ import annotations

from jinja2 import Environment, PackageLoader, select_autoescape

from . import keyboard
from .minimap import Minimap

_env = Environment(loader=PackageLoader("stockcount", "templates"), autoescape=select_autoescape(["html"]))


def render_minimap(minimap: Minimap, *, branch_label: str, as_of: str, generated_at: str) -> str:
    return _env.get_template("minimap.html").render(
        m=minimap,
        left=[w for w in minimap.walls if w.side == "L"],
        right=[w for w in minimap.walls if w.side == "R"],
        branch_label=branch_label,
        as_of=as_of,
        generated_at=generated_at,
        en_to_th=keyboard.EN_TO_TH,
        th_to_en=keyboard.TH_TO_EN,
    )
