with author_papers as (
    select * from {{ ref('int_author_papers') }}
)

select
    author_id,
    author_name,
    count(*) as total_papers,
    sum(citation_count) as total_citations,
    round(avg(citation_count), 2) as avg_citations,
    max(citation_count) as max_citations,
    min(published_date) as first_paper_date,
    max(published_date) as last_paper_date,
    count(*) filter (where published_date >= current_date - interval '12 months') as papers_last_12m,
    count(*) filter (where published_date >= current_date - interval '6 months') as papers_last_6m,
    round(
        count(*) filter (where published_date >= current_date - interval '6 months')::numeric 
        / nullif(count(*) filter (where published_date < current_date - interval '6 months'), 0),
        2
    ) as recent_velocity_ratio

from author_papers

group by author_id, author_name

having count(*) >= 2