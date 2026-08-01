"""
Week 1 entrypoint: pull papers for a set of seed queries and load into Postgres.

Usage:
    python -m scripts.run_ingest
    python -m scripts.run_ingest --query 'cat:quant-ph AND abs:"quantum machine learning"' --max-results 200

Run schema.sql once first:
    psql "$DATABASE_URL" -f sql/schema.sql
"""
from __future__ import annotations

import argparse
import sys

from ingestion.arxiv_client import fetch_all
from ingestion.load import get_conn, log_ingestion, upsert_papers

# Seed queries for the BCI / neurotech niche. Edit or extend this list to
# retarget the tracker at a different field.
DEFAULT_QUERIES = [
    'cat:q-bio.NC AND abs:EEG',
    'abs:"brain-computer interface"',
    'abs:fNIRS AND abs:EEG',
    'cat:quant-ph AND abs:"quantum machine learning"',
    'abs:"quantum neural network"',
]


def run(queries: list[str], max_results: int) -> None:
    conn = get_conn()
    try:
        for query in queries:
            print(f"Fetching: {query!r}")
            papers = fetch_all(query, max_total=max_results)
            pulled, new = upsert_papers(papers, conn=conn)
            log_ingestion("arxiv", query, pulled, new, conn=conn)
            print(f"  pulled={pulled} new={new}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", dest="queries", default=None,
                         help="arXiv search query; can be passed multiple times. "
                              "Defaults to the seed BCI/quantum ML query list.")
    parser.add_argument("--max-results", type=int, default=200)
    args = parser.parse_args()

    try:
        run(args.queries or DEFAULT_QUERIES, args.max_results)
    except Exception as e:  # noqa: BLE001
        print(f"Ingestion failed: {e}", file=sys.stderr)
        sys.exit(1)
