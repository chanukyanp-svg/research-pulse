with in_degree as (
    select
        cited_paper_id as paper_id,
        count(*) as in_degree
    from {{ source('raw', 'paper_citations') }}
    group by cited_paper_id
),

out_degree as (
    select
        citing_paper_id as paper_id,
        count(*) as out_degree
    from {{ source('raw', 'paper_citations') }}
    group by citing_paper_id
)

select
    p.paper_id,
    p.arxiv_id,
    p.title,
    p.primary_category,
    p.published_date,
    p.citation_count,
    p.reference_count,
    coalesce(id.in_degree, 0) as in_degree,
    coalesce(od.out_degree, 0) as out_degree,
    coalesce(id.in_degree, 0) + coalesce(od.out_degree, 0) as total_degree

from {{ ref('stg_arxiv_papers') }} p
left join in_degree id on p.paper_id = id.paper_id
left join out_degree od on p.paper_id = od.paper_id