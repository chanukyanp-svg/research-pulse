-- Week 2 migration: Semantic Scholar enrichment layer.
-- Run this after Week 1 schema.sql is already applied.

-- ---------------------------------------------------------------------------
-- 1. Extend raw_papers with S2 metadata
-- ---------------------------------------------------------------------------
ALTER TABLE raw_papers
ADD COLUMN IF NOT EXISTS s2_id TEXT,
ADD COLUMN IF NOT EXISTS citation_count INTEGER,
ADD COLUMN IF NOT EXISTS reference_count INTEGER,
ADD COLUMN IF NOT EXISTS s2_enriched_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_raw_papers_s2_id ON raw_papers(s2_id);
CREATE INDEX IF NOT EXISTS idx_raw_papers_s2_enriched ON raw_papers(s2_enriched_at)
    WHERE s2_enriched_at IS NULL;

-- ---------------------------------------------------------------------------
-- 2. Citation edges (many-to-many self-reference on raw_papers)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paper_citations (
    citing_paper_id INTEGER REFERENCES raw_papers(paper_id) ON DELETE CASCADE,
    cited_paper_id  INTEGER REFERENCES raw_papers(paper_id) ON DELETE CASCADE,
    PRIMARY KEY (citing_paper_id, cited_paper_id)
);

CREATE INDEX IF NOT EXISTS idx_paper_citations_cited ON paper_citations(cited_paper_id);

-- ---------------------------------------------------------------------------
-- 3. Enrichment audit log (mirrors ingestion_log pattern)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS enrichment_log (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    run_at TIMESTAMP NOT NULL DEFAULT now(),
    records_processed INTEGER NOT NULL,
    records_enriched INTEGER NOT NULL,
    records_failed INTEGER NOT NULL DEFAULT 0
);