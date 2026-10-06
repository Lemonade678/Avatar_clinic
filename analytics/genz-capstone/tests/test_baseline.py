import math
import pandas as pd
import pytest
from baseline.inputs import load_manual, load_export, load_audience, map_columns, age_bucket
from baseline.metrics import ratio, summarise
from baseline.report import build, run

MANUAL = """metric,value,verified,source,note
audience_pct_18_24,1.6,0,screenshot,
audience_pct_25_34,25.9,1,export,
plays,"2,000,000",0,screenshot,rounded
reach,1000000,0,screenshot,
views_3s,500000,0,screenshot,
comments,300,0,screenshot,
shares,2000,0,screenshot,
dropoff_sec,4,0,screenshot,
"""

@pytest.fixture
def manual(tmp_path):
    p = tmp_path / "m.csv"; p.write_text(MANUAL, encoding="utf-8"); return load_manual(p)

def by_key(summary):
    return {m.key: m for m, _ in summary}

def test_ratio_handles_missing_and_zero():
    assert ratio(1, 4, 100) == 25
    assert math.isnan(ratio(1, 0)) and math.isnan(ratio(float("nan"), 3)) and math.isnan(ratio(1, None))

def test_manual_metrics(manual):
    s = by_key(summarise(manual)[1])
    assert s["retention_3s_per_play"].value == pytest.approx(25.0)
    assert s["retention_3s_per_reach"].value == pytest.approx(50.0)
    assert s["shares_per_1k_reach"].value == pytest.approx(2.0)
    assert s["comments_per_1k_reach"].value == pytest.approx(0.3)
    assert s["dropoff_sec"].value == 4
    assert s["audience_pct_18_24"].value == 1.6

def test_verified_propagates(manual):
    s = by_key(summarise(manual)[1])
    assert not s["shares_per_1k_reach"].verified
    assert s["audience_pct_25_34"].verified and not s["audience_pct_18_24"].verified

def test_manual_rejects_unknown_metric(tmp_path):
    p = tmp_path / "bad.csv"; p.write_text("metric,value,verified,source,note\nlikes,5,0,x,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown metrics"): load_manual(p)

def test_manual_rejects_bad_verified_flag(tmp_path):
    p = tmp_path / "bad.csv"; p.write_text("metric,value,verified,source,note\nreach,5,maybe,x,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="verified"): load_manual(p)

def test_report_flags_unverified(manual, tmp_path):
    path, _ = run(manual, tmp_path, today="2026-09-26")
    text = path.read_text(encoding="utf-8")
    assert path.name == "Baseline - Facebook Insights.md"
    assert text.startswith("---\n") and "verified: false" in text and "[!warning]" in text
    assert "1.6% ⚠️" in text and "25.9%" in text and "25.9% ⚠️" not in text
    assert "n = 1 โพสต์" in text

def test_age_bucket():
    assert age_bucket("18-24") == "18_24" and age_bucket("Age 25 – 34") == "25_34" and age_bucket("65+") == "65_plus"
    with pytest.raises(ValueError): age_bucket("adults")

def test_map_columns_aliases_and_override():
    cols = ["Post ID", "Reach", "Views", "3-second video views", "Shares", "Comments", "Weird"]
    m, unmatched = map_columns(cols)
    assert m["reach"] == "Reach" and m["views_3s"] == "3-second video views" and unmatched == ["Weird"]
    m, _ = map_columns(cols, {"reach": "Weird"})
    assert m["reach"] == "Weird"
    with pytest.raises(ValueError): map_columns(cols, {"reach": "nope"})

@pytest.fixture
def export(tmp_path):
    posts = pd.DataFrame({"Post ID": ["a", "b", "c"], "Reach": [1000, 2000, 4000],
                          "Views": [2000, 4000, 8000], "3-second video views": [1000, 1000, 2000],
                          "Shares": [1, 4, 20], "Comments": ["2", "1,000", ""]})
    aud = pd.DataFrame({"Age": ["18-24", "18-24", "25-34", "35-44"], "Gender": ["F", "M", "F", "F"],
                        "Percent": [0.01, 0.01, 0.48, 0.50]})
    p1, p2 = tmp_path / "posts.xlsx", tmp_path / "age.csv"
    posts.to_excel(p1, index=False); aud.to_csv(p2, index=False)
    return load_export(p1, p2)

def test_export_median_across_posts(export):
    per_post, summary = summarise(export)
    s = {m.key: (m, n) for m, n in summary}
    assert s["retention_3s_per_play"][0].value == pytest.approx(25.0)       # 50, 25, 25 -> median 25
    assert s["shares_per_1k_reach"][0].value == pytest.approx(2.0)          # 1, 2, 5
    assert s["comments_per_1k_reach"] == (s["comments_per_1k_reach"][0], 2) # blank comment skipped
    assert s["comments_per_1k_reach"][0].value == pytest.approx(251.0)      # 2, 500
    assert s["shares_per_1k_reach"][0].verified and not s["dropoff_sec"][0].verified
    assert len(per_post) == 3 * 5

def test_audience_sums_gender_and_scales(export):
    assert export.audience["audience_pct_18_24"] == pytest.approx(2.0)
    assert export.audience["audience_pct_25_34"] == pytest.approx(48.0)
    assert any("คูณ 100" in l for l in export.log)

def test_audience_total_warning(tmp_path):
    p = tmp_path / "a.csv"; pd.DataFrame({"age": ["18-24"], "share": [40]}).to_csv(p, index=False)
    _, log = load_audience(p)
    assert any("⚠️" in l for l in log)

def test_export_report_is_verified_except_missing(export):
    text, _ = build(export, today="2026-09-26")
    assert "## 3. รายโพสต์" in text and "มัธยฐาน" in text and "Path A (export)" in text
    assert "n = 1 โพสต์" not in text
    assert "verified: true" in text and "[!warning]" not in text   # missing drop-off is not 'unverified'
