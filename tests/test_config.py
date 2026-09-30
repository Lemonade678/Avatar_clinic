from pathlib import Path

import pytest

from stockcount.config import ConfigError, load_config, parse_config


def raw(**over):
    base = {
        "branch": "ladprao",
        "line_basic_id": "@abc1234",
        "shelves": {"A1": {"label": "ชั้นเหล็กซ้าย 1", "skus": ["HB0001", "HB0003"]}},
    }
    base.update(over)
    return base


def test_parses_shelf_label_and_sku_order():
    cfg = parse_config(raw())
    assert cfg.shelves["A1"].label == "ชั้นเหล็กซ้าย 1"
    assert cfg.shelves["A1"].skus == ("HB0001", "HB0003")


def test_lowercase_shelf_code_is_uppercased():
    cfg = parse_config(raw(shelves={"a1": {"skus": ["X1"]}}))
    assert "A1" in cfg.shelves


def test_label_defaults_to_code():
    cfg = parse_config(raw(shelves={"B2": {"skus": ["X1"]}}))
    assert cfg.shelves["B2"].label == "B2"


def test_sku_on_two_shelves_is_rejected():
    with pytest.raises(ConfigError, match="HB0001"):
        parse_config(raw(shelves={"A1": {"skus": ["HB0001"]}, "A2": {"skus": ["HB0001"]}}))


def test_shelf_without_skus_is_rejected():
    with pytest.raises(ConfigError, match="A1"):
        parse_config(raw(shelves={"A1": {"skus": []}}))


def test_bad_shelf_code_is_rejected():
    with pytest.raises(ConfigError, match="bad shelf code"):
        parse_config(raw(shelves={"ชั้น1": {"skus": ["X1"]}}))


def test_missing_basic_id_is_rejected():
    bad = raw()
    del bad["line_basic_id"]
    with pytest.raises(ConfigError, match="line_basic_id"):
        parse_config(bad)


def test_empty_allowlist_allows_everyone():
    assert parse_config(raw()).is_allowed("U-anyone")


def test_allowlist_blocks_others():
    cfg = parse_config(raw(allowed_line_user_ids=["U-ok"]))
    assert cfg.is_allowed("U-ok")
    assert not cfg.is_allowed("U-other")


def test_repo_config_yaml_loads():
    cfg = load_config(Path(__file__).parents[1] / "config.yaml")
    assert cfg.branch == "mbk"
    assert list(cfg.shelves) == ["A1", "A2"]
