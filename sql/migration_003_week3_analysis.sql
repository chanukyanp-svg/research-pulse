-- Week 3 migration: analysis output tables for centrality and rising authors.

-- ---------------------------------------------------------------------------
-- 1. Paper centrality scores (populated by analysis/centrality.py)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paper_centrality (
    paper_id INTEGER PRIMARY KEY REFERENCES raw_papers(paper_id) ON DELETE CASCADE,
    arxiv_id TEXT,
    title TEXT,
    pagerank NUMERIC,
    betweenness NUMERIC,
    in_degree INTEGER,
    out_degree INTEGER,
    computed_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_paper_centrality_pagerank ON paper_centrality(pagerank DESC);

-- ---------------------------------------------------------------------------
-- 2. Rising authors (populated by analysis/rising_authors.py)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rising_authors (
    author_id INTEGER PRIMARY KEY REFERENCES authors(author_id) ON DELETE CASCADE,
    name TEXT,
    papers_12m INTEGER,
    papers_recent INTEGER,
    total_papers INTEGER,
    first_paper TIMESTAMP,
    last_paper TIMESTAMP,
    avg_citations NUMERIC,
    velocity_ratio NUMERIC,
    computed_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rising_authors_velocity ON rising_authors(velocity_ratio DESC);