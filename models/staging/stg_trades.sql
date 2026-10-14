-- Staging model: stg_trades
-- Normalizes trade records, derives financial cash-flow and net position deltas

with source as (
    select * from {{ ref('raw_trades') }}
),

renamed_and_enriched as (
    select
        cast(trade_id as text) as trade_id,
        cast(user_id as text) as user_id,
        upper(trim(ticker)) as ticker,
        upper(trim(side)) as side,
        cast(shares as integer) as shares,
        round(cast(price_eur as real), 4) as price_eur,
        round(cast(fee_eur as real), 2) as fee_eur,
        upper(trim(exchange)) as exchange,
        cast(executed_at as timestamp) as executed_at,

        -- Gross trade volume
        round(cast(shares as real) * cast(price_eur as real), 2) as gross_amount_eur,

        -- Share delta: positive for BUY, negative for SELL
        case
            when upper(trim(side)) = 'BUY' then cast(shares as integer)
            when upper(trim(side)) = 'SELL' then -cast(shares as integer)
            else 0
        end as share_delta,

        -- Net cash flow for the investor account (Outflow for BUY + fee, Inflow for SELL - fee)
        case
            when upper(trim(side)) = 'BUY' then -round((cast(shares as real) * cast(price_eur as real)) + cast(fee_eur as real), 2)
            when upper(trim(side)) = 'SELL' then round((cast(shares as real) * cast(price_eur as real)) - cast(fee_eur as real), 2)
            else 0.0
        end as cash_flow_eur
    from source
)

select * from renamed_and_enriched
