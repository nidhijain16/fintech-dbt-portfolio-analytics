-- Mart Model: fct_portfolio_performance
-- Computes cumulative positions, running cash balance, and historical price movements
-- using senior-level SQL Window Functions.

with trades as (
    select * from {{ ref('stg_trades') }}
),

users as (
    select * from {{ ref('stg_users') }}
),

windowed_metrics as (
    select
        t.trade_id,
        t.user_id,
        u.email,
        u.plan_tier,
        u.is_prime_subscriber,
        t.ticker,
        t.side,
        t.shares,
        t.price_eur,
        t.fee_eur,
        t.gross_amount_eur,
        t.cash_flow_eur,
        t.exchange,
        t.executed_at,

        -- 1. Sequential Trade Counter per user
        row_number() over (
            partition by t.user_id 
            order by t.executed_at asc
        ) as user_trade_sequence,

        -- 2. Cumulative Share Position in this specific ticker
        sum(t.share_delta) over (
            partition by t.user_id, t.ticker 
            order by t.executed_at asc
            rows between unbounded preceding and current row
        ) as cumulative_shares_held,

        -- 3. Running Net Cash Balance Impact for the user across all trades
        sum(t.cash_flow_eur) over (
            partition by t.user_id 
            order by t.executed_at asc
            rows between unbounded preceding and current row
        ) as running_cash_balance_impact_eur,

        -- 4. Previous Trade Execution Price for this ticker (to track price trend)
        lag(t.price_eur, 1) over (
            partition by t.user_id, t.ticker 
            order by t.executed_at asc
        ) as prev_execution_price_eur,

        -- 5. Cumulative Total Trading Volume (Gross EUR) for the user
        sum(t.gross_amount_eur) over (
            partition by t.user_id 
            order by t.executed_at asc
            rows between unbounded preceding and current row
        ) as cumulative_volume_eur

    from trades t
    inner join users u on t.user_id = u.user_id
),

final_calculations as (
    select
        *,
        -- Price differential compared to previous trade execution
        case
            when prev_execution_price_eur is not null 
            then round(price_eur - prev_execution_price_eur, 4)
            else 0.0
        end as price_change_since_prev_trade_eur
    from windowed_metrics
)

select * from final_calculations
order by user_id, executed_at asc
