# AI Database Assistant

AI-powered Database Assistant that converts natural language questions into SQL queries using Groq LLM, executes them on PostgreSQL, and displays results through a React frontend.

## Features

* Natural Language to SQL using Groq LLM
* PostgreSQL database integration
* Dynamic database schema discovery
* Query execution and result display
* Query history tracking
* Execution time tracking
* Recent query suggestions
* React frontend dashboard
* FastAPI backend API
* Dockerized backend
* Dockerized frontend
* Docker Compose multi-container setup

---

## Architecture

User Question

↓

React Frontend

↓

FastAPI Backend

↓

Groq LLM

↓

Generated SQL

↓

PostgreSQL Database

↓

Results Returned to Frontend

---

## Tech Stack

### Backend

* Python
* FastAPI
* PostgreSQL
* Psycopg2
* Groq API
* Pydantic

### Frontend

* React
* Vite
* Axios

### DevOps

* Docker
* Docker Compose
* Git
* GitHub

---

## Project Structure

```text
AI-db-assistant/
│
├── app/
│   ├── db/
│   │   └── database.py
│   │
│   ├── models/
│   │   └── schemas.py
│   │
│   ├── services/
│   │   ├── ai_service.py
│   │   ├── history_service.py
│   │   ├── query_service.py
│   │   └── schema_service.py
│   │
│   ├── config.py
│   └── main.py
│
├── ai-db-frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

### Home

```http
GET /
```

Returns API status.

### Ask Question

```http
POST /ask
```

Request:

```json
{
  "question": "show all customers"
}
```

Response:

```json
{
  "question": "show all customers",
  "generated_sql": "SELECT * FROM customers;",
  "execution_time_ms": 7,
  "data": [...]
}
```

### Query History

```http
GET /history
```

### History Count

```http
GET /history/count
```

### Latest Queries

```http
GET /history/latest
```

---

## Environment Variables

Create a `.env` file in the project root.

```env
GROQ_API_KEY=your_groq_api_key

DB_NAME=ai_db_assistant
DB_USER=your_username
DB_HOST=localhost
DB_PORT=5432
```

---

## Running Locally

### Backend

```bash
source venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger Docs:

```text
http://127.0.0.1:8000/docs
```

### Frontend

```bash
cd ai-db-frontend

npm install

npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## Running with Docker

Build and run the entire application:

```bash
docker compose up --build
```

Backend:

```text
http://localhost:8000
```

Frontend:

```text
http://localhost:5173
```

Stop containers:

```bash
docker compose down
```

---

## Example Questions

```text
show all customers

show customer count

show total orders for each customer

which customer placed the most orders

show all orders

show customers with their orders
```

---

## Current Version

### V1.0

Implemented:

* Natural Language to SQL
* PostgreSQL Query Execution
* Query History
* Recent Queries
* Execution Time Tracking
* React Frontend
* Dockerized Backend
* Dockerized Frontend
* Docker Compose

### Planned (V1.1)

* AI-generated insights from query results
* Query result summarization
* Business analytics suggestions
* Data trend detection

---

## Author

Madhu Sudhan Suravaram

B.Tech Computer Science (AI & ML)

AI Database Assistant Portfolio Project
