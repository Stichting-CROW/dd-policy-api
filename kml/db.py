from db_helper import db_helper

def get_zones_to_export(municipality):
    stmt = """
        SELECT geography_id, geographies.name as name, geography_type, effective_date, published_date, stop_id, ST_ASTEXT(area) as area 
        FROM geographies
        JOIN zones 
        USING(zone_id)
        LEFT JOIN stops
        USING(geography_id)
        WHERE retire_date IS NULL
        AND (false = %(municipality_code_is_set)s OR municipality = %(municipality_code)s);
    """
    with db_helper.get_resource() as (cur, conn):
        try:
            cur.execute(stmt, {
                "municipality_code_is_set": municipality != None,
                "municipality_code": municipality
            })
            return cur.fetchall()
        except Exception as e:
            conn.rollback()
            print(e)
            return False
        
def get_municipality_border(municipality_code: str):
    stmt = """
        SELECT area 
        FROM zones 
        WHERE municipality = %(municipality_code)s
        AND zone_type = 'municipality';
    """
    with db_helper.get_resource() as (cur, conn):
        try:
            cur.execute(stmt, {
                "municipality_code": municipality_code
            })
            return cur.fetchone()["area"]
        except Exception as e:
            conn.rollback()
            return None


