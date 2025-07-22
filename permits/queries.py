

def check_existing_permit_limit(cur, permit_limit_id: int):
    stmt = """
    SELECT CURRENT_DATE > effective_date AS is_in_past, municipality
    FROM permit_limit
    WHERE permit_limit_id = %s;
    """
    cur.execute(stmt, (
        permit_limit_id,
    ))
    return cur.fetchone()