-- Cleans and lightly reshapes the raw arXiv landing table.
-- One row per paper. Downstream marts (Week 3) will build trend/centrality
-- aggregations on top of this.

with source as (

    select * from {{ source('raw', 'raw_papers') }}

),

renamed as (

    select
        paper_id,
        arxiv_id,
        trim(title)                        as title,
        trim(abstract)                     as abstract,
        primary_category,
        categories,
        published_date,
        updated_date,
        date_trunc('week', published_date) as published_week,
        date_trunc('month', published_date) as published_month,
        source,
        ingested_at

    from source
    where arxiv_id is not null

)

select * from renamed
