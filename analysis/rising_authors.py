"""
Rising author detection based on publication velocity.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import psycopg2


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "research_pulse"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", "postgres"),
    )


def detect_rising_authors(
    conn, lookback_months: int = 6, min_recent_papers: int = 2
) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH author_history AS (
                SELECT 
                    a.author_id,
                    a.name,
                    COUNT(*) FILTER (WHERE p.published_date >= NOW() - INTERVAL '12 months') AS papers_12m,
                    COUNT(*) FILTER (WHERE p.published_date >= NOW() - INTERVAL '%s months') AS papers_recent,
                    COUNT(*) AS total_papers,
                    MIN(p.published_date) AS first_paper,
                    MAX(p.published_date) AS last_paper,
                    AVG(p.citation_count) AS avg_citations
                FROM authors a
                JOIN paper_authors pa ON a.author_id = pa.author_id
                JOIN raw_papers p ON pa.paper_id = p.paper_id
                GROUP BY a.author_id, a.name
                HAVING COUNT(*) >= 2
            )
            SELECT 
                author_id,
                name,
                papers_12m,
                papers_recent,
                total_papers,
                first_paper,
                last_paper,
                avg_citations,
                CASE 
                    WHEN total_papers > 2 AND papers_recent >= %s THEN 
                        ROUND(papers_recent::numeric / NULLIF(total_papers - papers_recent, 0), 2)
                    ELSE 0 
                END AS velocity_ratio
            FROM author_history
            WHERE papers_recent >= %s
            ORDER BY velocity_ratio DESC, papers_recent DESC
            LIMIT 50
            """,
            (lookback_months, min_recent_papers, min_recent_papers),
        )

        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def save_rising_authors(authors: list[dict], conn) -> None:
    with conn.cursor() as cur:
        for a in authors:
            cur.execute(
                """
                INSERT INTO rising_authors 
                (author_id, name, papers_12m, papers_recent, total_papers, 
                 first_paper, last_paper, avg_citations, velocity_ratio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (author_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    papers_12m = EXCLUDED.papers_12m,
                    papers_recent = EXCLUDED.papers_recent,
                    total_papers = EXCLUDED.total_papers,
                    first_paper = EXCLUDED.first_paper,
                    last_paper = EXCLUDED.last_paper,
                    avg_citations = EXCLUDED.avg_citations,
                    velocity_ratio = EXCLUDED.velocity_ratio,
                    computed_at = now()
                """,
                (
                    a["author_id"],
                    a["name"],
                    a["papers_12m"],
                    a["papers_recent"],
                    a["total_papers"],
                    a["first_paper"],
                    a["last_paper"],
                    a["avg_citations"],
                    a["velocity_ratio"],
                ),
            )
        conn.commit()


def export_csv(authors: list[dict], path: str = "analysis/rising_authors.csv") -> None:
    if not authors:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=authors[0].keys())
        writer.writeheader()
        writer.writerows(authors)


def run_rising_authors(
    lookback_months: int = 6, min_recent_papers: int = 2, export: bool = False
) -> None:
    conn = get_conn()
    try:
        print(
            f"Detecting rising authors (last {lookback_months} months, min {min_recent_papers} papers)..."
        )
        authors = detect_rising_authors(conn, lookback_months, min_recent_papers)
        print(f"Found {len(authors)} rising authors")

        if authors:
            save_rising_authors(authors, conn)
            if export:
                export_csv(authors)
                print("Exported to analysis/rising_authors.csv")
            print(
                f"Top rising author: {authors[0]['name']} (velocity_ratio={authors[0]['velocity_ratio']})"
            )
        else:
            print("No rising authors detected with current thresholds.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lookback-months", type=int, default=6)
    parser.add_argument("--min-recent-papers", type=int, default=2)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()

    try:
        run_rising_authors(
            lookback_months=args.lookback_months,
            min_recent_papers=args.min_recent_papers,
            export=args.export,
        )
    except Exception as e:
        print(f"Rising author detection failed: {e}", file=sys.stderr)
        sys.exit(1)