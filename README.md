# dbt Core & Advanced SQL Data Engineering
 
> **Target Mastery:** dbt Core (models, macros, `ref()`, DAG lineage, schema testing), Kimball Data Modeling (Staging vs Marts), and Senior-Level SQL Window Functions.

---

## 🏛️ Data Architecture & Lineage (DAG)

```mermaid
graph LR
    subgraph Sources["Raw Ingestion Layer (EL)"]
        R1["raw_users (CSV/Kafka)"]
        R2["raw_trades (CSV/Kafka)"]
    end

    subgraph Staging["Staging Layer (Views)"]
        S1["stg_users\n- Cast IDs & Timestamps\n- Standardize KYC status\n- Segment subscription tiers"]
        S2["stg_trades\n- Standardize ticker symbols\n- Compute share delta (+/-)\n- Calculate net cash flow"]
    end

    subgraph Marts["Analytics Marts Layer (Tables)"]
        M1["fct_portfolio_performance\n- Sequential Trade Sequence (ROW_NUMBER)\n- Cumulative Asset Holdings (SUM OVER)\n- Running Cash Balance (SUM OVER)\n- Price Drift Analysis (LAG)"]
    end

    R1 --> S1
    R2 --> S2
    S1 -->|ref('stg_users')| M1
    S2 -->|ref('stg_trades')| M1
```

---

## 🗂️ Dimensional Layering Strategy

| Layer | Model | Materialization | Design Principles & Responsibilities |
| :--- | :--- | :--- | :--- |
| **Staging** | `stg_users` | `view` | 1-to-1 with raw source. Enforces strict type casting, lowercases emails, cleans string whitespace, and maps subscription tiers (`PRIME`, `FREE`). |
| **Staging** | `stg_trades` | `view` | Normalizes trade executions. Derives positive/negative `share_delta` based on order side (`BUY`/`SELL`) and computes investor `cash_flow_eur` including venue fees. |
| **Marts** | `fct_portfolio_performance` | `table` | Business fact table. Combines users and trades to calculate cumulative holdings, running cash balances, and tick-by-tick price deltas without collapsing individual transaction granularity. |

---

## 🪟 Advanced SQL Window Function Engine

The fact table [`fct_portfolio_performance.sql`](file:///c:/Users/patni/OneDrive/Documents/GitHub/New%20skills/sprint_projects/02_dbt_fintech/models/marts/fct_portfolio_performance.sql) leverages window functions with precise partitioning and framing:

```sql
-- 1. Sequential Trade Counter per Investor
ROW_NUMBER() OVER (
    PARTITION BY t.user_id 
    ORDER BY t.executed_at ASC
) as user_trade_sequence,

-- 2. Cumulative Share Holding per Asset (Handles BUY additions & SELL subtractions)
SUM(t.share_delta) OVER (
    PARTITION BY t.user_id, t.ticker 
    ORDER BY t.executed_at ASC
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) as cumulative_shares_held,

-- 3. Running Net Cash Balance Impact (Outflows for purchases, inflows for sales)
SUM(t.cash_flow_eur) OVER (
    PARTITION BY t.user_id 
    ORDER BY t.executed_at ASC
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) as running_cash_balance_impact_eur,

-- 4. Historical Execution Price Comparison (Price Drift)
LAG(t.price_eur, 1) OVER (
    PARTITION BY t.user_id, t.ticker 
    ORDER BY t.executed_at ASC
) as prev_execution_price_eur
```

---

## 🧪 Automated Data Quality & Schema Testing

Every model is covered by automated schema tests defined in `schema.yml` contracts:

* **Uniqueness & Non-Null:** Primary keys (`user_id`, `trade_id`) are verified unique and non-null.
* **Referential Integrity:** `stg_trades.user_id` strictly references `stg_users.user_id`.
* **Accepted Values:** `side` is constrained to `['BUY', 'SELL']`; `plan_tier` constrained to `['FREE', 'PRIME', 'PRIME_PLUS']`.
* **Financial Invariant Assertions:** Validates that retail investor `cumulative_shares_held` never drops below zero (prevention of unauthorized short selling).

---

## 🚀 Quickstart & Local Execution

This repository includes a standalone simulation runner using Python's built-in `sqlite3` to materialize models and validate assertions without requiring an external cloud data warehouse:

```bash
# Execute transformations and run schema tests
python run_local_simulation.py
```

### Expected Output
```
================================================================================
🚀 STARTING DBT CORE SIMULATION: FINTECH ANALYTICS
================================================================================
[Step 1/4] Ingesting dbt Seeds (raw_users, raw_trades)...
  ✓ Loaded 4 records into raw_users.
  ✓ Loaded 8 records into raw_trades.

[Step 2/4] Materializing Staging Views...
  ✓ Created view: stg_users
  ✓ Created view: stg_trades

[Step 3/4] Materializing Mart Table with Advanced SQL Window Functions...
  ✓ Created table: fct_portfolio_performance

[Step 4/4] Executing Automated Schema & Data Quality Tests...
  ✓ [PASS] test_unique_fct_portfolio_performance_trade_id
  ✓ [PASS] test_not_null_fct_portfolio_performance_core_columns
  ✓ [PASS] test_accepted_values_stg_trades_side
  ✓ [PASS] test_no_negative_cumulative_shares (Fintech Business Rule)
```

---

## 📂 Project Structure

```
.
├── dbt_project.yml                       # Project configuration, schemas, and materializations
├── models/
│   ├── staging/
│   │   ├── stg_users.sql                 # User account cleansing and tiering
│   │   ├── stg_trades.sql                # Order normalization and cash flow calculation
│   │   └── schema.yml                    # Staging schema definitions and constraints
│   └── marts/
│       ├── fct_portfolio_performance.sql # Core fact table with window calculations
│       └── schema.yml                    # Mart tests and column documentation
├── seeds/
│   ├── raw_users.csv                     # Mock raw account records
│   └── raw_trades.csv                    # Mock multi-venue order execution data
├── run_local_simulation.py               # Standalone execution and validation runner
└── INTERVIEW_STUDY_GUIDE.md              # (Local Study) In-depth SQL & dbt interview scenarios
```
