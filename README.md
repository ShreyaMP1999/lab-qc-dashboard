# Lab QC Analytics Dashboard

A multi-site, multi-assay lab quality control monitoring dashboard. Built to
show two things together: real SQL querying against a database, and
multi-tool data visualization (Plotly, Seaborn, Matplotlib) in one working
dashboard.

## Problem

Labs running the same assay across multiple sites need to know, fast: which
site/assay combinations are drifting out of acceptance limits, and when a
drift started, not just that a single run failed. This project simulates
that monitoring problem with realistic synthetic QC data.

## Data

`src/generate_data.py` generates 8 months of daily QC control runs across:
- 4 sites (Irvine, Chicago, Austin, Raleigh)
- 4 assays (Lyme-OspC, RPR, SyphT, HbA1c-QC)
- 3 control levels (Low, Medium, High)

That's 11,520 rows, loaded into a SQLite database (`data/lab_qc.db`) with
indexes on site/assay and run_date, and a ~2.3% baseline out-of-range rate
with injected drift events, so the dashboard has something real to surface.

## SQL querying (`src/queries.py`)

Every chart in the dashboard is backed by an actual SQL query, not a pandas
groupby standing in for one:

- **`summary_by_site_assay()`** — `GROUP BY` with conditional aggregation
  (`AVG` of a 0/1 flag as a pass rate)
- **`daily_trend()`** — filtered aggregation by site/assay/control level
- **`rolling_out_of_range_rate()`** — a **window function**
  (`AVG(...) OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)`)
  for a 7-run rolling pass rate, used to catch drift before it becomes a
  full failure pattern
- **`worst_performing_combinations()`** — a CTE with `HAVING` to exclude
  low-volume combinations, `CROSS JOIN`ed against an overall-average CTE to
  rank how far each site/assay combination sits below the mean

## Visualization (`dashboard/app.py`)

Three different tools, each used for what it's actually good at:

- **Plotly** — interactive trend line with acceptance limit bands, for
  exploring a single site/assay/control level combination
- **Seaborn** — a pass-rate heatmap across every site × assay combination,
  for spotting problem areas at a glance
- **Matplotlib** — a rolling pass-rate control chart, the kind of static,
  precise chart you'd actually put in a validation report

## Project structure

```
lab-qc-dashboard/
├── src/
│   ├── generate_data.py     # builds the synthetic dataset, loads SQLite
│   └── queries.py           # all SQL queries, run directly against the DB
├── dashboard/
│   └── app.py                # Streamlit app: Plotly + Seaborn + Matplotlib
├── data/
│   └── lab_qc.db              # SQLite database (created by generate_data.py)
└── requirements.txt
```

## Running it locally

```bash
pip install -r requirements.txt

# 1. Generate the dataset and load it into SQLite
python src/generate_data.py

# 2. (optional) sanity-check the queries directly
python src/queries.py

# 3. Run the dashboard
streamlit run dashboard/app.py
```

## Notes

Data is synthetic, generated to resemble real multi-site QC monitoring
patterns (systematic site bias, level-dependent variance, occasional drift
events), not real patient or instrument data.
