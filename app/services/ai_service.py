from app.core.ai_client import client, DIALECT_MAP
from app.services.schema_service import get_database_schema
from app.services.relationship_service import get_relationships
from app.db.database import get_db_type


def generate_sql(question):

    schema = get_database_schema()
    relationships = get_relationships()
    db_type = get_db_type()
    dialect = DIALECT_MAP.get(db_type, "PostgreSQL")

    # Build dialect-specific SQL rules
    if db_type == "mysql":
        limit_rule = "Use LIMIT when user asks for top N."
        text_filter_rule = (
            "For text filtering, use LIKE instead of = "
            "(MySQL is case-insensitive by default with utf8 collation)."
        )
        text_example = "status LIKE 'active'"
        date_diff_rule = (
            "To calculate differences between dates/timestamps, use TIMESTAMPDIFF(unit, start_date, end_date) "
            "or DATEDIFF(end_date, start_date)."
        )
    elif db_type == "oracle":
        limit_rule = (
            "Oracle does NOT support the 'LIMIT' keyword. Use 'FETCH FIRST N ROWS ONLY' instead for any row limiting or top-N operations. "
            "In Oracle SQL, any recursive WITH clause (recursive CTE) MUST explicitly list the column aliases in the WITH header definition "
            "(e.g., `WITH CTE_NAME (COLUMN_A, COLUMN_B) AS (...)`)."
        )
        text_filter_rule = (
            "For text filtering, use UPPER(column) LIKE UPPER(value) "
            "for case-insensitive matching."
        )
        text_example = "UPPER(status) LIKE UPPER('active')"
        date_diff_rule = (
            "To calculate differences between dates, do NOT use TIMESTAMPDIFF. "
            "Instead, subtract dates directly (e.g., end_date - start_date) for days, "
            "or use MONTHS_BETWEEN(end_date, start_date) / 12 for years."
        )
    else:
        limit_rule = "Use LIMIT when user asks for top N."
        text_filter_rule = (
            "For text filtering, use ILIKE instead of = "
            "whenever possible."
        )
        text_example = "status ILIKE 'active'"
        date_diff_rule = (
            "To calculate differences between dates/timestamps, do NOT use TIMESTAMPDIFF. "
            "Instead, subtract dates directly (e.g., end_date - start_date) for day differences, "
            "or use EXTRACT(YEAR FROM AGE(end_date, start_date)) for year differences."
        )

    prompt = f"""
You are an expert {dialect} Database Analyst.

Database Schema:

{schema}

==================================================
TABLE RELATIONSHIPS (auto-discovered foreign keys)
===================================================

{relationships}

Use these relationships to determine valid JOINs.
Never assume columns or foreign keys that are not listed above.
Never invent tables, columns, or foreign keys.
Use only schema columns and discovered relationships.

==================================================
AGGREGATION RULES
=================

When calculating aggregate metrics across related tables:

Always aggregate metrics separately before joining.

Preferred approach:

WITH metric_a AS (...),
metric_b AS (...)
SELECT ...

Avoid duplicate aggregation caused by:

* one-to-many joins
* many-to-many joins

Never multiply metrics accidentally by joining detail-level tables.

==================================================
SQL RULES
=========

1. Generate {dialect} SQL only.
2. Return exactly ONE query.
3. Return ONLY executable SQL.
4. Do NOT explain anything.
5. Do NOT provide alternatives.
6. Do NOT provide comments.
7. Do NOT wrap SQL in markdown.
8. The first word MUST be SELECT or WITH.
9. Use only tables and columns from the schema.
10. Never invent table names.
11. Never invent column names.
12. Use aliases where helpful.
13. Use GROUP BY when aggregation is required.
14. Use ORDER BY when ranking is requested.
15. {limit_rule}
16. Prefer CTEs for complex analytics.
17. Only SELECT queries are allowed.
18. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE.
19. {text_filter_rule}
20. Status values are case-insensitive.
21. Example:
    {text_example}
22. When filtering text columns, always prefer case-insensitive matching.
23. {date_diff_rule}
24. Double-check all table aliases. Every alias (e.g. `f`, `t`, `leave`) must be explicitly defined in the FROM or JOIN clause of the query or subquery. Do not use undeclared table aliases.
25. Ensure matching parentheses. Verify that every open parenthesis '(' is properly balanced and closed.
26. Never append trailing semicolons (`;`) to the query.
27. Prevent ambiguous columns: when joining multiple tables, if tables share columns with the same name (e.g., customer_id, id, status, name), you MUST explicitly prefix those column references with the table name or alias (e.g., o.customer_id, c.customer_id) in all parts of the query (SELECT, JOIN, WHERE, GROUP BY, ORDER BY, subqueries) to prevent ORA-00918 or similar errors.
28. No bind variables/placeholders: Do NOT generate bind variables, parameter placeholders (e.g., :CUSTOMER_ID, :1, ?, %s), or prepared statement syntax. Every condition must use hardcoded values, column names, or actual literal values (e.g., use p.product_id = 1 instead of p.product_id = :PRODUCT_ID).
29. CTE naming: In any WITH clause, NEVER name a CTE (the temporary query name) the same as any table name in the database schema (e.g., do NOT write 'WITH products AS (SELECT ... FROM PRODUCTS)'). Choose a unique temporary name (e.g., 'product_cte') to prevent recursion errors (e.g. ORA-32039) on Oracle.


Question:
{question}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    sql = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    sql = clean_sql_query(sql)

    # Post-process for PostgreSQL TIMESTAMPDIFF error
    if db_type == "postgres":
        sql = fix_postgresql_timestampdiff(sql)

    return sql


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


def clean_sql_query(sql: str) -> str:
    """Cleans up markdown, conversational prefixes, explanation suffixes, and formatting from LLM SQL."""
    if not sql:
        return ""
        
    # 1. Clean up markdown blocks
    sql = sql.replace("```sql", "")
    sql = sql.replace("```", "")
    sql = sql.strip()
    
    # 2. Extract starting from SELECT or WITH (case-insensitive) to skip conversational prefixes
    sql_lower = sql.lower()
    select_idx = sql_lower.find("select")
    with_idx = sql_lower.find("with")
    
    start_idx = -1
    if select_idx != -1 and with_idx != -1:
        start_idx = min(select_idx, with_idx)
    elif select_idx != -1:
        start_idx = select_idx
    elif with_idx != -1:
        start_idx = with_idx
        
    if start_idx != -1:
        sql = sql[start_idx:].strip()
        
    # 3. Remove common explanation suffixes
    for marker in ["However", "Note:", "Explanation:", "This query", "The query"]:
        if marker in sql:
            sql = sql.split(marker)[0].strip()
            
    # 4. Strip trailing semicolon if present
    # Note: we discard anything after the last semicolon if it exists
    if ";" in sql:
        sql = sql[: sql.rfind(";") + 1].rstrip(";")
        
    return sql.strip()