-- Cleans and lightly reshapes the raw arXiv landing table.
-- Now includes S2 enrichment columns (citation_count, reference_count, s2_id).
-- Downstream marts (Week 3) will build trend/centrality aggregations on top.

with source as (

    select * from {{ source('raw', 'raw_papers') }}

),

renamed as (

    select
        paper_id,
        arxiv_id,
        s2_id,
        trim(title) as title,
        trim(abstract) as abstract,
        primary_category,
        categories,
        published_date,
        updated_date,
        citation_count,
        reference_count,
        date_trunc('week', published_date) as published_week,
        date_trunc('month', published_date) as published_month,
        source,
        ingested_at,
        s2_enriched_at

    from source
    where arxiv_id is not null

)

select * from renamed