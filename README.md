# 📊 Module 2: dbt Core & Advanced SQL Data Engineering

> **Time Commitment:** Hour 3 of the 5-Hour Sprint  
> **Target Mastery:** dbt Core (models, macros, `ref()`, DAG lineage, schema testing), Kimball Data Modeling (Staging vs Marts), and Senior-Level SQL Window Functions.

---

## 📖 1. What is dbt (data build tool)?

**dbt** is the industry-standard transformation framework for modern cloud data warehouses (Snowflake, BigQuery, Databricks, Redshift, DuckDB).

* **The Shift from ETL to ELT:**
  * **Traditional ETL (Extract -> Transform -> Load):** Data was transformed before loading using heavy tools (Informatica, Talend). It was slow and created data bottlenecks.
  * **Modern ELT (Extract -> Load -> Transform):** Raw data is loaded directly into the warehouse (via Kafka, Fivetran, or Airbyte). dbt then performs all transformations **inside the data warehouse engine** using pure SQL and Jinja.
* **Software Engineering Best Practices in SQL:**
  dbt brings version control, automated testing, CI/CD, documentation, and dependency resolution to SQL.

---

## 🗂️ 2. The Staging vs Marts Architecture

```mermaid
graph LR
    subgraph Raw["Raw Sources (EL)"]
        R1[raw_users.csv]
        R2[raw_trades.csv]
    end

    subgraph Staging["Staging Layer (Views)"]
        S1["stg_users\n(Casting, KYC standardization)"]
        S2["stg_trades\n(Cash flow deltas, exchange mapping)"]
    end

    subgraph Marts["Marts Layer (Fact Table)"]
        M1["fct_portfolio_performance\n(Cumulative positions, running cash,\nprice delta via Window Functions)"]
    end

    R1 --> S1
    R2 --> S2
    S1 -->|ref('stg_users')| M1
    S2 -->|ref('stg_trades')| M1
```

| Layer | Prefix | Materialization | Purpose | Rules |
| :--- | :--- | :--- | :--- | :--- |
| **Sources** | `raw_` | Tables | Raw data as dumped by ingestion pipelines | Never query directly in dashboards |
| **Staging** | `stg_` | Views | 1-to-1 with raw source: data cleansing, type casting, standardized column naming | No complex joins or aggregations |
| **Marts** | `fct_` / `dim_` | Tables | Business-ready dimensional models (Kimball facts and dimensions) | Contains business logic, metrics, and joins |

---

## 🔗 3. The Magic of `{{ ref(...) }}` & DAG Lineage

Instead of hardcoding table names like `FROM prod_db.analytics.stg_trades`, you write:
```sql
with trades as (
    select * from {{ ref('stg_trades') }}
)
```
### Why `ref()` is crucial:
1. **Automated DAG (Directed Acyclic Graph):** dbt parses all `ref()` calls to automatically determine the exact topological build order. It knows `stg_trades` must be built before `fct_portfolio_performance`.
2. **Environment Portability:** In development, dbt automatically resolves `{{ ref('stg_trades') }}` to `dev_alex.stg_trades`. In production, it resolves to `prod_analytics.stg_trades` without changing a single line of SQL.

---

## 🪟 4. Senior SQL Window Functions Breakdown

A common interview question: *"What is the fundamental difference between an aggregate function with `GROUP BY` and a `WINDOW FUNCTION`?"*
* **`GROUP BY`:** Collapses multiple rows into a single summary row per group.
* **`WINDOW FUNCTION`:** Performs a calculation across a set of table rows related to the current row, **while retaining the individuality of every single row**.

### The Anatomy of a Window Function:
```sql
FUNCTION() OVER (
    PARTITION BY user_id 
    ORDER BY executed_at ASC 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
```

### The 4 Window Functions Used in our `fct_portfolio_performance`:

#### 1. `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY executed_at ASC)`
* **Purpose:** Sequentially numbers each user's transactions (1, 2, 3...) regardless of ticker.
* **Fintech Use Case:** Determining first-time traders, onboarding velocity, and order sequencing.

#### 2. Cumulative Stock Holding:
```sql
SUM(share_delta) OVER (
    PARTITION BY user_id, ticker 
    ORDER BY executed_at ASC 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) as cumulative_shares_held
```
* **Explanation:** Sums the share deltas (+10 on BUY, -5 on SELL) for that specific investor and ticker up to the current trade row.
* **Result:** After BUY 10, position = 10. After BUY 15, position = 25. After SELL 5, position = 20.

#### 3. Running Account Cash Balance:
```sql
SUM(cash_flow_eur) OVER (
    PARTITION BY user_id 
    ORDER BY executed_at ASC 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) as running_cash_balance_impact_eur
```
* **Explanation:** Sums net trade outflows and inflows. Shows exact cash liquidity impact chronologically.

#### 4. Historical Comparison with `LAG()`:
```sql
LAG(price_eur, 1) OVER (
    PARTITION BY user_id, ticker 
    ORDER BY executed_at ASC
) as prev_execution_price_eur
```
* **Explanation:** Grabs the price from 1 row prior in the partition. Allows immediate computation of `price_eur - prev_execution_price_eur` to show whether the investor bought higher or lower than their last fill.

---

## 🧪 5. Testing in dbt: Generic vs Singular Tests

In `models/staging/schema.yml` and `models/marts/schema.yml`, we define assertions that run automatically:

* **Generic Tests:**
  * `unique`: Asserts no duplicate primary keys exist.
  * `not_null`: Asserts no NULL values exist in critical columns.
  * `accepted_values`: Asserts enum values only match permitted sets (`['BUY', 'SELL']`, `['FREE', 'PRIME', 'PRIME_PLUS']`).
  * `relationships`: Referential integrity test (asserts every `user_id` in trades exists in users).
* **Singular Custom Tests:**
  SQL queries stored in `tests/` that must return **0 rows** to pass. (e.g., Asserting `cumulative_shares_held >= 0`).

---

## 🎤 6. Senior Data Engineer Interview Questions

### Q1: "How do you handle massive datasets in dbt to avoid rebuilding full tables every time?"
> **Winning Answer:**  
> *"We use **Incremental Materializations** (`+materialized: incremental`). In the model, we wrap the incremental filter inside the `is_incremental()` macro:  
> ```sql
> {% if is_incremental() %}
>   where executed_at > (select max(executed_at) from {{ this }})
> {% endif %}
> ```  
> On the first run, dbt builds the full table. On subsequent runs, it only queries and appends or merges new records based on a unique key, drastically reducing warehouse compute costs and runtime."*

### Q2: "What is the difference between `ROW_NUMBER()`, `RANK()`, and `DENSE_RANK()`?"
> **Winning Answer:**  
> *"If two items tie at rank 1:  
> - `ROW_NUMBER()` arbitrarily assigns distinct numbers: `1, 2, 3`.  
> - `RANK()` assigns tied ranks and skips subsequent positions: `1, 1, 3`.  
> - `DENSE_RANK()` assigns tied ranks without skipping positions: `1, 1, 2`.  
> In trade execution or order book matching, `ROW_NUMBER()` is typically preferred to ensure unique sequence IDs."*

---

## 🚀 7. Running the Live Local Simulation

You can execute the entire dbt transformation pipeline and schema test suite locally with zero dependencies:

```bash
python sprint_projects/02_dbt_fintech/run_local_simulation.py
```
*(Verify that all 4 tests pass and view the rendered portfolio performance mart in your terminal!)*
