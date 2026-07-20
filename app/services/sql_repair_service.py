from app.core.ai_client import client, DIALECT_MAP
from app.services.schema_service import get_database_schema
from app.services.relationship_service import get_relationships
from app.db.database import get_db_type


def repair_sql(question, failed_sql, error_message):
    """Takes a question, failed SQL, and database error message, 
    and returns a corrected SQL query using the LLM."""

    schema = get_database_schema()
    relationships = get_relationships()
    db_type = get_db_type()
    dialect = DIALECT_MAP.get(db_type, "PostgreSQL")

    # Build dialect-specific SQL rules
    if db_type == "mysql":
        date_diff_rule = (
            "To calculate differences between dates/timestamps, use TIMESTAMPDIFF(unit, start_date, end_date) "
            "or DATEDIFF(end_date, start_date)."
        )
        limit_rule = "Use LIMIT when user asks for top N."
    elif db_type == "oracle":
        date_diff_rule = (
            "To calculate differences between dates, do NOT use TIMESTAMPDIFF. "
            "Instead, subtract dates directly (e.g., end_date - start_date) for days, "
            "or use MONTHS_BETWEEN(end_date, start_date) / 12 for years."
        )
        limit_rule = (
            "Oracle does NOT support the 'LIMIT' keyword. Use 'FETCH FIRST N ROWS ONLY' instead for any row limiting or top-N operations. "
            "In Oracle SQL, any recursive WITH clause (recursive CTE) MUST explicitly list the column aliases in the WITH header definition "
            "(e.g., `WITH CTE_NAME (COLUMN_A, COLUMN_B) AS (...)`)."
        )
    else:
        date_diff_rule = (
            "To calculate differences between dates/timestamps, do NOT use TIMESTAMPDIFF. "
            "Instead, subtract dates directly (e.g., end_date - start_date) for day differences, "
            "or use EXTRACT(YEAR FROM AGE(end_date, start_date)) for year differences."
        )
        limit_rule = "Use LIMIT when user asks for top N."

    prompt = f"""
You are an expert {dialect} Database Analyst. A generated SQL query failed to run because of a database error.
Your job is to repair the query so it is valid and executes successfully.

User's Original Question:
{question}

Failed SQL Query:
```sql
{failed_sql}
```

Database Error Message:
{error_message}

==================================================
DATABASE SCHEMA
==================================================
{schema}

==================================================
TABLE RELATIONSHIPS
==================================================
{relationships}

SQL REPAIR RULES:
1. Repair the failed query to address the database error.
2. Generate ONLY valid, executable {dialect} SQL.
3. Only output a SELECT or WITH query. Do NOT use INSERT, UPDATE, DELETE, DROP, or ALTER.
4. Keep the original query logic, but correct names of columns, tables, joins, aliases, syntax errors, or aggregate/GROUP BY constraints.
5. Return ONLY the executable SQL query. Do not explain anything, do not write comments, and do not wrap in markdown fences.
6. The first word must be SELECT or WITH.
7. {date_diff_rule}
8. {limit_rule}
9. Double-check all table aliases. Every alias (e.g. `f`, `t`, `leave`) must be explicitly defined in the FROM or JOIN clause of the query or subquery. Do not use undeclared table aliases.
10. Ensure matching parentheses. Verify that every open parenthesis '(' is properly balanced and closed.
11. Never append trailing semicolons (`;`) to the query.
12. Prevent ambiguous columns: when joining multiple tables, if tables share columns with the same name (e.g., customer_id, id, status, name), you MUST explicitly prefix those column references with the table name or alias (e.g., o.customer_id, c.customer_id) in all parts of the query (SELECT, JOIN, WHERE, GROUP BY, ORDER BY, subqueries) to prevent ORA-00918 or similar errors.
13. No bind variables/placeholders: Do NOT generate bind variables, parameter placeholders (e.g., :CUSTOMER_ID, :1, ?, %s), or prepared statement syntax. Every condition must use hardcoded values, column names, or actual literal values (e.g., use p.product_id = 1 instead of p.product_id = :PRODUCT_ID).
14. CTE naming: In any WITH clause, NEVER name a CTE (the temporary query name) the same as any table name in the database schema (e.g., do NOT write 'WITH products AS (SELECT ... FROM PRODUCTS)'). Choose a unique temporary name (e.g., 'product_cte') to prevent recursion errors (e.g. ORA-32039) on Oracle.



"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        sql = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )
        
        from app.services.ai_service import clean_sql_query
        sql = clean_sql_query(sql)

        # Post-process for PostgreSQL TIMESTAMPDIFF error
        if db_type == "postgres":
            sql = fix_postgresql_timestampdiff(sql)

        return sql

    except Exception:
        # If repair LLM call fails, return the original failed SQL so caller handles it
        return failed_sql


def fix_postgresql_timestampdiff(sql: str) -> str:
    """Post-processes SQL to replace TIMESTAMPDIFF with PostgreSQL equivalents,
    handling nested parentheses in arguments correctly."""
    import re
    
    pattern = r'(?i)\btimestampdiff\b'
    pos = 0
    while True:
        match = re.search(pattern, sql[pos:])
        if not match:
            break
            
        start_idx = pos + match.start()
        open_paren_idx = sql.find("(", start_idx)
        if open_paren_idx == -1:
            pos = start_idx + len(match.group(0))
            continue
            
        paren_count = 1
        i = open_paren_idx + 1
        args_str = ""
        while i < len(sql) and paren_count > 0:
            char = sql[i]
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
            
            if paren_count > 0:
                args_str += char
            i += 1
            
        if paren_count > 0:
            pos = start_idx + len(match.group(0))
            continue
            
        end_idx = i
        
        args = []
        current_arg = ""
        nested_parens = 0
        for char in args_str:
            if char == "(":
                nested_parens += 1
            elif char == ")":
                nested_parens -= 1
                
            if char == "," and nested_parens == 0:
                args.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char
        if current_arg:
            args.append(current_arg.strip())
            
        if len(args) != 3:
            pos = end_idx
            continue
            
        unit = args[0].lower().strip().strip("'").strip('"')
        start = args[1]
        end = args[2]
        
        replacement = ""
        if unit in ('year', 'yy', 'yyyy'):
            replacement = f"EXTRACT(YEAR FROM AGE({end}, {start}))"
        elif unit in ('month', 'm', 'mm'):
            replacement = f"(EXTRACT(YEAR FROM AGE({end}, {start})) * 12 + EXTRACT(MONTH FROM AGE({end}, {start})))"
        elif unit in ('day', 'd', 'dd'):
            replacement = f"({end}::date - {start}::date)"
        elif unit in ('hour', 'h', 'hh'):
            replacement = f"(EXTRACT(EPOCH FROM ({end} - {start})) / 3600)"
        elif unit in ('minute', 'mi', 'n'):
            replacement = f"(EXTRACT(EPOCH FROM ({end} - {start})) / 60)"
        elif unit in ('second', 'ss', 's'):
            replacement = f"EXTRACT(EPOCH FROM ({end} - {start}))"
        else:
            # Fallback if unit is unrecognized (e.g. TEXT or other hallucinations)
            replacement = f"EXTRACT(YEAR FROM AGE({end}, {start}))"
            
        sql = sql[:start_idx] + replacement + sql[end_idx:]
        pos = start_idx + len(replacement)
        
    return sql

