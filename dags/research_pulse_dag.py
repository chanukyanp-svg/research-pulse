"""
Airflow DAG for the Research Pulse pipeline.

Task graph:
    ingest_arxiv  →  enrich_s2
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _ingest_task() -> None:
    from scripts.run_ingest import DEFAULT_QUERIES, run
    run(queries=DEFAULT_QUERIES, max_results=200)


def _enrich_task() -> None:
    from enrichment.enrich import run_enrichment
    run_enrichment(batch_size=100, max_papers=10_000, fetch_edges=False)


with DAG(
    "research_pulse_dag",
    default_args=default_args,
    description="Research Pulse: arXiv ingestion → S2 citation enrichment",
    schedule=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["research", "arxiv", "s2", "neurotech", "quantum"],
) as dag:

    ingest_arxiv = PythonOperator(
        task_id="ingest_arxiv",
        python_callable=_ingest_task,
    )

    enrich_s2 = PythonOperator(
        task_id="enrich_s2",
        python_callable=_enrich_task,
    )

    ingest_arxiv >> enrich_s2