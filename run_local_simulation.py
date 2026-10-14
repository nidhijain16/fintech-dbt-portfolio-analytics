#!/usr/bin/env python3
"""
Zero-Dependency dbt & SQL Transformation Engine Simulator
---------------------------------------------------------
This script emulates dbt Core running against an analytical warehouse (DuckDB/BigQuery/Snowflake)
using Python's built-in sqlite3.

It proves and executes:
1. Seed ingestion (raw_users, raw_trades).
2. Staging model transformations (stg_users, stg_trades).
3. Analytics Mart generation with SQL Window Functions (fct_portfolio_performance).
4. Automated schema and data quality tests (unique, not_null, accepted_values).
"""

import csv
import os
import sqlite3
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEDS_DIR = os.path.join(BASE_DIR, "seeds")


def load_csv(filepath):
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def main():
    print("=" * 80)
    print("🚀 STARTING DBT CORE SIMULATION: SCALABLE CAPITAL ANALYTICS")
    print("=" * 80)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Step 1: Ingest Seeds
    print("\n[Step 1/4] 📥 Ingesting dbt Seeds (raw_users, raw_trades)...")

    # Ingest users
    users_data = load_csv(os.path.join(SEEDS_DIR, "raw_users.csv"))
    cursor.execute("""
        CREATE TABLE raw_users (
            user_id TEXT,
            email TEXT,
            kyc_status TEXT,
            plan_tier TEXT,
            created_at TEXT
        );
    """)
    for r in users_data:
        cursor.execute(
            "INSERT INTO raw_users VALUES (?, ?, ?, ?, ?)",
            (r["user_id"], r["email"], r["kyc_status"], r["plan_tier"], r["created_at"])
        )
    print(f"  ✓ Loaded {len(users_data)} records into raw_users.")

    # Ingest trades
    trades_data = load_csv(os.path.join(SEEDS_DIR, "raw_trades.csv"))
    cursor.execute("""
        CREATE TABLE raw_trades (
            trade_id TEXT,
            user_id TEXT,
            ticker TEXT,
            side TEXT,
            shares INTEGER,
            price_eur REAL,
            fee_eur REAL,
            exchange TEXT,
            executed_at TEXT
        );
    """)
    for r in trades_data:
        cursor.execute(
            "INSERT INTO raw_trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r["trade_id"],
                r["user_id"],
                r["ticker"],
                r["side"],
                int(r["shares"]),
                float(r["price_eur"]),
                float(r["fee_eur"]),
                r["exchange"],
                r["executed_at"]
            )
        )
    print(f"  ✓ Loaded {len(trades_data)} records into raw_trades.")

    # Step 2: Build Staging Views (ref('stg_users'), ref('stg_trades'))
    print("\n[Step 2/4] 🔨 Materializing Staging Views...")

    cursor.execute("""
        CREATE VIEW stg_users AS
        SELECT
            user_id,
            lower(trim(email)) as email,
            upper(trim(kyc_status)) as kyc_status,
            upper(trim(plan_tier)) as plan_tier,
            created_at as user_created_at,
            CASE WHEN upper(trim(plan_tier)) IN ('PRIME', 'PRIME_PLUS') THEN 1 ELSE 0 END AS is_prime_subscriber
        FROM raw_users;
    """)
    print("  ✓ Created view: stg_users")

    cursor.execute("""
        CREATE VIEW stg_trades AS
        SELECT
            trade_id,
            user_id,
            upper(trim(ticker)) as ticker,
            upper(trim(side)) as side,
            shares,
            round(price_eur, 4) as price_eur,
            round(fee_eur, 2) as fee_eur,
            upper(trim(exchange)) as exchange,
            executed_at,
            round(shares * price_eur, 2) as gross_amount_eur,
            CASE
                WHEN upper(trim(side)) = 'BUY' THEN shares
                WHEN upper(trim(side)) = 'SELL' THEN -shares
                ELSE 0
            END as share_delta,
            CASE
                WHEN upper(trim(side)) = 'BUY' THEN -round((shares * price_eur) + fee_eur, 2)
                WHEN upper(trim(side)) = 'SELL' THEN round((shares * price_eur) - fee_eur, 2)
                ELSE 0.0
            END as cash_flow_eur
        FROM raw_trades;
    """)
    print("  ✓ Created view: stg_trades")

    # Step 3: Materialize Mart Model (fct_portfolio_performance)
    print("\n[Step 3/4] 📊 Materializing Mart Table with Advanced SQL Window Functions...")

    cursor.execute("""
        CREATE TABLE fct_portfolio_performance AS
        WITH windowed_metrics AS (
            SELECT
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
                ROW_NUMBER() OVER (
                    PARTITION BY t.user_id 
                    ORDER BY t.executed_at ASC
                ) as user_trade_sequence,

                -- 2. Cumulative Share Position in this specific ticker
                SUM(t.share_delta) OVER (
                    PARTITION BY t.user_id, t.ticker 
                    ORDER BY t.executed_at ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as cumulative_shares_held,

                -- 3. Running Net Cash Balance Impact for the user
                SUM(t.cash_flow_eur) OVER (
                    PARTITION BY t.user_id 
                    ORDER BY t.executed_at ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as running_cash_balance_impact_eur,

                -- 4. Previous Trade Execution Price for this ticker (Price Trend)
                LAG(t.price_eur, 1) OVER (
                    PARTITION BY t.user_id, t.ticker 
                    ORDER BY t.executed_at ASC
                ) as prev_execution_price_eur,

                -- 5. Cumulative Total Trading Volume (Gross EUR)
                SUM(t.gross_amount_eur) OVER (
                    PARTITION BY t.user_id 
                    ORDER BY t.executed_at ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as cumulative_volume_eur

            FROM stg_trades t
            INNER JOIN stg_users u ON t.user_id = u.user_id
        )
        SELECT
            *,
            CASE
                WHEN prev_execution_price_eur IS NOT NULL
                THEN round(price_eur - prev_execution_price_eur, 4)
                ELSE 0.0
            END as price_change_since_prev_trade_eur
        FROM windowed_metrics
        ORDER BY user_id, executed_at ASC;
    """)
    print("  ✓ Created table: fct_portfolio_performance")

    # Step 4: Run Automated dbt Schema Tests
    print("\n[Step 4/4] 🧪 Executing Automated Schema & Data Quality Tests...")

    # Test 1: Unique trade_id in fct_portfolio_performance
    cursor.execute("""
        SELECT trade_id, COUNT(*)
        FROM fct_portfolio_performance
        GROUP BY trade_id
        HAVING COUNT(*) > 1;
    """)
    duplicate_trades = cursor.fetchall()
    assert len(duplicate_trades) == 0, f"Schema Test Failed: Found duplicates in trade_id: {duplicate_trades}"
    print("  ✓ [PASS] test_unique_fct_portfolio_performance_trade_id")

    # Test 2: Not null checks
    cursor.execute("""
        SELECT COUNT(*) FROM fct_portfolio_performance
        WHERE trade_id IS NULL OR user_id IS NULL OR cumulative_shares_held IS NULL;
    """)
    null_count = cursor.fetchone()[0]
    assert null_count == 0, "Schema Test Failed: Found unexpected NULL values"
    print("  ✓ [PASS] test_not_null_fct_portfolio_performance_core_columns")

    # Test 3: Accepted values on side
    cursor.execute("""
        SELECT DISTINCT side FROM stg_trades WHERE side NOT IN ('BUY', 'SELL');
    """)
    invalid_sides = cursor.fetchall()
    assert len(invalid_sides) == 0, f"Schema Test Failed: Invalid trade side found: {invalid_sides}"
    print("  ✓ [PASS] test_accepted_values_stg_trades_side")

    # Test 4: Financial Sanity - cumulative shares should never be negative
    cursor.execute("""
        SELECT COUNT(*) FROM fct_portfolio_performance WHERE cumulative_shares_held < 0;
    """)
    negative_shares = cursor.fetchone()[0]
    assert negative_shares == 0, "Business Rule Test Failed: User shorted stock without authorization!"
    print("  ✓ [PASS] test_no_negative_cumulative_shares (Fintech Business Rule)")

    # Print Table Preview
    print("\n" + "=" * 110)
    print("📈 FINAL ANALYTICS MART PREVIEW: fct_portfolio_performance")
    print("=" * 110)

    cursor.execute("""
        SELECT
            trade_id,
            user_id,
            ticker,
            side,
            shares,
            price_eur,
            cumulative_shares_held,
            running_cash_balance_impact_eur,
            price_change_since_prev_trade_eur,
            cumulative_volume_eur
        FROM fct_portfolio_performance;
    """)
    rows = cursor.fetchall()

    headers = [
        "Trade ID", "User", "Ticker", "Side", "Qty", "Price(€)",
        "Cumul.Shares", "Running Cash Impact(€)", "Δ Price", "Total Volume(€)"
    ]
    format_template = "{:<10} {:<9} {:<9} {:<6} {:<5} {:<10} {:<13} {:<24} {:<10} {:<15}"
    print(format_template.format(*headers))
    print("-" * 110)

    for row in rows:
        formatted_row = [
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3]),
            str(row[4]),
            f"{row[5]:.2f}",
            str(row[6]),
            f"{row[7]:.2f}",
            f"{row[8]:.2f}",
            f"{row[9]:.2f}"
        ]
        print(format_template.format(*formatted_row))

    print("=" * 110)
    print("✅ All transformations, window calculations, and dbt tests verified successfully!\n")
    conn.close()


if __name__ == "__main__":
    main()
