"""Load and validate config.yaml — settings only; the shelf layout lives in the layout CSV."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .location import LocationError, parse_location

CAMERAS = ("back", "front")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class CvConfig:
    enabled: bool = True
    model: str = ""
    min_confidence: float = 0.5
    tolerance_ratio: float = 0.10
    disabled_locations: frozenset[str] = field(default_factory=frozenset)

    def is_enabled_for(self, location_code: str) -> bool:
        return self.enabled and location_code not in self.disabled_locations


@dataclass(frozen=True)
class AppConfig:
    branch: str
    line_basic_id: str
    liff_id: str
    allowed_line_user_ids: frozenset[str]
    camera_default: str
    layout_file: str
    cv: CvConfig
    min_brightness: int

    def is_allowed(self, user_id: str) -> bool:
        return not self.allowed_line_user_ids or user_id in self.allowed_line_user_ids


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return parse_config(raw)


def _ratio(section: dict, key: str, default: float) -> float:
    value = float(section.get(key, default))
    if not 0 <= value <= 1:
        raise ConfigError(f"cv.{key} must be between 0 and 1, got {value}")
    return value


def _parse_cv(raw: dict) -> CvConfig:
    disabled = set()
    for code in raw.get("disabled_locations") or ():
        try:
            disabled.add(parse_location(str(code)).code)
        except LocationError as e:
            raise ConfigError(f"cv.disabled_locations: {e}") from e
    return CvConfig(
        enabled=bool(raw.get("enabled", True)),
        model=str(raw.get("model", "")),
        min_confidence=_ratio(raw, "min_confidence", 0.5),
        tolerance_ratio=_ratio(raw, "tolerance_ratio", 0.10),
        disabled_locations=frozenset(disabled),
    )


def parse_config(raw: dict) -> AppConfig:
    if not raw.get("branch"):
        raise ConfigError("missing 'branch'")
    camera = str(raw.get("camera_default", "back"))
    if camera not in CAMERAS:
        raise ConfigError(f"camera_default must be one of {CAMERAS}, got '{camera}'")
    brightness = int((raw.get("photo") or {}).get("min_brightness", 60))
    if not 0 <= brightness <= 255:
        raise ConfigError(f"photo.min_brightness must be 0-255, got {brightness}")

    return AppConfig(
        branch=str(raw["branch"]),
        line_basic_id=str(raw.get("line_basic_id", "")),
        liff_id=str(raw.get("liff_id", "")),
        allowed_line_user_ids=frozenset(raw.get("allowed_line_user_ids") or ()),
        camera_default=camera,
        layout_file=str(raw.get("layout_file", "data/layout_mbk.csv")),
        cv=_parse_cv(raw.get("cv") or {}),
        min_brightness=brightness,
    )
