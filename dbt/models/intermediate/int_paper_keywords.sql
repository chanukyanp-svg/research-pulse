with source as (
    select * from {{ ref('stg_arxiv_papers') }}
),

categories as (
    select
        paper_id,
        published_date,
        unnest(categories) as keyword
    from source
),

title_terms as (
    select
        paper_id,
        published_date,
        case
            when lower(title) like '%eeg%' then 'EEG'
            when lower(title) like '%fnirs%' then 'fNIRS'
            when lower(title) like '%bci%' or lower(title) like '%brain-computer%' or lower(title) like '%brain computer%' then 'BCI'
            when lower(title) like '%quantum machine learning%' then 'Quantum ML'
            when lower(title) like '%quantum neural%' then 'Quantum NN'
            when lower(title) like '%neurotech%' or lower(title) like '%neurotechnology%' then 'Neurotech'
            else null
        end as keyword
    from source
    where 
        lower(title) like '%eeg%'
        or lower(title) like '%fnirs%'
        or lower(title) like '%bci%'
        or lower(title) like '%brain-computer%'
        or lower(title) like '%brain computer%'
        or lower(title) like '%quantum machine learning%'
        or lower(title) like '%quantum neural%'
        or lower(title) like '%neurotech%'
)

select * from categories
union all
select * from title_terms where keyword is not null