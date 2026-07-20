# AI Database Assistant

An enterprise-ready business intelligence platform that translates plain-English questions into valid SQL queries using Groq LLMs, runs them securely against your target database, and renders interactive analytics, charts, and summaries.

---

## 🚀 Key Features

* **Natural Language to SQL**: Ask questions like *"show monthly revenue for 2025"* and watch the AI translate, execute, and explain the query.
* **Multi-Database Support**: Connects dynamically to **PostgreSQL**, **MySQL**, and **Oracle** databases.
* **Interactive Schema Explorer**: Inspect table structures, columns, row counts, and trigger safe table sample previews.
* **AI Analytics & Visualization**: Automatically generates executive summaries, key findings, risks, and recommendations for query results, alongside chart recommendations (Bar, Line, Area, Pie).
* **Dynamic Portfolio Dashboard**: Real-time KPI widgets and saved reports that synchronize immediately when you switch target databases.
* **Automatic SQL Repair (Self-Healing)**: Translucently repairs syntax or mismatch errors using original DB engine exception feedback.
* **Security Hardening**:
  * Strict read-only SQL validation (blocks `DELETE`, `DROP`, `ALTER`, etc.).
  * User authentication via JWT with automatic refresh tokens.
  * Brute-force lockout protection (5 failed logins locks the account for 15 minutes).
  * API rate limiting (10 attempts/min for login, 30 requests/min for ask).
  * Full security audit logs in SQLite.

---

## 🛠️ Tech Stack

* **Backend**: FastAPI (Python), Uvicorn, SQLite (`assistant_metadata.db` for metadata & authentication), Groq LLM API.
* **Drivers**: `psycopg2-binary` (PostgreSQL), `pymysql` (MySQL), `oracledb` (Oracle).
* **Frontend**: React 19, Vite 8, Recharts (visualizations), Axios (API client), XLSX (Excel export).
* **DevOps**: Docker, Docker Compose.

---

## 📂 Documentation

For a comprehensive guide covering detailed system architecture, API endpoints, component design, database schemas, and security specifications, see:
* **[DOCUMENTATION.md](./DOCUMENTATION.md)**

---

## ⚡ Quick Start (Using Docker)

The easiest way to launch the entire application stack is using Docker Desktop.

### 1. Configure Environment Variables
Create a `.env` file in the project root:
```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# SQLite Metadata Database Path (Keep default for Docker)
METADATA_DB_PATH=/app/assistant_metadata.db
```

### 2. Run the Stack
Start the containers using Docker Compose:
```bash
docker compose up --build
```
* **React Frontend**: [http://localhost:5173](http://localhost:5173)
* **FastAPI Backend**: [http://localhost:8000](http://localhost:8000)
* **Swagger API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔧 Manual Local Setup (Without Docker)

### 1. Set Up Backend
1. Initialize virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows: venv\Scripts\activate
   ```
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your environment variables in `.env` (ensure a local SQLite path):
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   METADATA_DB_PATH=assistant_metadata.db
   ```
4. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

### 2. Set Up Frontend
1. Navigate to the client directory:
   ```bash
   cd ai-db-frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```

---

## 🧪 Verification & Diagnostics

To run the full suite of automated unit and diagnostic verification tests:

```bash
# Run all unit tests
python -m unittest discover -s tests

# Verify specific modules
python test_security_hardening.py
python test_sprint6_ops.py
python test_sprint7_admin.py
```
