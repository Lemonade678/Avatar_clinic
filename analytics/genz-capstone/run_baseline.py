"""CLI: Facebook Insights baseline -> Obsidian note.
  python run_baseline.py --out ..                                   # Path B: data/baseline_manual.csv
  python run_baseline.py --export posts.xlsx --audience age.csv --out ..   # Path A
  python run_baseline.py --export posts.csv --map reach="Reach (Accounts Center)"   # fix a column name"""
import argparse, math
from baseline.inputs import load_manual, load_export
from baseline.report import run

ap = argparse.ArgumentParser()
ap.add_argument("--manual", default="data/baseline_manual.csv", help="Path B input (values typed from screenshots)")
ap.add_argument("--export", help="Path A: Insights post export (CSV/XLSX, one row per post)")
ap.add_argument("--audience", help="Path A: age breakdown export (age column + percent column)")
ap.add_argument("--map", action="append", default=[], metavar="KEY=COLUMN", help="override export column for a canonical key")
ap.add_argument("--out", default="outputs/baseline")
a = ap.parse_args()

overrides = dict(m.split("=", 1) for m in a.map)
b = load_export(a.export, a.audience, overrides) if a.export else load_manual(a.manual)
path, summary = run(b, a.out)
print("path:", b.path, "| posts:", len(b.posts)); print("report:", path)
for m, n in summary:
    v = "–" if math.isnan(m.value) else round(m.value, 3)
    print(f"  {m.key:24s} {v!s:>10} {m.unit:4s} {'verified' if m.verified else 'UNVERIFIED'}")
for l in b.log: print("  log:", l)
