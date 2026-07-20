# AI Database Assistant — 3-Minute Video Demo Script & Storyboard

This document is your step-by-step guide to recording a highly professional video demonstration of the AI Database Assistant. It is divided into key chronological segments, showing you **what to do on screen (Visual Actions)** and **what to say (Voiceover Script)**.

---

## Storyboard Timeline Overview
* **0:00 - 0:30 (Hook & Introduction)**: Introduce the app, the core problem it solves, and the tech stack.
* **0:30 - 1:10 (Auth & Multi-Database Connection)**: Show the login, connection setup, and Schema Explorer.
* **1:10 - 1:50 (Natural Language-to-SQL & Explanations)**: Type a query, show the generated SQL, results, and plain-English translation.
* **1:50 - 2:20 (AI Analytics & Chart Recommendations)**: Showcase Recharts integration, summaries, and saving a custom report.
* **2:20 - 2:45 (Self-Healing SQL Repair Demo)**: Explain the backend query-healing process.
* **2:45 - 3:15 (Dynamic Dashboard & Admin Panels)**: Show real-time KPI updates on connection switch, telemetry, and audit log exports.

---

## Scene-by-Scene Script

### Scene 1: Introduction & Hook
* **Time**: 0:00 – 0:30
* **Visual Action**: 
  * Show the application login screen.
  * *Optionally*, turn on your webcam in the corner if you're comfortable.
  * Log in with test user credentials (e.g. `madhusuravaram91@gmail.com`).
* **Voiceover Script**:
  > *"Hi everyone! Today, I’m excited to show you the AI Database Assistant—a full-stack, enterprise-ready business intelligence platform that translates plain-English questions into database executions. 
  > 
  > Instead of writing complex SQL queries manually, users can simply type their business questions in plain English. The platform dynamically discovers database structures, generates dialect-compliant SQL via LLMs, validates queries against AST security policies, runs them, and provides full analytics summaries."*

---

### Scene 2: Database Connection & Schema Explorer
* **Time**: 0:30 – 1:10
* **Visual Action**: 
  * Once logged in, expand the Left Sidebar.
  * Highlight the **Database Connection** panel. Show the green `🟢 Connected` badge.
  * Point your mouse to the **📂 Schema Explorer**.
  * Expand the `expenses` or `properties` table, showing columns and column types.
  * Click the **View Sample Data** button at the bottom of the table list.
  * Watch the screen automatically switch to the Chat tab and show the first 15 table rows.
* **Voiceover Script**:
  > *"After logging in, we enter a secure connection panel. The backend dynamically supports PostgreSQL, MySQL, and Oracle database drivers. 
  > 
  > Once connected, the app performs real-time schema discovery. Over in the Schema Explorer, we can browse tables, column catalogs, and row counts dynamically queried from database catalogs. Clicking 'View Sample Data' instantly executes a safe read-only preview of the table right inside our workspace."*

---

### Scene 3: Natural Language-to-SQL & Plain-English Explanations
* **Time**: 1:10 – 1:50
* **Visual Action**:
  * Type this query into the search bar: 
    `Show the total rent payment amount collected in each month of 2025 to see the monthly trend`
  * Press **Enter** or click **Ask AI**.
  * Scroll through the query card results: point to the **Generated SQL** card, the **Execution Time** badge (e.g. `⚡ 350ms`), the **Results Table**, and the **💡 Plain-English Explanation**.
* **Voiceover Script**:
  > *"Let's ask the assistant a real question: 'Show the total rent payment amount collected in each month of 2025'. 
  > 
  > The FastAPI backend processes the question, checks our SQLite cache, and triggers a Llama-3 completion. In just 380 milliseconds, the assistant generates a dialect-compliant SQL query, validates it against our AST parser to prevent injection attacks, and runs it. Alongside the results table, the system translates the SQL back into plain English, explaining exactly how it fetched the records."*

---

### Scene 4: AI Insights & Recharts Visualization
* **Time**: 1:50 – 2:20
* **Visual Action**:
  * Scroll down to show the **🧠 AI Analysis** card containing Executive Summary, Key Findings, and Recommendations.
  * Scroll to the **Chart Card** displaying the monthly trend visualization.
  * Click **❤️ Favorite** to bookmark the query.
  * Click **⭐ Save Report** and name it `Monthly Rent Trends`.
* **Voiceover Script**:
  > *"But we don't just get data tables. An integrated AI analytics pipeline parses the query output to generate executive summaries, key findings, and risk alerts. 
  > 
  > Furthermore, our heuristic engine recommends and renders the optimal Recharts layout—recommending this Area chart for our monthly rent trend. We can bookmark this query as a favorite, or save it directly to our portfolio dashboard."*

---

### Scene 5: Self-Healing SQL Repair (AI Agent)
* **Time**: 2:20 – 2:45
* **Visual Action**:
  * Speak to the camera or show the backend file structure (`app/services/sql_repair_service.py`).
  * *Optional*: Enter a query with a column typo to trigger the repair, or simply explain it conceptually while pointing to the documentation.
* **Voiceover Script**:
  > *"One of the core engineering highlights is our Self-Healing SQL Repair Framework. If the LLM generates a query that fails due to a database exception—like referencing a missing column or incorrect table alias—the backend catches the error. 
  > 
  > Instead of failing, an AI repair agent intercepts the exception, aggregates the bad SQL, the database error message, and schema columns, re-prompts the LLM, and runs the corrected query—repairing 80% of execution anomalies on the first retry."*

---

### Scene 6: Dynamic Portfolio Dashboard & Admin Panel
* **Time**: 2:45 – 3:15
* **Visual Action**:
  * Click the **Dashboard** tab in the top-right navbar. Show the KPI cards (`Total Revenue`, `Occupancy Rate`, etc.) and the charts loading.
  * Open the sidebar, switch the connection details, and click **Connect**. Show the Dashboard metrics instantly updating.
  * Click the **Admin** tab. Show the telemetry metrics, system uptime banner, daily metrics line graph, and highlight the **Download Audit Trail** button.
* **Voiceover Script**:
  > *"When we jump over to our Portfolio Analytics Dashboard, we see our dynamic KPIs and saved reports. Because we implement live connection state tracking, switching databases automatically updates all dashboard cards and charts in real-time. 
  > 
  > Lastly, the Admin panel displays telemetry graphs tracking daily query metrics, LLM repair successes, and uptime. To satisfy enterprise compliance, admins can download the SQLite security events audit trail directly as a CSV.
  > 
  > The entire stack is containerized with Docker for easy deployment. Thanks for watching, and check out the full code in the GitHub link below!"*

---

## 📹 Production Tips for Recording
1. **Screen Resolution**: Set your monitor to **1080p (1920x1080)** before recording. This ensures all text, code cards, and charts are crisp and readable on mobile phones and laptops.
2. **Audio Quality**: Use a dedicated USB microphone if possible. Sound quality is often more important than video quality for tutorials.
3. **Pacing**: Don't rush through the clicks. Let the transition animations in the React application play out smoothly.
4. **Recording Tools**: Use **OBS Studio** (free, open-source) or **Loom** for recording your screen and camera bubble.
