# AI Database Assistant V1.0

## Overview

AI Database Assistant is a full-stack AI-powered application that converts natural language questions into SQL queries using Groq LLM. The application dynamically discovers database schemas, generates SQL queries, executes them securely against PostgreSQL, and displays the results through a React frontend.

The project supports complex SQL generation including joins, aggregations, ranking queries, and business analytics questions.

---

## Features

### AI Features

* Natural Language to SQL Conversion
* Groq LLM Integration
* Dynamic Schema Discovery
* Multi-table JOIN Generation
* Aggregation Query Support
* Business Analytics Query Support

### Backend Features

* FastAPI REST APIs
* PostgreSQL Integration
* Query Validation
* Query History Tracking
* Execution Time Monitoring
* Analytics Endpoints

### Frontend Features

* React + Vite
* Axios API Integration
* Dynamic Results Table
* Loading Indicators
* Error Handling
* Recent Query History
* Auto-run Recent Queries
* Query Statistics Dashboard

---

## Architecture

```text
React Frontend
       ↓
FastAPI Backend
       ↓
Groq LLM
       ↓
PostgreSQL Database
```

---

## Technology Stack

### Frontend

* React
* Vite
* Axios

### Backend

* FastAPI
* Python
* Pydantic

### Database

* PostgreSQL
* Psycopg2

### AI

* Groq API
* Llama Models

---

## Project Structure

```text
AI-Database-Assistant/

├── app/
│   ├── db/
│   │   └── database.py
│   │
│   ├── models/
│   │   └── schemas.py
│   │
│   ├── services/
│   │   ├── ai_service.py
│   │   ├── query_service.py
│   │   ├── history_service.py
│   │   └── schema_service.py
│   │
│   └── main.py
│
├── ai-db-frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── App.jsx
│   │   └── api.js
│   │
│   └── package.json
│
├── requirements.txt
├── README.md
└── .env
```

---

## API Endpoints

### Home

```http
GET /
```

### Ask AI

```http
POST /ask
```

Request:

```json
{
  "question": "show all customers"
}
```

---

### Query History

```http
GET /history
```

---

### Query Count

```http
GET /history/count
```

---

### Latest Queries

```http
GET /history/latest
```

---

## Example Questions

```text
show all customers

show customer emails

show all orders

show customer names and products they ordered

show total orders for each customer

which customer placed the most orders

show the customer who spent the most money
```

---

## Security

The application executes only SELECT statements.

This prevents accidental or malicious execution of:

* INSERT
* UPDATE
* DELETE
* DROP
* ALTER
* TRUNCATE

and keeps the database in read-only mode.

---

## Monitoring

The system automatically tracks:

* Query History
* Generated SQL
* Execution Time
* Query Statistics

---

## How to Run Backend

Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## How to Run Frontend

Navigate to frontend:

```bash
cd ai-db-frontend
```

Install dependencies:

```bash
npm install
npm install axios
```

Start React:

```bash
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

---

## Future Enhancements

### V1.1

* AI Insights Generation
* Charts and Visualizations
* Analytics Dashboard

### V2.0

* Predictive Analytics
* Revenue Forecasting
* Customer Churn Prediction
* Business Intelligence Features

---

## Author

Madhu Sudhan Suravaram

B.Tech Computer Science (AI & ML)

AI Database Assistant V1.0
