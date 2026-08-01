# Research Pulse Tracker

An end-to-end analytics pipeline that tracks research trends in a chosen field
(seeded here with BCI/neurotech + quantum ML) by ingesting papers from arXiv,
modeling them in a warehouse, and surfacing trend and citation-network insights.

**Status: Week 1 of 4.** This slice covers arXiv ingestion → Postgres → one dbt
staging model → a static trend chart. Airflow scheduling, Semantic Scholar
citation enrichment, centrality analysis, and the interactive dashboard land
in later weeks (see [Roadmap](#roadmap)).

## Architecture (target end-state)

```
arXiv API ─┐
           ├─▶ Ingest (Airflow) ─▶ Postgres ─▶ dbt ─▶ Analysis (networkx) ─▶ Dashboard (Streamlit)
S2 API ────┘
```

## What's working right now

- `ingestion/arxiv_client.py` — queries arXiv's public Atom API, parses entries into `Paper` objects
- `ingestion/load.py` — upserts papers/authors into Postgres, deduping on `arxiv_id`
- `scripts/run_ingest.py` — CLI to pull a set of seed queries and load them
- `dbt/models/staging/stg_arxiv_papers.sql` — cleaned staging view with week/month rollup columns
- `analysis/trend_chart.py` — static matplotlib chart of papers/week by category
- `tests/test_arxiv_client.py` — parser tests run against a saved fixture (no network needed)

## Setup

1. **Start Postgres**
   ```bash
   docker compose up -d
   ```
   This also runs `sql/schema.sql` automatically on first boot. If you ever
   need to re-apply it manually:
   ```bash
   docker exec -i research_pulse_pg psql -U postgres -d research_pulse < sql/schema.sql
   ```

2. **Install dependencies**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   export $(cat .env | xargs)
   ```

4. **Set up dbt**
   ```bash
   mkdir -p ~/.dbt
   cp dbt/profiles.yml.example ~/.dbt/profiles.yml
   cd dbt && dbt debug   # should say "All checks passed!"
   ```

## Running the pipeline

```bash
# 1. Pull papers from arXiv and load into Postgres
python -m scripts.run_ingest

# 2. Build the dbt staging model
cd dbt && dbt run && dbt test && cd ..

# 3. Generate the trend chart
python -m analysis.trend_chart --out charts/trend.png
```

Edit `DEFAULT_QUERIES` in `scripts/run_ingest.py` to retarget the tracker at
a different field — the arXiv query grammar (field prefixes, `AND`/`OR`,
phrase quoting) is documented in
[arXiv's API user manual](https://info.arxiv.org/help/api/user-manual.html#query_details).

## Running tests

```bash
PYTHONPATH=. pytest tests/
```

The parser tests run against `tests/fixtures/sample_response.xml`, a saved
real arXiv API response shape, so they don't depend on network access.

## Design notes

- **Why upsert on `arxiv_id` instead of a full replace-load?** Papers get
  revised (new versions) but we want stable identity for trend analysis over
  time; landing table is additive, not append-only-with-duplicates.
- **Why a dbt view, not a table, for staging?** No data volume pressure yet
  at this stage — views keep the staging layer always-fresh without an extra
  build step. This will likely switch to `table` materialization once the
  intermediate/marts layer in Week 3 starts joining across it repeatedly.
- **Why arXiv before Semantic Scholar?** arXiv has no rate-limit friction and
  no key requirement, so it's the fastest path to a working v0. Semantic
  Scholar is layered in next for citation edges and enrichment.

## Roadmap

- **Week 2** — Airflow DAG for scheduled ingestion; Semantic Scholar
  enrichment (citation counts, citation edges)
- **Week 3** — dbt intermediate/marts models (keyword co-occurrence, author
  rollups); `networkx`-based centrality and rising-author detection
- **Week 4** — Streamlit dashboard with interactive citation graph; Docker
  Compose for the full stack; architecture diagram
