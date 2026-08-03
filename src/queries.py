"""
SQL query layer for the lab QC dashboard. Every function here runs a real SQL
query against the SQLite database, no pandas groupby standing in for it.
Demonstrates aggregation, filtering, window functions, and multi-column joins
against a self-referencing summary.
"""

import os
import sqlite3

import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "lab_qc.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_filter_options():
    """Distinct sites and assays for dashboard filter dropdowns."""
    conn = get_connection()
    sites = pd.read_sql("SELECT DISTINCT site FROM qc_results ORDER BY site", conn)["site"].tolist()
    assays = pd.read_sql("SELECT DISTINCT assay FROM qc_results ORDER BY assay", conn)["assay"].tolist()
    conn.close()
    return sites, assays


def summary_by_site_assay():
    """
    Aggregate pass rate and mean result per site/assay combination.
    Uses GROUP BY with conditional aggregation (AVG of a 0/1 flag = pass rate).
    """
    query = """
        SELECT
            site,
            assay,
            COUNT(*) AS n_runs,
            ROUND(AVG(result_value), 3) AS mean_result,
            ROUND(AVG(in_range) * 100, 2) AS pass_rate_pct,
            SUM(CASE WHEN in_range = 0 THEN 1 ELSE 0 END) AS out_of_range_count
        FROM qc_results
        GROUP BY site, assay
        ORDER BY pass_rate_pct ASC
    """
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def daily_trend(site, assay, control_level):
    """
    Daily mean result for a given site/assay/control level, used for the
    trend chart. Straightforward filtered aggregation.
    """
    query = """
        SELECT
            run_date,
            AVG(result_value) AS mean_result,
            AVG(lower_limit) AS lower_limit,
            AVG(upper_limit) AS upper_limit
        FROM qc_results
        WHERE site = ? AND assay = ? AND control_level = ?
        GROUP BY run_date
        ORDER BY run_date
    """
    conn = get_connection()
    df = pd.read_sql(query, conn, params=[site, assay, control_level])
    conn.close()
    return df


def rolling_out_of_range_rate(site, assay):
    """
    7-run rolling out-of-range rate using a SQL window function, to spot
    drift before it becomes a full-blown failure pattern.
    """
    query = """
        SELECT
            run_date,
            control_level,
            in_range,
            AVG(CAST(in_range AS FLOAT)) OVER (
                PARTITION BY control_level
                ORDER BY run_date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) AS rolling_pass_rate
        FROM qc_results
        WHERE site = ? AND assay = ?
        ORDER BY control_level, run_date
    """
    conn = get_connection()
    df = pd.read_sql(query, conn, params=[site, assay])
    conn.close()
    return df


def worst_performing_combinations(min_runs=50, limit=5):
    """
    Ranks site/assay combinations by pass rate using a HAVING clause to
    exclude low-volume combinations, then a self-join style comparison
    against the overall average pass rate.
    """
    query = """
        WITH site_assay_stats AS (
            SELECT
                site,
                assay,
                COUNT(*) AS n_runs,
                AVG(in_range) AS pass_rate
            FROM qc_results
            GROUP BY site, assay
            HAVING COUNT(*) >= ?
        ),
        overall AS (
            SELECT AVG(in_range) AS overall_pass_rate FROM qc_results
        )
        SELECT
            s.site,
            s.assay,
            s.n_runs,
            ROUND(s.pass_rate * 100, 2) AS pass_rate_pct,
            ROUND(o.overall_pass_rate * 100, 2) AS overall_pass_rate_pct,
            ROUND((s.pass_rate - o.overall_pass_rate) * 100, 2) AS pct_pts_below_average
        FROM site_assay_stats s
        CROSS JOIN overall o
        ORDER BY s.pass_rate ASC
        LIMIT ?
    """
    conn = get_connection()
    df = pd.read_sql(query, conn, params=[min_runs, limit])
    conn.close()
    return df


if __name__ == "__main__":
    print("Summary by site/assay:")
    print(summary_by_site_assay().head())
    print("\nWorst performing combinations:")
    print(worst_performing_combinations())
