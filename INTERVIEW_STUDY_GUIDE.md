# 🧠 dbt Core & Advanced SQL: Mental Models & Senior Data Engineer Interview Guide

> **Note:** This is your internal study guide and interview playbook. It breaks down dbt, Kimball dimensional modeling, and SQL window functions into intuitive analogies, gives you a 4-step formula to build any dbt pipeline from scratch, and arms you with 10 senior-level interview questions and winning answers.

---

## 🧒 Part 1: Explain dbt Like I'm 15 (The Restaurant Kitchen Analogy)

Imagine you run a restaurant that serves gourmet meals (reports and dashboards).

* **The Old ETL Way:**  
  You buy whole carrots and potatoes from the market. You hire a third party to peel, boil, and mash them on a truck in the parking lot, and then carry the mashed potatoes inside. It was slow, expensive, and if a potato went bad, you didn't find out until it was already mashed.
* **The Modern dbt (ELT) Way:**  
  You dump all the raw groceries straight into your giant walk-in industrial kitchen (**the Cloud Data Warehouse: Snowflake / BigQuery / Redshift**).  
  **dbt is your master chef's recipe book.**  
  It says:
  1. *Station 1 (Staging):* Wash and peel the carrots (`stg_users`, `stg_trades`).
  2. *Station 2 (Marts):* Combine them into the final dish (`fct_portfolio_performance`).  
  All the cooking happens **inside your powerful kitchen**, automated with clean SQL!

---

## 🔑 Part 2: The Core Concepts

### 1. What does `{{ ref(...) }}` actually do?
Instead of hardcoding database table paths like `FROM prod_db.analytics.stg_trades`, you write:
```sql
FROM {{ ref('stg_trades') }}
```
**Why this is genius:**
* **Automated Lineage (The GPS):** dbt scans all your SQL files, finds every `ref()`, and automatically draws the **DAG** (Directed Acyclic Graph). It knows `stg_trades` MUST be built before `fct_portfolio_performance`. You never have to manually sequence your scripts.
* **Environment Switcher:** In development, dbt automatically routes queries to your sandbox (`dev_nidhi.stg_trades`). In production, it routes to `prod_analytics.stg_trades` without changing a single line of code.

### 2. Staging vs Marts (Kimball Dimensional Modeling)
* **Staging (`stg_`):** Views. 1-to-1 with raw sources. Only used for cleaning, renaming columns, and casting types (`int`, `timestamp`). No heavy joins or aggregations!
* **Marts (`fct_` / `dim_`):** Tables. Business-ready. This is where joins, window functions, and business KPIs live.

---

## 🪟 Part 3: Window Functions Demystified

A classic interview question: *"What is the difference between `GROUP BY` and a `WINDOW FUNCTION`?"*

* **`GROUP BY`:** A trash compactor. If you have 10 trade rows for a user, `GROUP BY user_id` crushes them into **1 row**. You lose the transaction-level details!
* **`WINDOW FUNCTION`:** A moving magnifying glass. It calculates metrics across rows, but **keeps all 10 individual trade rows alive**!

### Anatomy of a Window Function:
```sql
SUM(share_delta) OVER (
    PARTITION BY user_id, ticker 
    ORDER BY executed_at ASC 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) as cumulative_shares_held
```
* **`PARTITION BY user_id, ticker`**: Create separate calculation buckets for each investor and stock.
* **`ORDER BY executed_at ASC`**: Sort the transactions chronologically from oldest to newest.
* **`ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`**: Start from the very first trade and add up everything until the current row.

---

## 🛠️ Part 4: The 4-Step Formula to Build Any dbt Model

1. **Declare Sources:** Define raw tables in a YAML file (`sources.yml`).
2. **Create Staging (`stg_`):** Create views with clean column aliases, consistent casing, and boolean flags.
3. **Build the Mart (`fct_`):** Use `ref()` to join staging models and compute running balances or sequences with window functions.
4. **Add Schema Tests (`schema.yml`):** Enforce `unique`, `not_null`, and `accepted_values`.

---

## 🎤 Part 5: 10 Senior Data Engineer Interview Questions & Answers

### Q1: "Why do modern data architectures prefer ELT over ETL?"
> **Winning Answer:**  
> *"Traditional ETL was limited by on-premises compute, requiring data to be transformed outside the database in transformation servers (Informatica, Talend) before loading.  
> Cloud data warehouses like Snowflake, BigQuery, and Databricks offer near-infinite, decoupled compute and storage. ELT dumps raw, immutable data directly into the warehouse first. Tools like dbt then transform data natively inside the warehouse engine using SQL, providing greater speed, automated lineage, zero data loss, and version-controlled transformations."*

### Q2: "How do you handle massive tables in dbt to avoid rebuilding full tables every time?"
> **Winning Answer:**  
> *"We use **Incremental Materializations** (`+materialized: incremental`). We define a `unique_key` and wrap the filter condition inside the `is_incremental()` Jinja macro:  
> ```sql
> {% if is_incremental() %}
>   where executed_at > (select max(executed_at) from {{ this }})
> {% endif %}
> ```  
> On the first run, dbt builds the full table. On subsequent runs, it only queries, transforms, and merges newly inserted or updated rows, saving massive warehouse compute costs."*

### Q3: "What is the difference between `ROW_NUMBER()`, `RANK()`, and `DENSE_RANK()`?"
> **Winning Answer:**  
> *"When ordering values that have ties (e.g., two trades with the exact same timestamp):  
> - `ROW_NUMBER()` arbitrarily breaks the tie and assigns unique sequential integers: `1, 2, 3`.  
> - `RANK()` assigns tied rows the same rank, but skips subsequent numbers: `1, 1, 3`.  
> - `DENSE_RANK()` assigns tied rows the same rank without skipping: `1, 1, 2`.  
> In order matching and financial transaction ledgers, `ROW_NUMBER()` is standard to maintain strict unique sequence identifiers."*

### Q4: "What are Slowly Changing Dimensions (SCD Type 1 vs Type 2) and how does dbt handle them?"
> **Winning Answer:**  
> *"SCD Type 1 overwrites old data with new data (no history retained).  
> SCD Type 2 preserves historical changes by appending a new row with validity timestamps (`valid_from`, `valid_to`, `is_current`).  
> dbt implements SCD Type 2 natively using **dbt Snapshots** (`snapshot` block). By defining a `target_schema`, `unique_key`, and `check_cols` (or `updated_at`), dbt automatically tracks historical state changes over time without manual merge SQL."*

### Q5: "What is the difference between generic tests and singular tests in dbt?"
> **Winning Answer:**  
> *"Generic tests are parameterized assertions defined in YAML files applied to columns—such as `unique`, `not_null`, `accepted_values`, and `relationships`.  
> Singular tests are custom SQL queries stored in the `tests/` directory. If the query returns **0 rows**, the test passes. If it returns 1 or more rows, the test fails (e.g., querying for accounts where `cumulative_shares_held < 0`)."*

### Q6: "How do you implement CI/CD for dbt to test pull requests quickly and affordably?"
> **Winning Answer:**  
> *"We use **dbt Slim CI** (`dbt build --select state:modified+ --defer --state path/to/prod/manifest`).  
> Instead of rebuilding the entire multi-terabyte data warehouse on every PR, dbt compares the PR code with the production `manifest.json`. It builds and tests **only the models that were modified and their downstream dependencies**, running them in an ephemeral PR schema before merging."*

### Q7: "How do you handle out-of-order financial events or late-arriving data in incremental models?"
> **Winning Answer:**  
> *"In financial data pipelines, network latency or partner bank delays can cause events to arrive out of order.  
> In incremental models, rather than querying `> max(executed_at)`, we implement a **lookback window**:  
> ```sql
> where executed_at > (select dateadd('day', -3, max(executed_at)) from {{ this }})
> ```  
> Paired with a robust `unique_key` (`trade_id`), dbt performs an `UPSERT` (MERGE), safely updating late-arriving or modified records without duplicating transactions."*

### Q8: "What are dbt Packages and Jinja Macros, and when should you use them?"
> **Winning Answer:**  
> *"Jinja macros are reusable functions in SQL (like DRY functions in Python). For example, creating a macro to convert currencies or clean phone numbers across 20 models.  
> dbt Packages are modular libraries of macros and models (like `dbt-utils` or `dbt-expectations`) imported via `packages.yml`. We use `dbt-utils` for surrogate key generation (`dbt_utils.generate_surrogate_key`) and cross-database SQL compatibility."*

### Q9: "What is a Surrogate Key, and why is it preferred over natural business keys in Kimball dimensional modeling?"
> **Winning Answer:**  
> *"A natural key is a business identifier (like an account number or email). Natural keys can change, contain special characters, or clash across merged systems.  
> A surrogate key is a system-generated hash or sequence (e.g. `md5(user_id || '-' || country_code)`). It ensures consistent integer or hash joins, decouples database performance from external business systems, and is mandatory for tracking historical states in SCD Type 2 dimension tables."*

### Q10: "How do you optimize query performance and reduce compute costs in Snowflake or BigQuery when querying large fact tables?"
> **Winning Answer:**  
> *"1. **Partitioning:** In BigQuery or Snowflake, partition the table on event date (`executed_at`). This allows the query engine to prune unneeded partitions during scans.  
> 2. **Clustering:** Cluster on frequently filtered/joined columns like `(user_id, ticker)` to co-locate related records in storage micro-partitions.  
> 3. **Avoid `SELECT *`:** Only project required columns to prevent full column scans in columnar databases."*

---

## 🎯 Part 6: The 30-Second Interview Pitch

> *"I design modern dimensional data architectures using dbt Core and cloud data warehouses. In my fintech analytics models, I structured clean staging views that enforce type safety and data quality contracts, feeding dimensional fact tables that utilize advanced SQL window functions (`SUM OVER`, `ROW_NUMBER`, `LAG`) for running cash liquidity and cumulative asset holdings. I maintain automated CI/CD schema testing covering uniqueness, referential integrity, and business logic invariants."*
