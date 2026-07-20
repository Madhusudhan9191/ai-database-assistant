from fastapi import APIRouter, HTTPException, Depends, Request
import time
import logging
import hashlib
import json
from datetime import datetime, timezone

from app.models.schemas import UserQuestion, QueryResponse
from app.services.ai_service import generate_sql
from app.services.query_service import execute_query
from app.services.query_validator import validate_sql
from app.services.history_service import save_query
from app.services.insight_service import generate_insights
from app.services.chart_decision_service import get_chart_decision
from app.services.chat_data_service import generate_chart_data
from app.services.kpi_service import detect_kpis
from app.services.error_intelligence import get_intelligent_error
from app.services.auth_service import get_current_user
from app.db.connection_store import active_connection
from app.services.schema_service import get_schema_hash
from app.db.metadata_db import log_security_event, get_cached_query, cache_query
from app.core.rate_limiter import ask_limiter

logger = logging.getLogger(__name__)
router = APIRouter()

CACHE_TTL_SECONDS = 600  # 10 minutes

@router.post("/ask", response_model=QueryResponse)
def ask_question(data: UserQuestion, request: Request, current_user: dict = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"

    # Connection guard
    if not active_connection.get("host"):
        raise HTTPException(
            status_code=400,
            detail="No active database connection. Please connect a database first.",
        )

    # Rate limiting
    if ask_limiter.is_rate_limited(client_ip):
        log_security_event(
            event_type="RATE_LIMIT_TRIGGERED",
            username=current_user.get("username", "unknown"),
            client_ip=client_ip,
            details="Rate limit exceeded on /ask endpoint (30 requests/minute)"
        )
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Maximum 30 queries per minute allowed."
        )

    question = data.question
    sql = None
    start_time = time.time()
    repair_attempted = 0
    repaired = 0

    try:
        # Schema Hash for Cache Key
        try:
            schema_hash = get_schema_hash()
        except Exception:
            schema_hash = "unknown"

        # Question Hash
        question_hash = hashlib.sha256(question.strip().lower().encode('utf-8')).hexdigest()

        # Cache check
        cached = get_cached_query(question_hash, schema_hash)
        if cached:
            try:
                # SQLite CURRENT_TIMESTAMP is UTC
                # Format: "2026-06-15 03:40:00" (or similar ISO-like structure depending on platform)
                # Parse to datetime
                created_str = cached["created_at"].replace("T", " ").split(".")[0]
                created_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - created_dt).total_seconds()
                if age < CACHE_TTL_SECONDS:
                    logger.info(f"Query cache hit for question: '{question}' (age: {int(age)}s)")
                    return json.loads(cached["result_json"])
            except Exception as cache_err:
                logger.warning(f"Error parsing cache created_at timestamp: {cache_err}")

        # Cache miss: Generate SQL
        sql = generate_sql(question)

        # Clean query
        from app.services.ai_service import clean_sql_query
        sql = clean_sql_query(sql)

        # Security Check
        validate_sql(sql)

        # Execute Query
        exec_start = time.time()
        try:
            result = execute_query(sql)
            execution_time_ms = int((time.time() - exec_start) * 1000)
        except Exception as initial_error:
            logger.warning(f"Initial SQL execution failed: {initial_error}. Attempting repair...")
            repaired_sql = None
            repair_attempted = 1
            try:
                from app.services.sql_repair_service import repair_sql
                repaired_sql = repair_sql(question, sql, str(initial_error))
                
                # Enforce safety check on the repaired SQL
                validate_sql(repaired_sql)
                
                # Execute repaired query
                exec_start = time.time()
                result = execute_query(repaired_sql)
                execution_time_ms = int((time.time() - exec_start) * 1000)
                
                # Log detailed success metrics for SQL repair
                logger.info(
                    f"SQL Repair Succeeded:\n"
                    f"  Question: {question}\n"
                    f"  Original SQL: {sql}\n"
                    f"  Error: {initial_error}\n"
                    f"  Repaired SQL: {repaired_sql}"
                )
                sql = repaired_sql
                repaired = 1
            except Exception as repair_error:
                # Log detailed failure metrics for SQL repair
                logger.error(
                    f"SQL Repair Failed:\n"
                    f"  Question: {question}\n"
                    f"  Original SQL: {sql}\n"
                    f"  Error: {initial_error}\n"
                    f"  Repaired SQL: {repaired_sql or 'Failed to generate'}\n"
                    f"  Repair Error: {repair_error}"
                )
                raise initial_error

        row_count = len(result) if isinstance(result, list) else 0

        # Generate Insights
        insights = generate_insights(
            question=question,
            data=result[:20] if isinstance(result, list) else result,
        )

        # Generate Chart Recommendation
        chart_decision = get_chart_decision(
            question=question,
            data=result,
        )

        chart_data = generate_chart_data(
            data=result,
            chart_type=chart_decision["chart_type"],
        )

        # Detect KPIs
        kpis = detect_kpis(result)

        # Generate Plain-English Explanation
        try:
            from app.services.explanation_service import explain_query
            explanation = explain_query(sql, question)
        except Exception as explanation_err:
            logger.error(f"Failed to generate query explanation: {explanation_err}")
            explanation = "This query retrieves data matching your question."

        # Save to audit log (success)
        save_query(
            question=question,
            sql=sql,
            execution_time_ms=execution_time_ms,
            success=True,
            row_count=row_count,
            chart_type=chart_decision["chart_type"],
            user_id=current_user["id"],
            repair_attempted=repair_attempted,
            repaired=repaired,
        )

        response_data = {
            "question": question,
            "generated_sql": sql,
            "execution_time_ms": execution_time_ms,
            "data": result,
            "insights": insights,
            "kpis": kpis,
            "show_chart": chart_decision["show_chart"],
            "chart_type": chart_decision["chart_type"],
            "chart_data": chart_data,
            "explanation": explanation,
        }

        # Convert response_data to JSON-serializable types using FastAPI's encoder
        from fastapi.encoders import jsonable_encoder
        serializable_data = jsonable_encoder(response_data)

        # Cache the success response
        cache_query(question_hash, schema_hash, sql, json.dumps(serializable_data))

        return serializable_data

    except HTTPException:
        execution_time_ms = int((time.time() - start_time) * 1000)
        save_query(
            question=question,
            sql=sql or "",
            execution_time_ms=execution_time_ms,
            success=False,
            error_message="Validation error",
            user_id=current_user["id"],
            repair_attempted=repair_attempted,
            repaired=repaired,
        )
        raise

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.exception("Query processing failed")
        smart_error = get_intelligent_error(e, sql)

        save_query(
            question=question,
            sql=sql or "",
            execution_time_ms=execution_time_ms,
            success=False,
            error_message=smart_error,
            user_id=current_user["id"],
            repair_attempted=repair_attempted,
            repaired=repaired,
        )

        raise HTTPException(
            status_code=500,
            detail=smart_error,
        )
