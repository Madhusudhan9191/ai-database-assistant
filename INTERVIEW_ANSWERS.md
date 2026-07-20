# AI Database Assistant — Interview Q&A Answers

---

## 🏗️ Architecture

### Q: Approximately how many backend API endpoints do you have?

**Answer: 22 endpoints.**

Here's the complete breakdown:

| # | Method | Route | Purpose |
|---|---|---|---|
| 1 | `GET` | `/` | Home / API status |
| 2 | `GET` | `/health` | Health check |
| 3 | `GET` | `/api/health` | API health check |
| 4 | `GET` | `/api/version` | Version + uptime metadata |
| 5 | `POST` | `/ask` | NL-to-SQL query execution (core feature) |
| 6 | `GET` | `/history` | User's query history |
| 7 | `GET` | `/history/count` | User's total query count |
| 8 | `GET` | `/history/latest` | User's latest unique queries |
| 9 | `DELETE` | `/history` | Clear all user history |
| 10 | `DELETE` | `/history/{id}` | Delete single history entry |
| 11 | `POST` | `/history/bulk-delete` | Bulk delete history entries |
| 12 | `GET` | `/schema/fingerprint` | DB type + name + schema hash |
| 13 | `POST` | `/saved-reports` | Save a report |
| 14 | `GET` | `/saved-reports` | Get user's saved reports |
| 15 | `DELETE` | `/saved-reports/{id}` | Soft-delete a saved report |
| 16 | `POST` | `/favorites` | Add a favorite query |
| 17 | `GET` | `/favorites` | Get user's favorites |
| 18 | `DELETE` | `/favorites/{id}` | Remove a favorite |
| 19 | `GET` | `/admin/stats` | Admin analytics dashboard (RBAC-protected) |
| 20 | `POST` | `/test-connection` | Test + set active DB connection |
| 21 | `GET` | `/schema` | List all tables in connected DB |
| 22 | `GET` | `/table-columns/{table}` | Get columns for a table |
| 23 | `GET` | `/table-data/{table}` | Preview first 15 rows of a table |
| 24 | `GET` | `/table-counts` | Row counts for all tables |
| 25 | `GET` | `/dashboard/summary` | Full dashboard: KPIs + charts + saved reports |
| 26 | `POST` | `/auth/register` | User registration |
| 27 | `POST` | `/auth/login` | User login |
| 28 | `GET` | `/auth/me` | Get current authenticated user |

**Corrected count: 28 endpoints total.**

---

### Q: Did you design the database schema yourself for chat history, saved reports, settings, etc.?

**Answer: Yes, I designed the entire metadata database schema myself.** It's a local SQLite database (`assistant_metadata.db`) with 4 tables:

```sql
-- 1. users: Authentication & user management
users (
    id, username, email, password_hash, is_admin, created_at
)

-- 2. query_logs: Full audit trail of every query executed
query_logs (
    id, question, generated_sql, execution_time_ms, success,
    error_message, row_count, chart_type, question_hash,
    user_id, repair_attempted, repaired, created_at
)

-- 3. saved_reports: Dashboard report definitions with schema versioning
saved_reports (
    id, report_name, question, generated_sql, chart_type,
    database_type, database_name, schema_hash, schema_version,
    is_active, user_id, created_at, updated_at,
    last_execution_time, execution_count
)

-- 4. favorites: Bookmarked queries scoped to user + DB fingerprint
favorites (
    id, question, generated_sql, database_type, database_name,
    schema_hash, schema_version, user_id, created_at
)
```

Key design decisions:
- **User-scoped data isolation** — All `query_logs`, `saved_reports`, and `favorites` are filtered by `user_id`
- **Schema fingerprinting** — Saved reports and favorites are tied to a specific `database_type + database_name + schema_hash` combination, so they only show up when the matching database is connected
- **Soft deletes** — Reports use `is_active = 0` instead of hard deletion
- **Telemetry columns** — `repair_attempted` and `repaired` track SQL auto-repair metrics
- **Dynamic migration** — Schema uses `ALTER TABLE ... ADD COLUMN` with error handling to support incremental upgrades without migrations

---

### Q: Are you using SQLAlchemy, psycopg, or direct database connections?

**Answer: Direct database connections using native drivers — no ORM.**

| Database | Driver | Connection Method |
|---|---|---|
| PostgreSQL | `psycopg2-binary` | **Connection pooling** via `psycopg2.pool.ThreadedConnectionPool` (min=1, max=10 connections) |
| MySQL | `pymysql` | Direct connection per request |
| Oracle | `oracledb` | Direct connection per request |
| SQLite (metadata) | `sqlite3` (built-in) | Direct connection per request with `row_factory = sqlite3.Row` |

For PostgreSQL, I built a custom `PooledConnection` wrapper class that overrides `.close()` to return the connection back to the pool instead of closing it — this way all existing code can call `conn.close()` without knowing about pooling. The pool also detects when the user switches databases and rebuilds itself automatically.

---

## 🤖 AI Features

### Q: Which Groq models are you using?

**Answer: `llama-3.1-8b-instant`** — used across all 5 AI service modules:

| Service | What It Does |
|---|---|
| `ai_service.py` | Converts natural language → SQL query |
| `insight_service.py` | Generates structured business insights (Executive Summary, Key Findings, Risks, Recommendations) |
| `chart_decision_service.py` | Determines which chart type best visualizes the data |
| `explanation_service.py` | Generates a 1-sentence plain-English explanation of the SQL |
| `sql_repair_service.py` | Takes a failed SQL + error message and generates a corrected query |

I chose `llama-3.1-8b-instant` for its speed — it has sub-second response times through Groq's inference engine, which is important because each `/ask` request may trigger up to 4 LLM calls (SQL generation → explanation → insights → chart decision).

---

### Q: Do you send schema information to the LLM dynamically?

**Answer: Yes, the full schema is sent dynamically in every SQL generation prompt.** Here's exactly what gets sent:

1. **Table names + columns + data types** — Fetched live from `information_schema.columns` (PostgreSQL/MySQL) or `user_tab_columns` (Oracle)
2. **Sample values** — For text/varchar columns, up to 3 distinct sample values are fetched and included (e.g., `status (varchar) [Samples: Active, Vacated, Notice Period]`). This helps the LLM understand the actual values in the data.
3. **Foreign key relationships** — Auto-discovered from `information_schema.table_constraints` (PostgreSQL), `KEY_COLUMN_USAGE` (MySQL), or `user_constraints` (Oracle)
4. **Logical relationship fallback** — If no physical foreign keys exist, the system auto-discovers relationships by matching column naming patterns (e.g., `room_id` in table `tenants` → `id` in table `rooms`)

The schema is **cached in memory** and only re-fetched when the database connection parameters change (detected by comparing a tuple of host, port, database, username).

---

### Q: Do you have SQL repair/correction if generated SQL fails?

**Answer: Yes — I built a full SQL Self-Healing pipeline.** Here's how it works:

```
Step 1: Generate SQL from user question
Step 2: Validate SQL (security check)
Step 3: Execute SQL
        ↓ (if execution fails)
Step 4: Catch the database error
Step 5: Send to repair service with:
        - Original question
        - Failed SQL
        - Database error message
        - Full schema + relationships
Step 6: LLM generates corrected SQL
Step 7: Validate repaired SQL (security check again)
Step 8: Execute repaired SQL
        ↓ (if repair also fails)
Step 9: Return the original error with intelligent suggestions
```

**Telemetry tracking:** Every query logs `repair_attempted` (0 or 1) and `repaired` (0 or 1) to the metadata database, so the admin dashboard can show the repair success rate across the platform.

---

## 🗄️ Multi-Database

### Q: How many databases are currently supported?

**Answer: 3 database engines are fully supported:**

| Database | Status | Driver | Dialect Handling |
|---|---|---|---|
| **PostgreSQL** | ✅ Fully supported | `psycopg2-binary` | `ILIKE`, `LIMIT`, `EXTRACT(YEAR FROM AGE(...))` |
| **Oracle** | ✅ Fully supported | `oracledb` | `UPPER() LIKE UPPER()`, `FETCH FIRST N ROWS ONLY`, direct date subtraction |
| **MySQL** | ✅ Fully supported | `pymysql` | `LIKE` (case-insensitive by default), `LIMIT`, `TIMESTAMPDIFF()` |

### Q: Does the same prompt work across all supported databases?

**Answer: No — the prompt is dynamically customized per database dialect.** Specifically, 3 rules in the LLM prompt change based on `db_type`:

1. **Row limiting** — PostgreSQL/MySQL use `LIMIT`, Oracle uses `FETCH FIRST N ROWS ONLY`
2. **Text filtering** — PostgreSQL uses `ILIKE`, MySQL uses `LIKE`, Oracle uses `UPPER(col) LIKE UPPER(value)`
3. **Date arithmetic** — PostgreSQL uses `end_date - start_date` or `EXTRACT(YEAR FROM AGE(...))`, MySQL uses `TIMESTAMPDIFF()`, Oracle uses `MONTHS_BETWEEN()` or direct date subtraction

The same dynamic dialect rules are also applied in the SQL repair service, so corrected queries are also dialect-appropriate.

---

## 📊 Dashboard

### Q: What exactly is saved?

| Component | Saved? | How |
|---|---|---|
| **SQL query** | ✅ Yes | Stored in `saved_reports.generated_sql` |
| **Query results** | ❌ No | Results are re-executed live each time the dashboard loads |
| **Charts** | ✅ Yes (type only) | The `chart_type` (bar, line, pie, area) is stored. The chart is re-rendered from live data |
| **AI insights** | ❌ No | Insights are only generated during the `/ask` flow, not stored |
| **Full report definition** | ✅ Yes | `report_name`, `question`, `generated_sql`, `chart_type`, `database_type`, `database_name`, `schema_hash` |

**Additional metadata tracked per report:**
- `execution_count` — How many times the report has been run
- `last_execution_time` — Duration of the last execution (ms)
- `schema_version` — Defaults to `v1`
- `is_active` — Soft delete flag

### Q: Can users reopen reports later and rerun them?

**Answer: Yes.** When a user opens the Dashboard tab, the system:

1. Fetches all saved reports matching the current `database_type + database_name + schema_hash + user_id`
2. **Re-executes the stored SQL** against the live database
3. Validates the SQL for security before execution
4. Generates chart data from the fresh results
5. Renders the charts using Recharts
6. Caches results in memory for 60 seconds (TTL) to avoid redundant queries
7. Increments the `execution_count` and updates `last_execution_time`

Reports are scoped to the database fingerprint — if the user connects to a different database, only reports saved for that database appear. If the schema has changed since the report was saved (different `schema_hash`), the report won't appear.

---

## 📈 Visualization

### Q: Which chart types are supported?

**Answer: 5 chart types + automatic AI-powered chart selection:**

| Chart Type | When Used | Component |
|---|---|---|
| **Bar** | Category comparisons, rankings, top-N | `BarChart` from Recharts |
| **Line** | Time series with ≤8 data points | `LineChart` from Recharts |
| **Area** | Time series with >8 data points, volume trends | `AreaChart` with gradient fill |
| **Pie** | Distribution/share data (2–8 categories) | `PieChart` with labeled segments |
| **Scatter** | Correlation between 2 numeric variables | `ScatterChart` from Recharts |

**How chart selection works — 3-tier decision system:**

1. **Smart Heuristics (no LLM call):** If columns contain time keywords (`month`, `date`, `year`, etc.) → Line/Area. If 2–6 categories with positive numbers → Pie.
2. **AI Decision (for ambiguous cases):** The LLM analyzes the data sample and returns a JSON decision.
3. **Post-validation & Sanitization:** A rule engine validates the AI's decision against the actual data shape:
   - Pie demoted to Bar if >8 or <2 categories
   - Scatter demoted to Bar if <2 numeric columns
   - Line/Area demoted to Bar if no time columns detected
   - Area/Line threshold: >8 points → Area, ≤8 → Line

All charts include a custom dark-theme tooltip, responsive containers, and gradient effects on Area charts.

---

## 🔒 Security

### Q: Besides SELECT/WITH validation, do you also block:

| Protection | Status | Implementation |
|---|---|---|
| **Multiple statements** | ✅ Blocked | Strips string literals, counts semicolons. If >1 found → rejected |
| **Comments** | ✅ Blocked | Regex patterns detect `-- ` line comments and `/* */` block comments |
| **DDL commands** | ✅ Blocked | `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `RENAME` in forbidden keywords list |
| **DML commands** | ✅ Blocked | `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `REPLACE` in forbidden keywords list |
| **Privilege escalation** | ✅ Blocked | `GRANT`, `REVOKE`, `EXEC`, `EXECUTE`, `CALL` blocked |
| **SQL injection patterns** | ✅ Blocked | 12 regex patterns including `UNION ALL SELECT...information_schema`, `INTO OUTFILE`, `LOAD_FILE()`, `BENCHMARK()`, `SLEEP()`, `PG_SLEEP()`, `WAITFOR DELAY`, `DBMS_PIPE` |
| **Query depth** | ✅ Limited | Max 10 levels of parenthesis nesting |
| **Query length** | ✅ Limited | Max 5,000 characters |
| **Table identifier injection** | ✅ Protected | `_validate_identifier()` enforces `^[a-zA-Z_][a-zA-Z0-9_$.]*$` regex on table names in schema routes |

**Full list of 18 forbidden keywords:**
`INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE, EXEC, EXECUTE, CALL, MERGE, REPLACE, LOCK, UNLOCK, RENAME, COMMENT`

### Q: Do you support read-only database users?

**Answer: Yes.** The system is designed to work with read-only database users. The SQL validation engine enforces that only `SELECT` and `WITH` (CTE) queries can be executed. The default database credentials in the `.env.example` use a user named `ai_readonly` — the recommended approach is to create a read-only database user with `SELECT`-only privileges.

---

## 📏 Scale

### Q: Largest result set tested?

**Answer:** Based on the code, there's no explicit row limit on query results. The system:
- Sends full results to the frontend
- Shows first **10 rows** in the UI table
- Sends first **20 rows** to the AI insight service
- Sends first **20 rows** for chart data
- Sends first **10 rows** to the AI chart decision service

The system has been tested with the sample data generator which creates: **10 owners, 25 properties, ~100 rooms, 50 tenants, 600 payments (50 tenants × 12 months), 150 expenses, and 100 maintenance requests** — totaling approximately **1,035 records** across 7 tables.

### Q: Largest database tested?

**Answer:** The sample data generator populates **7 tables** with ~1,035 total records across a PG property management database. Oracle and MySQL databases have also been tested (confirmed by error logs showing Oracle `ORA-` errors and MySQL connections).

### Q: Roughly how many tables have you tested against?

**Answer: 7 core tables:** `owners`, `properties`, `rooms`, `tenants`, `payments`, `expenses`, `maintenance_requests` — plus the system automatically discovers and works with any tables in the connected database via dynamic schema introspection.

---

## 📤 Export

| Export Format | Status | Implementation |
|---|---|---|
| **CSV** | ✅ Supported | Client-side export using manual CSV construction with proper escaping (handles commas, quotes, newlines) |
| **Excel (.xlsx)** | ✅ Supported | Client-side export using the `xlsx` (SheetJS) library |
| **PDF** | ❌ Not yet | Not implemented |

Both CSV and Excel exports include all rows from the query result (not just the 10 shown in the UI table).

---

## 🐳 Deployment

### Q: Is the entire application Dockerized?

**Answer: Yes, fully Dockerized with a production-grade setup.**

| Component | Container | Base Image | Details |
|---|---|---|---|
| **Backend** | `ai-db-backend` | `python:3.12-slim` | Uvicorn serving FastAPI on port 8000 |
| **Frontend** | `ai-db-frontend` | Multi-stage: `node:20-alpine` → `nginx:alpine` | Vite builds React app, Nginx serves static files on port 80 (mapped to 5173) |

### Q: Single container or Docker Compose?

**Answer: Docker Compose** — orchestrates both containers with:
- **Health checks** — Backend container has a Python-based health check hitting `/health` every 10 seconds
- **Volume mounts** — `logs/` directory and `assistant_metadata.db` are persisted across container restarts
- **Service dependency** — Frontend waits for backend to be healthy before starting (`condition: service_healthy`)
- **Host networking** — `extra_hosts: host.docker.internal:host-gateway` allows the backend container to connect to databases running on the host machine

```yaml
# docker-compose.yml structure:
services:
  backend:   # Port 8000, health-checked, volumes for logs + metadata DB
  frontend:  # Port 5173 → Nginx on port 80, depends on backend health
```

### Q: Have you deployed it anywhere publicly?

**Answer:** Based on the codebase, the project is configured for local development and Docker deployment. The CORS origins are set to `http://localhost:5173`, the frontend hardcodes `http://127.0.0.1:8000` as the backend URL, and the environment is set to `development` — indicating it has not been deployed to a public cloud environment yet. However, the Docker Compose setup is production-ready and could be deployed to AWS ECS, Google Cloud Run, or any Docker-compatible hosting with minimal configuration changes (primarily updating the API URL and CORS origins).
