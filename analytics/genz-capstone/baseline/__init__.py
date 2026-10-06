"""Facebook Insights baseline: pre-pilot reference values for the Avatar Gen Z pilot.

Path A: parse an Insights export (CSV/XLSX, one row per post) -> `inputs.load_export`.
Path B: hand-typed values from meeting screenshots -> `inputs.load_manual`.
Both feed the same `metrics.compute_*` and `report.run`.
"""
