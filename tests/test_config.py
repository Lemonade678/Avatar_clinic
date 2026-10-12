from pathlib import Path

import pytest

from stockcount.config import ConfigError, load_config, parse_config


def test_defaults_when_only_branch_is_given():
    cfg = parse_config({"branch": "mbk"})
    assert cfg.camera_default == "back"
    assert cfg.layout_file == "data/layout_mbk.csv"
    assert cfg.cv.enabled and cfg.cv.min_confidence == 0.5 and cfg.cv.tolerance_ratio == 0.10
    assert cfg.min_brightness == 60


def test_missing_branch_is_rejected():
    with pytest.raises(ConfigError, match="branch"):
        parse_config({})


def test_front_camera_can_be_the_default():
    assert parse_config({"branch": "mbk", "camera_default": "front"}).camera_default == "front"


def test_unknown_camera_is_rejected():
    with pytest.raises(ConfigError, match="camera_default"):
        parse_config({"branch": "mbk", "camera_default": "side"})


@pytest.mark.parametrize("key, value", [("tolerance_ratio", 1.5), ("min_confidence", -0.1)])
def test_cv_ratios_must_be_between_0_and_1(key, value):
    with pytest.raises(ConfigError, match=key):
        parse_config({"branch": "mbk", "cv": {key: value}})


def test_cv_can_be_switched_off_per_slot():
    cfg = parse_config({"branch": "mbk", "cv": {"disabled_locations": ["l0301"]}})
    assert cfg.cv.is_enabled_for("R0101")
    assert not cfg.cv.is_enabled_for("L0301")


def test_bad_disabled_location_is_rejected():
    with pytest.raises(ConfigError, match="X1"):
        parse_config({"branch": "mbk", "cv": {"disabled_locations": ["X1"]}})


def test_brightness_must_be_0_to_255():
    with pytest.raises(ConfigError, match="min_brightness"):
        parse_config({"branch": "mbk", "photo": {"min_brightness": 300}})


def test_empty_allowlist_allows_everyone():
    assert parse_config({"branch": "mbk"}).is_allowed("U-anyone")


def test_allowlist_blocks_others():
    cfg = parse_config({"branch": "mbk", "allowed_line_user_ids": ["U-ok"]})
    assert cfg.is_allowed("U-ok")
    assert not cfg.is_allowed("U-other")


def test_repo_config_yaml_loads():
    cfg = load_config(Path(__file__).parents[1] / "config.yaml")
    assert cfg.branch == "mbk"
    assert cfg.layout_file == "data/layout_mbk.csv"


def test_shelf_life_defaults_to_two_years_with_a_three_month_warning():
    cfg = parse_config({"branch": "mbk"})
    assert (cfg.shelf_life_months, cfg.expiry_warn_months) == (24, 3)


def test_shelf_life_can_be_set():
    cfg = parse_config({"branch": "mbk", "shelf_life": {"months": 18, "warn_months": 2}})
    assert (cfg.shelf_life_months, cfg.expiry_warn_months) == (18, 2)


@pytest.mark.parametrize("raw", [{"months": 0}, {"months": 24, "warn_months": 24}, {"months": 24, "warn_months": -1}])
def test_impossible_shelf_life_is_refused(raw):
    with pytest.raises(ConfigError, match="shelf_life"):
        parse_config({"branch": "mbk", "shelf_life": raw})
