"""
Lab QC Analytics Dashboard.

Reads from a SQLite database via real SQL queries (src/queries.py) and
visualizes results three ways:
  - Plotly for the interactive trend chart
  - Seaborn for the site/assay heatmap
  - Matplotlib for the rolling pass-rate control chart

Run with: streamlit run dashboard/app.py
"""

import os
import sys

import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src import queries

st.set_page_config(page_title="Lab QC Analytics Dashboard", layout="wide")

st.title("Lab QC Analytics Dashboard")
st.caption(
    "Multi-site, multi-assay quality control monitoring. Data is queried live "
    "from SQLite (aggregations, joins, and a rolling window function), then "
    "visualized with Plotly, Seaborn, and Matplotlib."
)

sites, assays = queries.get_filter_options()

# ---------------------------------------------------------------------------
# Section 1: Overview table (SQL: GROUP BY + conditional aggregation)
# ---------------------------------------------------------------------------
st.subheader("Pass rate by site and assay")
summary_df = queries.summary_by_site_assay()
st.dataframe(summary_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Section 2: Seaborn heatmap of pass rate across site x assay
# ---------------------------------------------------------------------------
st.subheader("Pass rate heatmap")
pivot = summary_df.pivot(index="assay", columns="site", values="pass_rate_pct")

fig, ax = plt.subplots(figsize=(8, 3.5))
sns.heatmap(pivot, annot=True, fmt=".1f", cmap="RdYlGn", vmin=90, vmax=100, ax=ax, cbar_kws={"label": "Pass rate %"})
ax.set_title("Pass Rate (%) by Site and Assay")
st.pyplot(fig)

st.divider()

# ---------------------------------------------------------------------------
# Section 3: Plotly interactive trend chart (SQL: filtered aggregation)
# ---------------------------------------------------------------------------
st.subheader("QC result trend over time")
col1, col2, col3 = st.columns(3)
with col1:
    sel_site = st.selectbox("Site", sites)
with col2:
    sel_assay = st.selectbox("Assay", assays)
with col3:
    sel_level = st.selectbox("Control level", ["Low", "Medium", "High"])

trend_df = queries.daily_trend(sel_site, sel_assay, sel_level)

trend_fig = px.line(
    trend_df,
    x="run_date",
    y="mean_result",
    title=f"{sel_assay} ({sel_level}) — {sel_site}",
    labels={"mean_result": "Mean result", "run_date": "Date"},
)
trend_fig.add_scatter(
    x=trend_df["run_date"], y=trend_df["upper_limit"], mode="lines",
    line=dict(dash="dash", color="red"), name="Upper limit",
)
trend_fig.add_scatter(
    x=trend_df["run_date"], y=trend_df["lower_limit"], mode="lines",
    line=dict(dash="dash", color="red"), name="Lower limit",
)
st.plotly_chart(trend_fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Section 4: Matplotlib rolling pass-rate control chart (SQL: window function)
# ---------------------------------------------------------------------------
st.subheader("7-run rolling pass rate (drift detection)")
rolling_df = queries.rolling_out_of_range_rate(sel_site, sel_assay)

fig2, ax2 = plt.subplots(figsize=(10, 3.5))
for level, group in rolling_df.groupby("control_level"):
    ax2.plot(group["run_date"], group["rolling_pass_rate"] * 100, label=level, marker="o", markersize=2)
ax2.axhline(95, color="red", linestyle="--", linewidth=1, label="95% threshold")
ax2.set_ylabel("Rolling pass rate (%)")
ax2.set_xlabel("Date")
ax2.set_xticks(ax2.get_xticks()[::30])
ax2.legend(fontsize=8)
ax2.set_title(f"{sel_assay} — {sel_site}: rolling pass rate by control level")
plt.xticks(rotation=45)
plt.tight_layout()
st.pyplot(fig2)

st.caption(
    "This chart uses a SQL window function (rolling average over the 7 most "
    "recent runs, partitioned by control level) computed in the database, "
    "not in pandas."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 5: Worst performing combinations (SQL: CTE + HAVING + CROSS JOIN)
# ---------------------------------------------------------------------------
st.subheader("Site/assay combinations furthest below the overall pass rate")
worst_df = queries.worst_performing_combinations()
st.dataframe(worst_df, use_container_width=True, hide_index=True)
