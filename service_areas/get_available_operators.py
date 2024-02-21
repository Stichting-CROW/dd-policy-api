from db_helper import db_helper
import json
from fastapi import HTTPException
from pydantic import BaseModel

class AvailableOperatorResponse(BaseModel):
    operators_with_service_area: list[str]

def get_available_operators(municipalities):
    with db_helper.get_resource() as (cur, conn):
        try:
            res = query_available_operators(cur, municipalities=municipalities)
            return AvailableOperatorResponse(operators_with_service_area=res["active_operators"])
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")


def query_available_operators(cur, municipalities):
    stmt = """
        SELECT ARRAY_AGG(DISTINCT(operator)) AS active_operators 
        FROM service_area 
        WHERE municipality = ANY(%s)
        AND valid_until IS NULL;
    """
    cur.execute(stmt, (municipalities,))
    return cur.fetchone()
