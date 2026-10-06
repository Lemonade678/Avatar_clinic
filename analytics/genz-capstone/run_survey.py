"""CLI: python run_survey.py <google_forms_export.csv> [--synthetic] [--out DIR]
       python run_survey.py --demo            # generate synthetic data and run everything"""
import argparse, pandas as pd
from survey.clean import clean
from survey.report import run
from survey.synth import generate

ap = argparse.ArgumentParser()
ap.add_argument("csv", nargs="?")
ap.add_argument("--demo", action="store_true", help="generate SYNTHETIC data (n=200) and run")
ap.add_argument("--n", type=int, default=200)
ap.add_argument("--synthetic", action="store_true", help="mark report as synthetic")
ap.add_argument("--out", default="outputs/survey_report")
a = ap.parse_args()
if a.demo:
    df = generate(a.n); df.to_csv("data/SYNTHETIC_survey.csv", index=False, encoding="utf-8-sig"); synthetic = True
else:
    df = pd.read_csv(a.csv); synthetic = a.synthetic
res = clean(df)
title = "Survey Report (SYNTHETIC DEMO)" if synthetic else "Survey Report"
path, f = run(res, a.out, synthetic, title)
print("flow:", res.flow); print("report:", path)
for k, v in f.items(): print(" ", k, v if not isinstance(v, dict) else {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()})
