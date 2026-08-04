select
    a.author_id,
    a.name as author_name,
    pa.paper_id,
    pa.author_position,
    p.published_date,
    p.published_week,
    p.published_month,
    p.citation_count,
    p.reference_count,
    p.primary_category

from {{ source('raw', 'authors') }} a
inner join {{ source('raw', 'paper_authors') }} pa on a.author_id = pa.author_id
inner join {{ ref('stg_arxiv_papers') }} p on pa.paper_id = p.paper_id