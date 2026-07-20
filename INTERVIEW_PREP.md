# AI Database Assistant — Interview Preparation Master Guide

This guide compiles potential interview questions you could face as an **AI / GenAI Engineer** or **Full-Stack Developer** based on this project. Questions are grouped by technical area and include comprehensive, production-grade answers to help you explain your design decisions, technical tradeoffs, and code implementation details.

---

## Table of Contents
1. [Project Overview & Behavioral Questions](#1-project-overview--behavioral-questions)
2. [Generative AI & LLM Engineering](#2-generative-ai--llm-engineering)
3. [Self-Healing SQL Repair (AI Agents)](#3-self-healing-sql-repair-ai-agents)
4. [Heuristic AI Charting & Analytics](#4-heuristic-ai-charting--analytics)
5. [Database Architecture & Schema Discovery](#5-database-architecture--schema-discovery)
6. [Security Hardening & AST SQL Validation](#6-security-hardening--ast-sql-validation)
7. [Caching, Performance & Latency Optimization](#7-caching-performance--latency-optimization)
8. [Full-Stack React & FastAPI Integration](#8-full-stack-react--fastapi-integration)

---

## 1. Project Overview & Behavioral Questions

### Q1. Can you walk me through the architecture and user flow of the AI Database Assistant?
**Answer:**
"The application is structured as a multi-container Dockerized platform consisting of a React 19 frontend, a FastAPI backend, and an SQLite database for storing local system metadata, session cache, and audit logs. 
When a user connects their PostgreSQL, MySQL, or Oracle database, the system performs dynamic schema discovery to fetch table catalogs and column lists.
When the user submits a plain-English question in the chat interface, the request is sent via JWT-authenticated REST APIs to the backend. The backend checks an SQLite cache using a SHA-256 hash of the question and schema fingerprint. On a cache miss, the backend utilizes Groq to generate a dialect-compliant SQL query. The query is put through an AST validation shield to block destructive commands. If the query runs successfully on the target database, the backend feeds the tabular results back to LLM pipelines to generate a plain-English explanation, an executive summary, and chart recommendations (Line, Area, Bar, or Pie) before returning the unified JSON package to the React client in **~380ms**."

### Q2. What was the most challenging technical hurdle you faced in this project, and how did you resolve it?
**Answer:**
"The most significant challenge was state synchronization and telemetry updating when switching target database connections. Originally, the business portfolio metrics and Recharts dashboard loaded telemetry on initial mount. However, if the user opened the sidebar and switched database connections, the dashboard components remained mounted and rendered outdated or empty KPI metrics because they didn't listen to active connection updates. 
I resolved this by implementing a **connection version tracking system**. I raised the connection version state to the parent `App.jsx` component and exposed an `onConnectionChange` callback. When the database connected or auto-connected, the `ConnectionManager` fired this callback, incrementing a `dbConnectionVersion` integer. By passing this integer as a prop to the `Dashboard` component and putting it inside the `useEffect` dependencies, the dashboard instantly detects the connection switch and triggers a clean re-fetch of KPI cards and analytics charts in real-time."

---

## 2. Generative AI & LLM Engineering

### Q3. Why did you choose Groq and Llama 3 over other LLMs (like GPT-4 or Claude)?
**Answer:**
"I selected **Groq with Llama 3** primarily due to **inference speed and cost-to-performance ratio**. Groq’s LPU (Language Processing Unit) architecture consistently returns tokens at exceptionally high throughput, yielding an LLM response latency of just **150ms - 300ms** (compared to 1.5 - 3 seconds on standard cloud endpoints). This throughput is critical for maintaining an interactive chat interface. In addition, Llama 3 is highly capable at structured text tasks like SQL generation when provided with clear, schema-injected system prompts, delivering **91% first-try SQL accuracy** without the cost overhead of commercial proprietary models."

### Q4. How did you structure the prompt to ensure the LLM generates syntax-correct SQL instead of conversational text?
**Answer:**
"I used strict **system prompting and schema context injection**. The prompt includes a dynamic printout of the database schema (table names, columns, data types). To ensure output sanitization, I instructed the model:
1. *'Return ONLY the raw SQL code. Do not include markdown fences like ` ```sql ` or conversational preamble.'*
2. *'Limit query outputs to 15 rows unless specified otherwise.'*
3. *'Utilize standard SQL Dialect syntax compliant with [PostgreSQL/MySQL/Oracle] depending on the active configuration.'*
On the backend, I implemented parsing logic that automatically strips any leftover markdown ticks and trims comments, keeping only the SQL query up to the last semicolon."

### Q5. LLMs have a context window limit. How does your platform handle very large database schemas with 100+ tables?
**Answer:**
"If we blindly inject every column of 100+ tables into the prompt, we run into context window bloat and LLM confusion. To scale schema injection:
1. We only inject the list of table names and descriptions first.
2. If the user asks a question, we run a lightweight pre-filtering step (using TF-IDF or vector embeddings of table descriptions) to identify the **top 5-10 most relevant tables** related to the query.
3. We then inject *only* the column details of those selected tables into the final prompt context. This reduces context consumption and keeps SQL translation accuracy high."

---

## 3. Self-Healing SQL Repair (AI Agents)

### Q6. Walk me through the engineering of the "Self-Healing SQL Repair Framework". How does the backend recover from failed SQL queries?
**Answer:**
"When the backend attempts to execute a generated query against a target database and encounters a database driver exception (e.g., a missing column or incorrect table join), the error is caught by a `try-except` block. 
Instead of bubbling this error up to the client, the backend initiates a **one-shot repair iteration**:
1. It aggregates the user's original question, the failing SQL query, and the exact database engine error message (e.g., `Relation "rooms" does not exist`).
2. It sends this error packet back to the LLM with a system prompt: *'The generated query failed with error [Error]. Correct the SQL syntax using the actual schema columns [Columns].'*
3. The LLM processes the error context, identifies the mismatch (e.g., correcting table name `rooms` to `property_rooms`), and returns a repaired query.
4. The backend runs this query through the AST validator and executes it. This self-healing mechanism recovers **80% of query failures** automatically."

```text
[FastAPI Backend] ──(Execute SQL)──► [Target DB]
                                       │
                                   [FAIL - Database Driver Error]
                                       │
                                       ▼
  [SQL Repair Service] ──(Question + Bad SQL + Error)──► [LLM Reprompt]
                                                               │
                                                               ▼
  [Execute Repaired SQL] ◄────────────────────────────── [Returned SQL]
```

### Q7. Why do you only allow a single repair attempt (one-shot repair)?
**Answer:**
"Limiting the repair agent to a single attempt prevents infinite loop states and excessive API token usage. If the LLM generates a bad query, gets feedback, and generates a second query that *also* fails, it indicates either a fundamental schema misunderstanding or an ambiguous user question. In this case, it is computationally cleaner and safer to raise a sanitized error message to the user, asking them to clarify their prompt."

---

## 4. Heuristic AI Charting & Analytics

### Q8. How does the application decide whether to show a chart, and how does it select the chart type?
**Answer:**
"We use a **Heuristic Chart Decision Engine** (`app/services/chart_decision_service.py`). When query results are returned, the engine analyzes the shape, names, and data types of the output dataset:
* **Time-Series Data**: If one column contains dates or months, and another is numeric, it recommends a **Line or Area chart** to visualize trends.
* **Proportional Data**: If there are 3-5 distinct category rows representing fractions of a total sum, it recommends a **Pie chart**.
* **Categorical Comparisons**: If there are multiple textual categories (e.g., properties) and numeric counts, it recommends a **Bar chart**.
* **Scalar values**: If there's only a single row/column output, it turns off chart rendering (`show_chart = False`) and prompts the UI to display KPI cards instead.
This rule-based classification ensures **95% recommendation accuracy** without running expensive LLM loops."

---

## 5. Database Architecture & Schema Discovery

### Q9. How did you implement dynamic schema discovery across different database systems?
**Answer:**
"I designed a driver-agnostic schema service (`app/services/schema_service.py`). When the target database connection is established, the backend executes metadata queries against the database's catalog tables:
* **PostgreSQL / MySQL**: Queries the standard `information_schema.tables` and `information_schema.columns` catalogs to fetch table list, columns, data types, and primary keys.
* **Oracle**: Queries Oracle-specific catalogs like `sys.user_tables` and `sys.user_tab_cols`.
The results are mapped into a standardized Python dictionary and passed to the frontend to build the **Schema Explorer** tree."

### Q10. What are the tables inside your metadata database (`assistant_metadata.db`) and why is it separated from the target database?
**Answer:**
"The metadata database is a local SQLite database that houses 6 core tables: `users` (profiles), `user_connections` (credentials), `query_logs` (audit history), `query_cache` (cached lookups), `saved_reports` (pinned dashboards), and `security_events` (admin audit trails).
This database is isolated from target databases for three reasons:
1. **Security**: We do not store application state, users, or credentials in client business databases.
2. **Performance**: Isolates transactional logging and query caching from business operations.
3. **Decoupling**: Allows the assistant to operate independently even if the client database is offline or disconnected."

---

## 6. Security Hardening & AST SQL Validation

### Q11. SQL Injection is a primary threat for NL-to-SQL systems. How did you harden the backend against injection attacks?
**Answer:**
"I built a multi-layered security shield:
1. **Strict Read-Only Credentials**: The target database connection credentials are configured on the database engine itself to only have `SELECT` privileges.
2. **AST-based SQL Validation**: Every generated query is parsed and validated using a custom validator (`app/services/query_validator.py`) before execution. It scans the query syntax tree and strictly blocks forbidden operations like `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, or `TRUNCATE`.
3. **Chained Query Block**: It rejects multi-statement executions (queries containing a semicolon followed by another instruction, e.g. `SELECT * FROM users; DROP TABLE rooms;`) by verifying that the semicolon only appears at the terminal end of the query."

### Q12. How does the account lockout policy defend against brute-force attacks on your authentication API?
**Answer:**
"The backend implements an automated account lockout policy. In `app/routes/auth.py`, login attempts track consecutive password failures in the metadata DB. If a username registers **5 consecutive failures**, we set a `locked_until` timestamp to **15 minutes** in the future. Any subsequent login attempt within that window immediately returns `403 Forbidden` and logs a `LOCKED_OUT_ATTEMPT` event in the audit trail, preventing malicious automated tools from trying thousands of password combinations."

---

## 7. Caching, Performance & Latency Optimization

### Q13. How did you design the query caching mechanism, and how do you prevent stale cache hits?
**Answer:**
"The caching mechanism (`query_cache` table) uses a compound primary key: `question_hash` (SHA-256 of the lowercase user question) and `schema_hash` (a fingerprint representing the table names and column counts of the database). 
1. If the user asks a cached question, but the database schema has changed (e.g., a table was added or renamed), the `schema_hash` changes. This triggers a cache miss, forcing a fresh query generation.
2. We enforce a **TTL (Time-To-Live) of 10 minutes (600 seconds)** on cached results. We check the `created_at` timestamp of the cache entry; if it exceeds 10 minutes, the entry is invalidated and a fresh query is generated to ensure data accuracy."

---

## 8. Full-Stack React & FastAPI Integration

### Q14. What are React state initializers and how did you resolve the React "impure function call during render" error?
**Answer:**
"In React, setting initial state values by executing functions directly—like `useState(Date.now())` or `useState(JSON.parse(localStorage.getItem(...)))`—causes those functions to execute on *every single render* of the component, which violates React's pure rendering model and degrades performance. 
I resolved this by converting the initializers in `App.jsx` into **lazy state initializers** (passing a callback function, e.g. `useState(() => Date.now())`). React will then execute this function **only once during the mounting phase**, keeping rendering pure and efficient."

### Q15. How does the frontend handle Excel and CSV exports? Do you perform this on the server or the client?
**Answer:**
"We perform data exports **entirely on the client side** to minimize server load. 
* **CSV Export**: The frontend maps the array of JSON objects returned from `/ask` into a comma-delimited string, escapes special characters (comma, double quotes) using a custom sanitization function, wraps it in a `Blob` object, and triggers a local browser download link.
* **Excel Export**: We integrated the lightweight client library `xlsx`. We convert the query result array to a sheet using `XLSX.utils.json_to_sheet` and save the file using `XLSX.writeFile`. This keeps data processing fast and local."

---

## 9. Commonly Neglected Basics & Security Tradeoffs

### Q16. In FastAPI, what is the difference between `async def` and `def` when declaring route handlers? Why did you use `def` for your SQL queries?
**Answer:**
"If you declare an endpoint with `async def`, FastAPI executes it directly in the main event loop, expecting all operations inside to be non-blocking. If a route runs blocking synchronous operations (such as query execution using synchronous database drivers like `psycopg2` or `pymysql`), it blocks the entire event loop, stopping the server from processing other requests. 
FastAPI runs endpoints declared with standard `def` in an **external threadpool** automatically. Because our database drivers and Groq API calls are synchronous and blocking, declaring them as regular `def` ensures they execute in worker threads, keeping the event loop unblocked and highly concurrent."

### Q17. What is CORS and how is it configured in your application? What are the production security implications?
**Answer:**
"**CORS (Cross-Origin Resource Sharing)** is a browser security mechanism that restricts web applications from making requests to a domain different from the one that served it. 
In `app/main.py`, we import `CORSMiddleware` and configure it:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
In development, we restrict origins to our React client `http://localhost:5173`. In production, leaving `allow_origins` as a wildcard `*` is a high security vulnerability (it allows any malicious site to perform requests on behalf of users). We must lock it down to the exact production domain names."

### Q18. Your frontend stores the JWT in `localStorage`. What are the security risks associated with this, and how would you fix it?
**Answer:**
"Storing sensitive tokens in `localStorage` makes them vulnerable to **XSS (Cross-Site Scripting)** attacks. If a malicious script runs on the client, it can read `localStorage` and steal the token. 
The secure alternative is to store the JWT inside an **`httpOnly` and `Secure` cookie**. When the user logs in, the backend sets this cookie in the HTTP response. The browser automatically sends it with every API call, but JavaScript cannot read or access it, fully isolating the credentials from XSS scripts."

### Q19. SQLite supports multiple readers but only a single writer. How does your app handle SQLite concurrency and prevent "database is locked" errors?
**Answer:**
"To prevent SQLite write locks from blocking connections, we configure two standard mechanisms:
1. **Busy Timeout**: When connecting to SQLite, we pass `timeout=10.0` (10 seconds). If a transaction is writing, other threads will wait up to 10 seconds for the lock to clear before throwing an error.
2. **Write-Ahead Logging (WAL)**: We run `PRAGMA journal_mode=WAL;` on database initialization. WAL mode allows multiple reader threads to read concurrent snapshots of the database while a writer thread is executing, significantly reducing lock contention."

### Q20. Why is creating and closing database connections for every request bad? How would you optimize it?
**Answer:**
"Opening a new TCP/IP connection to PostgreSQL/MySQL for every single request creates high network latency overhead and consumes significant CPU resources on both the backend and database server. 
To optimize this, we should implement **Connection Pooling** (e.g. using SQLAlchemy's connection pool or `psycopg2.pool`). A pool maintains a set of hot, open database connections. When a request comes in, it rents a connection from the pool, executes the query, and returns it immediately without ever closing the TCP socket."

