"""Upsert parsed arXiv Paper objects into Postgres."""
from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

from ingestion.arxiv_client import Paper


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "research_pulse"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", "postgres"),
    )


def upsert_papers(papers: list[Paper], conn=None) -> tuple[int, int]:
    """
    Insert papers + authors, skipping ones we've already ingested (by arxiv_id).
    Returns (pulled_count, new_count).
    """
    own_conn = conn is None
    conn = conn or get_conn()
    new_count = 0
    try:
        with conn:
            with conn.cursor() as cur:
                for paper in papers:
                    cur.execute(
                        """
                        INSERT INTO raw_papers
                            (arxiv_id, title, abstract, primary_category,
                             categories, published_date, updated_date, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (arxiv_id) DO NOTHING
                        RETURNING paper_id
                        """,
                        (
                            paper.arxiv_id,
                            paper.title,
                            paper.abstract,
                            paper.primary_category,
                            paper.categories,
                            paper.published_date,
                            paper.updated_date,
                            paper.source,
                        ),
                    )
                    row = cur.fetchone()
                    if row is None:
                        continue  # already ingested, skip author links too
                    new_count += 1
                    paper_id = row[0]

                    for position, name in enumerate(paper.authors):
                        cur.execute(
                            """
                            INSERT INTO authors (name) VALUES (%s)
                            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                            RETURNING author_id
                            """,
                            (name,),
                        )
                        author_id = cur.fetchone()[0]
                        cur.execute(
                            """
                            INSERT INTO paper_authors (paper_id, author_id, author_position)
                            VALUES (%s, %s, %s)
                            ON CONFLICT DO NOTHING
                            """,
                            (paper_id, author_id, position),
                        )
    finally:
        if own_conn:
            conn.close()

    return len(papers), new_count


def log_ingestion(source: str, query: str, pulled: int, new: int, conn=None) -> None:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingestion_log (source, query, records_pulled, records_new)
                VALUES (%s, %s, %s, %s)
                """,
                (source, query, pulled, new),
            )
    finally:
        if own_conn:
            conn.close()
