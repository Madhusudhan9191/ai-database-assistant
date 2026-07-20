from app.db.database import get_connection, get_db_type


def get_relationships():
    """Auto-discovers foreign key relationships from the database.
    Returns a formatted string describing all FK relationships."""

    db_type = get_db_type()
    conn = get_connection()
    cur = conn.cursor()

    try:

        if db_type == "oracle":
            cur.execute("""
                SELECT
                    a.table_name AS source_table,
                    a.column_name AS source_column,
                    c_pk.table_name AS target_table,
                    b.column_name AS target_column
                FROM user_cons_columns a
                JOIN user_constraints c
                    ON a.constraint_name = c.constraint_name
                JOIN user_constraints c_pk
                    ON c.r_constraint_name = c_pk.constraint_name
                JOIN user_cons_columns b
                    ON c_pk.constraint_name = b.constraint_name
                    AND a.position = b.position
                WHERE c.constraint_type = 'R'
                ORDER BY a.table_name
            """)

        elif db_type == "mysql":
            cur.execute("""
                SELECT
                    TABLE_NAME AS source_table,
                    COLUMN_NAME AS source_column,
                    REFERENCED_TABLE_NAME AS target_table,
                    REFERENCED_COLUMN_NAME AS target_column
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY TABLE_NAME
            """)

        else:
            cur.execute("""
                SELECT
                    tc.table_name AS source_table,
                    kcu.column_name AS source_column,
                    ccu.table_name AS target_table,
                    ccu.column_name AS target_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                    AND tc.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
                ORDER BY tc.table_name
            """)

        rows = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    if not rows:
        # Fallback: logical relationship auto-discovery based on column naming conventions
        logical_relations = _discover_logical_relationships()
        if logical_relations:
            return logical_relations
        return "No foreign key relationships found."

    result = ""
    current_table = None

    for source_table, source_column, target_table, target_column in rows:

        if source_table != current_table:
            result += f"\n{source_table}:\n"
            current_table = source_table

        result += (
            f"  {source_column} -> "
            f"{target_table}.{target_column}\n"
        )

    return result.strip()


def _discover_logical_relationships():
    """Fallbacks to logical relationship mapping if no physical FKs exist.
    Matches tables where column name corresponds to another table's PK (e.g. room_id in rooms)."""
    db_type = get_db_type()
    conn = None
    cur = None
    cols_data = []
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if db_type == "oracle":
            cur.execute("""
                SELECT table_name, column_name 
                FROM user_tab_columns 
                ORDER BY table_name
            """)
        elif db_type == "mysql":
            cur.execute("""
                SELECT table_name, column_name 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                ORDER BY table_name
            """)
        else:
            cur.execute("""
                SELECT table_name, column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
        cols_data = cur.fetchall()
    except Exception:
        return ""
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
                
    if not cols_data:
        return ""
        
    # Group columns by table
    tables_cols = {}
    for table, col in cols_data:
        t_low = table.lower()
        if t_low in ["query_logs", "query_history"]:
            continue
        if t_low not in tables_cols:
            tables_cols[t_low] = []
        tables_cols[t_low].append(col.lower())
        
    relations = {}
    
    for tbl, cols in tables_cols.items():
        for col in cols:
            if col.endswith("_id") and col != "id":
                target_base = col[:-3]  # e.g., "room" from "room_id"
                
                # Look for matching table name (singular or plural, e.g., room, rooms, owner, owners)
                possible_targets = [target_base, f"{target_base}s", f"{target_base}es"]
                for pt in possible_targets:
                    if pt in tables_cols and pt != tbl:
                        # Target table exists and has 'id' or matching column
                        if "id" in tables_cols[pt] or col in tables_cols[pt]:
                            target_col = col if col in tables_cols[pt] else "id"
                            if tbl not in relations:
                                relations[tbl] = []
                            relations[tbl].append(f"  {col} -> {pt}.{target_col}")
                            break
                            
    if not relations:
        return ""
        
    result = ""
    for tbl, links in sorted(relations.items()):
        result += f"\n{tbl}:\n" + "\n".join(links) + "\n"
        
    return result.strip()