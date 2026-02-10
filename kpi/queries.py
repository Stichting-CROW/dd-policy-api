def check_existing_geometry_operator_modality_limit(cur, limit_id: int):
    """Check if a geometry operator modality limit exists and return its status."""
    stmt = """
    SELECT CURRENT_DATE > effective_date AS is_in_past
    FROM geometry_operator_modality_limit
    WHERE geometry_operator_modality_limit_id = %s;
    """
    cur.execute(stmt, (limit_id,))
    result = cur.fetchone()
    if result:
        return result["is_in_past"]
    return None

