-- Week 1 schema: just enough to land arXiv data.
-- Semantic Scholar enrichment (citations table, s2_id columns) lands in Week 2.

CREATE TABLE IF NOT EXISTS raw_papers (
    paper_id            SERIAL PRIMARY KEY,
    arxiv_id            TEXT UNIQUE NOT NULL,
    title               TEXT NOT NULL,
    abstract            TEXT,
    primary_category    TEXT,
    categories          TEXT[],
    published_date      TIMESTAMP,
    updated_date        TIMESTAMP,
    source              TEXT NOT NULL DEFAULT 'arxiv',
    ingested_at         TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS authors (
    author_id           SERIAL PRIMARY KEY,
    name                TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_authors (
    paper_id            INTEGER REFERENCES raw_papers(paper_id) ON DELETE CASCADE,
    author_id           INTEGER REFERENCES authors(author_id) ON DELETE CASCADE,
    author_position     INTEGER NOT NULL,
    PRIMARY KEY (paper_id, author_id)
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    id                  SERIAL PRIMARY KEY,
    source              TEXT NOT NULL,
    query               TEXT NOT NULL,
    run_at              TIMESTAMP NOT NULL DEFAULT now(),
    records_pulled      INTEGER NOT NULL,
    records_new         INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_papers_published ON raw_papers(published_date);
CREATE INDEX IF NOT EXISTS idx_raw_papers_category ON raw_papers(primary_category);
