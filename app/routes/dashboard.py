from fastapi import APIRouter, HTTPException, Depends
import logging
import time
from datetime import datetime
from app.services.query_service import execute_query
from app.services.query_validator import validate_sql
from app.services.chat_data_service import generate_chart_data
from app.services.saved_reports_service import get_compatible_reports, increment_report_execution
from app.services.auth_service import get_current_user
from app.services.schema_service import get_schema_hash
from app.db.connection_store import active_connection
from app.services.dashboard_service import get_dynamic_dashboard_queries

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory TTL Cache: { "report_id:schema_hash": { "timestamp": float, "chart_data": dict } }
_report_cache = {}
CACHE_TTL_SECONDS = 60
MAX_DASHBOARD_REPORTS = 10

@router.get("/dashboard/summary")
def get_dashboard_summary(current_user: dict = Depends(get_current_user)):
    try:
        # Check connection first
        if not active_connection.get("host"):
            return {
                "kpis": {
                    "total_revenue": 0.0,
                    "occupancy_rate": 0.0,
                    "active_tenants": 0,
                    "open_issues": 0
                },
                "charts": {
                    "monthly_trend": {"chart_type": "area", "data": []},
                    "category_expenses": {"chart_type": "bar", "data": []},
                    "property_occupancy": {"chart_type": "bar", "data": []},
                    "maintenance_priorities": {"chart_type": "pie", "data": []}
                },
                "saved_reports": [],
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        db_type = active_connection.get("db_type", "postgres")
        db_name = active_connection.get("database", "")
        
        # Calculate schema fingerprint
        try:
            schema_hash = get_schema_hash()
        except Exception as e:
            logger.warning(f"Failed to generate schema hash for dashboard: {e}")
            schema_hash = "unknown"

        # Fetch KPIs and charts using dynamic queries mapped to schema
        dashboard_config = get_dynamic_dashboard_queries(schema_hash)

        # 1. Fetch KPIs
        # Total Revenue
        try:
            rev_res = execute_query(dashboard_config["kpis"]["total_revenue"])
            val = rev_res[0]["total_revenue"] if rev_res and "total_revenue" in rev_res[0] else next(iter(rev_res[0].values())) if rev_res else 0.0
            total_revenue = float(val) if val is not None else 0.0
        except Exception as e:
            logger.warning(f"Error fetching total revenue: {e}")
            total_revenue = 0.0

        # Occupancy Rate
        try:
            occ_res = execute_query(dashboard_config["kpis"]["occupancy_rate"])
            val = occ_res[0]["occupancy_rate"] if occ_res and "occupancy_rate" in occ_res[0] else next(iter(occ_res[0].values())) if occ_res else 0.0
            occupancy_rate = float(val) if val is not None else 0.0
        except Exception as e:
            logger.warning(f"Error fetching occupancy rate: {e}")
            occupancy_rate = 0.0

        # Active Tenants
        try:
            ten_res = execute_query(dashboard_config["kpis"]["active_tenants"])
            val = ten_res[0]["active_tenants"] if ten_res and "active_tenants" in ten_res[0] else next(iter(ten_res[0].values())) if ten_res else 0
            active_tenants = int(val) if val is not None else 0
        except Exception as e:
            logger.warning(f"Error fetching active tenants: {e}")
            active_tenants = 0

        # Open Issues
        try:
            issue_res = execute_query(dashboard_config["kpis"]["open_issues"])
            val = issue_res[0]["open_issues"] if issue_res and "open_issues" in issue_res[0] else next(iter(issue_res[0].values())) if issue_res else 0
            open_issues = int(val) if val is not None else 0
        except Exception as e:
            logger.warning(f"Error fetching open issues: {e}")
            open_issues = 0

        kpis = {
            "total_revenue": total_revenue,
            "occupancy_rate": occupancy_rate,
            "active_tenants": active_tenants,
            "open_issues": open_issues
        }

        # 2. Fetch Charts Data
        charts = {}

        # Monthly Trend Chart (Area/Line)
        try:
            monthly_res = execute_query(dashboard_config["charts"]["monthly_trend"])
            monthly_chart_data = []
            for row in monthly_res:
                m_val = row.get("month") if "month" in row else next(iter(row.values())) if row else ""
                r_val = row.get("revenue") if "revenue" in row else list(row.values())[1] if len(row) > 1 else 0.0
                monthly_chart_data.append({
                    "month": str(m_val) if m_val is not None else "",
                    "revenue": float(r_val) if r_val is not None else 0.0
                })
            charts["monthly_trend"] = {
                "chart_type": "area",
                "data": monthly_chart_data
            }
        except Exception as e:
            logger.warning(f"Error creating monthly trend chart: {e}")
            charts["monthly_trend"] = {"chart_type": "area", "data": []}

        # Category Expenses Chart (Bar)
        try:
            expense_res = execute_query(dashboard_config["charts"]["category_expenses"])
            charts["category_expenses"] = {
                "chart_type": "bar",
                "data": [
                    {
                        "category": str(row.get("category") if "category" in row else next(iter(row.values())) if row else ""),
                        "expenses": float(row.get("expenses") if "expenses" in row else list(row.values())[1] if len(row) > 1 else 0.0)
                    }
                    for row in expense_res
                ]
            }
        except Exception as e:
            logger.warning(f"Error creating category expenses chart: {e}")
            charts["category_expenses"] = {"chart_type": "bar", "data": []}

        # Property Occupancy Comparison (Bar)
        try:
            prop_res = execute_query(dashboard_config["charts"]["property_occupancy"])
            charts["property_occupancy"] = {
                "chart_type": "bar",
                "data": [
                    {
                        "property_name": str(row.get("property_name") if "property_name" in row else next(iter(row.values())) if row else ""),
                        "occupancy_rate": float(row.get("occupancy_rate") if "occupancy_rate" in row else list(row.values())[1] if len(row) > 1 else 0.0)
                    }
                    for row in prop_res
                ]
            }
        except Exception as e:
            logger.warning(f"Error creating property occupancy chart: {e}")
            charts["property_occupancy"] = {"chart_type": "bar", "data": []}

        # Maintenance Priorities Chart (Pie)
        try:
            maint_res = execute_query(dashboard_config["charts"]["maintenance_priorities"])
            charts["maintenance_priorities"] = {
                "chart_type": "pie",
                "data": [
                    {
                        "priority": str(row.get("priority") if "priority" in row else next(iter(row.values())) if row else ""),
                        "requests": int(row.get("requests") if "requests" in row else list(row.values())[1] if len(row) > 1 else 0)
                    }
                    for row in maint_res
                ]
            }
        except Exception as e:
            logger.warning(f"Error creating maintenance priorities chart: {e}")
            charts["maintenance_priorities"] = {"chart_type": "pie", "data": []}

        # 3. Retrieve and Execute Compatible Saved Reports (Cap at 10)
        saved_reports_out = []
        try:
            reports = get_compatible_reports(db_type, db_name, schema_hash, current_user["id"])
            # Limit to maximum reports
            active_reports = reports[:MAX_DASHBOARD_REPORTS]
            
            for report in active_reports:
                report_id = report["id"]
                cache_key = f"{report_id}:{schema_hash}:{current_user['id']}"
                now = time.time()
                
                # Check Cache
                if cache_key in _report_cache and (now - _report_cache[cache_key]["timestamp"]) < CACHE_TTL_SECONDS:
                    formatted_chart = _report_cache[cache_key]["chart_data"]
                    logger.debug(f"Using cached result for saved report {report_id}")
                else:
                    # Execute SQL securely with validation
                    sql = report["generated_sql"]
                    try:
                        # Safety check on SQL query
                        validate_sql(sql)
                        
                        exec_start = time.time()
                        raw_result = execute_query(sql)
                        execution_time_ms = int((time.time() - exec_start) * 1000)
                        
                        # Format for Recharts
                        formatted_chart = generate_chart_data(raw_result, report["chart_type"])
                        
                        # Cache the outcome
                        _report_cache[cache_key] = {
                            "timestamp": now,
                            "chart_data": formatted_chart
                        }
                        
                        # Async/background stats logging
                        increment_report_execution(report_id, execution_time_ms)
                    except Exception as exec_err:
                        logger.exception(f"Failed to execute saved report {report_id} ({report['report_name']})")
                        formatted_chart = {
                            "chart_type": report["chart_type"],
                            "data": [],
                            "error": str(exec_err)
                        }

                saved_reports_out.append({
                    "id": report["id"],
                    "report_name": report["report_name"],
                    "question": report["question"],
                    "generated_sql": report["generated_sql"],
                    "chart_type": report["chart_type"],
                    "chart_data": formatted_chart
                })

        except Exception as re_err:
            logger.exception("Failed to fetch saved reports for dashboard")

        return {
            "kpis": kpis,
            "charts": charts,
            "saved_reports": saved_reports_out,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        logger.exception("Failed to load dashboard summary")
        raise HTTPException(status_code=500, detail=f"Database execution error: {str(e)}")
