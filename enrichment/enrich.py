"""
Idempotent orchestrator: pull S2 metadata + citation edges for papers that
haven't been enriched yet.

Usage:
    python -m enrichment.enrich
    python -m enrichment.enrich --fetch-edges --max-papers 500
"""
from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras

from enrichment.s2_client import fetch_citations, fetch_paper_details, fetch_references


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "research_pulse"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", "postgres"),
    )


def _get_papers_to_enrich(conn, batch_size: int = 100) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT paper_id, arxiv_id
            FROM raw_papers
            WHERE s2_enriched_at IS NULL
            ORDER BY paper_id
            LIMIT %s
            """,
            (batch_size,),
        )
        return cur.fetchall()


def _resolve_paper_id(
    cur, s2_id: str | None = None, arxiv_id: str | None = None
) -> int | None:
    if arxiv_id:
        cur.execute("SELECT paper_id FROM raw_papers WHERE arxiv_id = %s", (arxiv_id,))
        row = cur.fetchone()
        if row:
            return row[0]
    if s2_id:
        cur.execute("SELECT paper_id FROM raw_papers WHERE s2_id = %s", (s2_id,))
        row = cur.fetchone()
        if row:
            return row[0]
    return None


def _store_citation_edges(cur, paper_id: int, s2_id: str, fetch_edges: bool) -> None:
    if not fetch_edges or not s2_id:
        return

    citations = fetch_citations(s2_id, limit=100)
    references = fetch_references(s2_id, limit=100)

    edges: list[tuple[int, int]] = []

    for edge in citations:
        citing_id = _resolve_paper_id(cur, s2_id=edge.citing_s2_id, arxiv_id=edge.arxiv_id)
        if citing_id:
            edges.append((citing_id, paper_id))

    for edge in references:
        cited_id = _resolve_paper_id(cur, s2_id=edge.cited_s2_id, arxiv_id=edge.arxiv_id)
        if cited_id:
            edges.append((paper_id, cited_id))

    if edges:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO paper_citations (citing_paper_id, cited_paper_id)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            edges,
        )


def _enrich_batch(
    papers: list[dict], conn, fetch_edges: bool
) -> tuple[int, int, int]:
    arxiv_ids = [p["arxiv_id"] for p in papers]
    s2_papers = fetch_paper_details(arxiv_ids)
    s2_by_arxiv = {p.arxiv_id: p for p in s2_papers}

    processed = len(papers)
    enriched = 0
    failed = 0

    with conn.cursor() as cur:
        for paper in papers:
            s2 = s2_by_arxiv.get(paper["arxiv_id"])

            if s2:
                cur.execute(
                    """
                    UPDATE raw_papers
                    SET s2_id = %s,
                        citation_count = %s,
                        reference_count = %s,
                        s2_enriched_at = now()
                    WHERE paper_id = %s
                    """,
                    (s2.s2_id, s2.citation_count, s2.reference_count, paper["paper_id"]),
                )
                enriched += 1
                _store_citation_edges(cur, paper["paper_id"], s2.s2_id, fetch_edges)
            else:
                cur.execute(
                    """
                    UPDATE raw_papers
                    SET s2_enriched_at = now()
                    WHERE paper_id = %s
                    """,
                    (paper["paper_id"],),
                )
                failed += 1

    conn.commit()
    return processed, enriched, failed


def log_enrichment(
    source: str,
    processed: int,
    enriched: int,
    failed: int,
    conn=None,
) -> None:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO enrichment_log
                (source, records_processed, records_enriched, records_failed)
                VALUES (%s, %s, %s, %s)
                """,
                (source, processed, enriched, failed),
            )
    finally:
        if own_conn:
            conn.close()


def run_enrichment(
    batch_size: int = 100,
    max_papers: int = 10_000,
    fetch_edges: bool = False,
) -> None:
    conn = get_conn()
    try:
        total_processed = 0
        total_enriched = 0
        total_failed = 0

        while total_processed < max_papers:
            papers = _get_papers_to_enrich(conn, batch_size)
            if not papers:
                print("No more papers to enrich.")
                break

            processed, enriched, failed = _enrich_batch(papers, conn, fetch_edges)
            total_processed += processed
            total_enriched += enriched
            total_failed += failed

            print(
                f"Batch: processed={processed}, enriched={enriched}, failed={failed} "
                f"(running totals: {total_processed}/{total_enriched}/{total_failed})"
            )

        log_enrichment(
            "semantic_scholar",
            total_processed,
            total_enriched,
            total_failed,
            conn=conn,
        )
        print(
            f"Enrichment complete: {total_processed} processed, "
            f"{total_enriched} enriched, {total_failed} not found in S2."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-papers", type=int, default=10_000)
    parser.add_argument(
        "--fetch-edges",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()

    try:
        run_enrichment(
            batch_size=args.batch_size,
            max_papers=args.max_papers,
            fetch_edges=args.fetch_edges,
        )
    except Exception as e:
        print(f"Enrichment failed: {e}", file=sys.stderr)
        sys.exit(1)
        