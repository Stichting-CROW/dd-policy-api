def check_existing_kpi_threshold(cur, threshold_id: int):
    """Check if a KPI threshold exists and return its status."""
    stmt = """
    SELECT CURRENT_DATE > effective_date AS is_in_past, municipality
    FROM permit_limit
    WHERE permit_limit_id = %s;
    """
    cur.execute(stmt, (threshold_id,))
    return cur.fetchone()


# Backwards compatibility alias
check_existing_permit_limit = check_existing_kpi_threshold