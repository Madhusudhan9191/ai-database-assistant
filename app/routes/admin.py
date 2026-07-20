from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import logging
import io
import csv

from app.services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/admin/stats")
def get_admin_stats(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    from app.db.metadata_db import get_metadata_connection
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        
        # 1. Total users
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        
        # 2. Total saved reports
        cur.execute("SELECT COUNT(*) FROM saved_reports WHERE is_active = 1")
        total_reports = cur.fetchone()[0]
        
        # 3. Total queries
        cur.execute("SELECT COUNT(*) FROM query_logs")
        total_queries = cur.fetchone()[0]
        
        # 4. Successful vs Failed queries
        cur.execute("SELECT COUNT(*) FROM query_logs WHERE success = 1")
        success_queries = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM query_logs WHERE success = 0")
        failed_queries = cur.fetchone()[0]
        
        # 5. Active favorites
        cur.execute("SELECT COUNT(*) FROM favorites")
        total_favorites = cur.fetchone()[0]
        
        # 6. Repair metrics
        cur.execute("SELECT COALESCE(SUM(repair_attempted), 0), COALESCE(SUM(repaired), 0) FROM query_logs")
        row = cur.fetchone()
        repair_attempts = row[0]
        repair_successes = row[1]
        
        repair_success_rate = 0.0
        if repair_attempts > 0:
            repair_success_rate = round((repair_successes / repair_attempts) * 100, 2)
            
        # 7. Daily query metrics (last 30 days)
        cur.execute("""
            SELECT date(created_at) as query_date,
                   COUNT(*) as total,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                   SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failure_count,
                   SUM(COALESCE(repair_attempted, 0)) as repair_attempts,
                   SUM(COALESCE(repaired, 0)) as repaired_count
            FROM query_logs
            GROUP BY query_date
            ORDER BY query_date ASC
            LIMIT 30
        """)
        daily_rows = cur.fetchall()
        daily_metrics = []
        for r in daily_rows:
            r_dict = dict(r) if hasattr(r, "keys") else {cur.description[i][0]: val for i, val in enumerate(r)}
            daily_metrics.append({
                "date": r_dict.get("query_date"),
                "total": r_dict.get("total"),
                "success": r_dict.get("success_count"),
                "failed": r_dict.get("failure_count"),
                "repair_attempts": r_dict.get("repair_attempts"),
                "repaired": r_dict.get("repaired_count")
            })
            
        return {
            "total_users": total_users,
            "total_reports": total_reports,
            "total_queries": total_queries,
            "success_queries": success_queries,
            "failed_queries": failed_queries,
            "total_favorites": total_favorites,
            "repair_attempts": repair_attempts,
            "repair_successes": repair_successes,
            "repair_success_rate": repair_success_rate,
            "daily_metrics": daily_metrics
        }
    except Exception as e:
        logger.exception("Failed to fetch admin stats")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch admin statistics. Please contact the system administrator."
        )
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@router.get("/admin/audit-trail/export")
def export_audit_trail(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    from app.db.metadata_db import get_metadata_connection
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, event_type, username, client_ip, details, created_at 
            FROM security_events 
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Event Type", "Username", "Client IP", "Details", "Timestamp"])
        
        for row in rows:
            writer.writerow([
                row["id"], 
                row["event_type"], 
                row["username"], 
                row["client_ip"], 
                row["details"], 
                row["created_at"]
            ])
            
        output.seek(0)
        
        response = StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = "attachment; filename=audit_trail.csv"
        return response
    except Exception as e:
        logger.exception("Failed to export audit trail")
        raise HTTPException(
            status_code=500, 
            detail=f"Export failed: {str(e)}"
        )
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
