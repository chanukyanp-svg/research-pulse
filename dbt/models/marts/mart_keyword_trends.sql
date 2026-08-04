with keywords as (
    select * from {{ ref('int_paper_keywords') }}
)

select
    keyword,
    date_trunc('week', published_date) as trend_week,
    date_trunc('month', published_date) as trend_month,
    count(*) as paper_count

from keywords

group by keyword, date_trunc('week', published_date), date_trunc('month', published_date)