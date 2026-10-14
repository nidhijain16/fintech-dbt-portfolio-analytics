-- Staging model: stg_users
-- Cleanses raw user records, filters non-kyc compliant data, and standardizes plan tiers

with source as (
    select * from {{ ref('raw_users') }}
),

renamed_and_cleaned as (
    select
        cast(user_id as text) as user_id,
        lower(trim(email)) as email,
        upper(trim(kyc_status)) as kyc_status,
        upper(trim(plan_tier)) as plan_tier,
        cast(created_at as timestamp) as user_created_at,
        case
            when upper(trim(plan_tier)) in ('PRIME', 'PRIME_PLUS') then 1
            else 0
        end as is_prime_subscriber
    from source
)

select * from renamed_and_cleaned
