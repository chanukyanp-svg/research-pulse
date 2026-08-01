"""
Week 1 stand-in for the eventual dashboard: a static matplotlib chart
showing paper volume per week, split by primary_category.

This reads from the dbt staging view (stg_arxiv_papers), so run
`dbt run` before this.

Usage:
    python -m analysis.trend_chart
    python -m analysis.trend_chart --out charts/trend.png
"""
from __future__ import annotations

import argparse
import os

import matplotlib.pyplot as plt
import psycopg2

QUERY = """
    select
        published_week,
        primary_category,
        count(*) as paper_count
    from stg_arxiv_papers
    where published_week is not null
    group by 1, 2
    order by 1
"""


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "research_pulse"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", "postgres"),
    )


def fetch_trend_data():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY)
            return cur.fetchall()
    finally:
        conn.close()


def plot_trend(rows, out_path: str) -> None:
    if not rows:
        raise ValueError(
            "No rows returned from stg_arxiv_papers. "
            "Run scripts/run_ingest.py and dbt run first."
        )

    by_category: dict[str, dict] = {}
    for week, category, count in rows:
        by_category.setdefault(category, {})[week] = count

    fig, ax = plt.subplots(figsize=(10, 6))
    for category, week_counts in sorted(by_category.items()):
        weeks = sorted(week_counts)
        counts = [week_counts[w] for w in weeks]
        ax.plot(weeks, counts, marker="o", label=category)

    ax.set_title("arXiv papers per week by category")
    ax.set_xlabel("Week")
    ax.set_ylabel("Papers published")
    ax.legend(title="Category", loc="upper left", fontsize="small")
    fig.autofmt_xdate()
    fig.tight_layout()

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=150)
    print(f"Saved chart to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="charts/trend.png")
    args = parser.parse_args()

    rows = fetch_trend_data()
    plot_trend(rows, args.out)
