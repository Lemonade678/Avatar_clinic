"""Load and validate config.yaml: branch, LINE basic ID, allowlist, shelf layout."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

SHELF_CODE_RE = re.compile(r"^[A-Z0-9-]{1,10}$")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Shelf:
    code: str
    label: str
    skus: tuple[str, ...]


@dataclass(frozen=True)
class AppConfig:
    branch: str
    line_basic_id: str
    allowed_line_user_ids: frozenset[str]
    shelves: dict[str, Shelf]

    def is_allowed(self, user_id: str) -> bool:
        return not self.allowed_line_user_ids or user_id in self.allowed_line_user_ids


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return parse_config(raw)


def parse_config(raw: dict) -> AppConfig:
    for key in ("branch", "line_basic_id", "shelves"):
        if not raw.get(key):
            raise ConfigError(f"missing '{key}'")

    shelves: dict[str, Shelf] = {}
    shelf_of_sku: dict[str, str] = {}
    for code, body in raw["shelves"].items():
        code = str(code).upper()
        if not SHELF_CODE_RE.match(code):
            raise ConfigError(f"bad shelf code '{code}' (use A-Z, 0-9, -)")
        body = body or {}
        skus = tuple(str(s) for s in body.get("skus") or ())
        if not skus:
            raise ConfigError(f"shelf {code} has no skus")
        for sku in skus:
            if sku in shelf_of_sku:
                raise ConfigError(f"sku {sku} is on both {shelf_of_sku[sku]} and {code}")
            shelf_of_sku[sku] = code
        shelves[code] = Shelf(code=code, label=str(body.get("label", code)), skus=skus)

    return AppConfig(
        branch=str(raw["branch"]),
        line_basic_id=str(raw["line_basic_id"]),
        allowed_line_user_ids=frozenset(raw.get("allowed_line_user_ids") or ()),
        shelves=shelves,
    )
