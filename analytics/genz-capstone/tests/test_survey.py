import numpy as np
import pandas as pd
import pytest
from survey.synth import generate, header
from survey.clean import clean, rename_columns
from survey import stats as st
from survey.report import run

@pytest.fixture(scope="module")
def raw():
    return generate(150, seed=11)

def test_headers_map_to_codes(raw):
    df, unknown = rename_columns(raw)
    assert "C1_neck" in df and "F2_doctor" in df and "D1" in df
    assert unknown == ["ประทับเวลา"]

def test_screening_flow_monotone(raw):
    f = clean(raw).flow
    assert f["responses"] >= f["consented"] >= f["age_eligible"] >= f["analysed"]

def test_out_of_range_age_is_dropped_and_logged(raw):
    bad = raw.copy()
    bad.loc[0, header("Q0_1", "ท่านยินยอม...")] = "ยินยอม"
    bad.loc[0, header("Q0_2", "ท่านอายุ 20–29 ปีหรือไม่")] = "ใช่"
    bad.loc[0, header("A1", "อายุ (ปี)")] = 35
    r = clean(bad)
    assert any("อายุจริงนอกช่วง" in l for l in r.log)
    assert (r.data["age"] <= 29).all()

def test_unknown_option_is_logged(raw):
    bad = raw.copy(); bad.loc[1, header("A2", "เพศ")] = "อื่น"
    r = clean(bad); assert any(l.startswith("A2") for l in r.log)

def test_multiselect_parsed(raw):
    d = clean(raw).data
    assert set(d["G2__ไม่เคย"].unique()) <= {0, 1}
    assert ((d["helped_parents"] == 1) | (d["G2__ไม่เคย"] == 1)).all()

def test_stage_and_hesitant(raw):
    d = clean(raw).data
    assert d["stage"].between(1, 5).all()
    assert (d["hesitant"] == d["stage"].isin([2, 3]).astype(int)).all()

def test_wilson_known_value():
    p, lo, hi = st.wilson_ci(45, 100)
    assert lo == pytest.approx(0.356, abs=0.002) and hi == pytest.approx(0.548, abs=0.002)

def test_cronbach_perfect_items():
    x = pd.Series([1, 2, 3, 4, 5.0])
    assert st.cronbach_alpha(pd.DataFrame({"a": x, "b": x, "c": x})) == pytest.approx(1.0)

def test_odds_ratio_simple():
    e = [1] * 20 + [0] * 20; o = [1] * 15 + [0] * 5 + [1] * 5 + [0] * 15
    assert st.odds_ratio(e, o)["or"] == pytest.approx(9.0)

def test_power_increases_with_n():
    assert st.simulate_power_2x2(400, reps=300) > st.simulate_power_2x2(60, reps=300)

def test_report_runs(raw, tmp_path):
    path, f = run(clean(raw), tmp_path, True, "t")
    text = path.read_text(encoding="utf-8")
    assert "SYNTHETIC" in text and (tmp_path / "open_ended_for_coding.csv").exists()
    assert 0 <= f["hesitant"][0] <= 1
