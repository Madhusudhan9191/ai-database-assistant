import json
import logging
from app.core.ai_client import client, DIALECT_MAP
from app.services.schema_service import get_database_schema
from app.db.database import get_db_type
from app.db.metadata_db import get_schema_dashboard, save_schema_dashboard

logger = logging.getLogger(__name__)

DEFAULT_DASHBOARD_CONFIG = {
    "kpis": {
        "total_revenue": "SELECT 0.0 AS total_revenue",
        "occupancy_rate": "SELECT 0.0 AS occupancy_rate",
        "active_tenants": "SELECT 0 AS active_tenants",
        "open_issues": "SELECT 0 AS open_issues"
    },
    "charts": {
        "monthly_trend": "SELECT '' AS month, 0.0 AS revenue WHERE 1=0",
        "category_expenses": "SELECT '' AS category, 0.0 AS expenses WHERE 1=0",
        "property_occupancy": "SELECT '' AS property_name, 0.0 AS occupancy_rate WHERE 1=0",
        "maintenance_priorities": "SELECT '' AS priority, 0 AS requests WHERE 1=0"
    }
}

def get_dynamic_dashboard_queries(schema_hash: str) -> dict:
    """
    Fetches the dynamic SQL dashboard queries from the cache,
    or generates them via AI if they are not yet cached for this schema.
    """
    # 1. Check SQLite cache
    cached_config = get_schema_dashboard(schema_hash)
    if cached_config:
        try:
            return json.loads(cached_config)
        except Exception as e:
            logger.error(f"Failed to parse cached dashboard config: {e}")

    # 2. Cache miss - generate via Groq LLM
    db_type = get_db_type()
    dialect = DIALECT_MAP.get(db_type, "PostgreSQL")
    schema_desc = get_database_schema()

    prompt = f"""
You are an expert {dialect} Database Analyst.
Your task is to analyze the database schema below and generate the exact SQL queries needed to build a business intelligence dashboard.

Here is the Database Schema:
{schema_desc}

The dashboard requires exactly 4 KPI queries and 4 Chart queries.
You must map this database schema to these KPIs and Charts. Find the most relevant tables and columns (e.g., if it's a sales DB, total_revenue is total sales sum, occupancy_rate could be orders per customer ratio or similar, active_tenants could be total active customers count, open_issues could be pending orders count, etc. If it's a completely different domain, map the concepts to the closest logical aggregates, or count tables).

You MUST return a JSON object with exactly the structure below, containing executable, single {dialect} SELECT queries.
Do NOT use markdown code fences in the JSON.
Do NOT explain anything.
Do NOT include SQL comments.

Required JSON Structure:
{{
  "kpis": {{
    "total_revenue": "SELECT <sum/count/value> AS total_revenue ...",
    "occupancy_rate": "SELECT <percentage/rate/ratio> AS occupancy_rate ...",
    "active_tenants": "SELECT <count> AS active_tenants ...",
    "open_issues": "SELECT <count> AS open_issues ..."
  }},
  "charts": {{
    "monthly_trend": "SELECT <month_name/date> AS month, <numeric_value> AS revenue GROUP BY ... ORDER BY ...",
    "category_expenses": "SELECT <category_name/type> AS category, <numeric_value> AS expenses GROUP BY ... ORDER BY ... DESC",
    "property_occupancy": "SELECT <name/attribute> AS property_name, <percentage/rate> AS occupancy_rate GROUP BY ...",
    "maintenance_priorities": "SELECT <status/priority> AS priority, <count> AS requests GROUP BY ... ORDER BY ... DESC"
  }}
}}

Ensure that:
1. Column aliases in SELECT statements match exactly the target keys:
   - total_revenue
   - occupancy_rate
   - active_tenants
   - open_issues
   - month, revenue
   - category, expenses
   - property_name, occupancy_rate
   - priority, requests
2. If the schema does not have logical tables to support some of these charts/KPIs, write fallback queries that query existing tables or count rows, but always return the correct column structure.
3. Every query must be a valid, executable {dialect} query. Do NOT use TIMESTAMPDIFF on PostgreSQL. Use LIMIT for top rows on PostgreSQL/MySQL, or FETCH FIRST for Oracle.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1
        )
        
        config_text = response.choices[0].message.content.strip()
        config_dict = json.loads(config_text)
        
        # Verify structure keys
        if "kpis" in config_dict and "charts" in config_dict:
            kpis = config_dict["kpis"]
            charts = config_dict["charts"]
            
            # Verify sub-keys
            required_kpis = ["total_revenue", "occupancy_rate", "active_tenants", "open_issues"]
            required_charts = ["monthly_trend", "category_expenses", "property_occupancy", "maintenance_priorities"]
            
            if all(k in kpis for k in required_kpis) and all(c in charts for c in required_charts):
                # Clean up queries (strip markdown / trailing semicolons if LLM added them)
                for k in required_kpis:
                    kpis[k] = kpis[k].strip().replace("```sql", "").replace("```", "").rstrip(";")
                for c in required_charts:
                    charts[c] = charts[c].strip().replace("```sql", "").replace("```", "").rstrip(";")
                
                # Save to cache
                save_schema_dashboard(schema_hash, json.dumps(config_dict))
                return config_dict

        logger.warning("Dynamic dashboard generation returned invalid JSON structure. Using fallback.")
    except Exception as e:
        logger.error(f"Failed to generate dynamic dashboard queries: {e}")
        
    return DEFAULT_DASHBOARD_CONFIG
