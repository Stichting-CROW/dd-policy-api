from authorization import access_control
from db_helper import db_helper
from fastapi import HTTPException
import traceback
from model import permit_limit as pm
from permits.queries import check_existing_permit_limit
from permits.create_permit_limit import check_if_user_has_edit_permit_permission
from psycopg2 import errorcodes
import psycopg2
from modalities import Modality

def get_permit_limit_history(municipality: str, system_id: str, modality: Modality):
    with db_helper.get_resource() as (cur, conn):
        try:
            res = query_permit_limit_history(cur, municipality, system_id, modality)
            for index, row in enumerate(res):
                res[index]["modality"] = row["modality"].lower()

            return res
        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
        
def query_permit_limit_history(cur, municipality: str, system_id: str, modality: Modality):
    stmt = """
    SELECT *,
        LEAD(effective_date, 1) OVER (
            PARTITION BY municipality, system_id, modality
            ORDER BY effective_date
        ) AS end_date
    FROM permit_limit
    WHERE municipality = %s
    AND system_id = %s
    AND modality = %s
    ORDER BY effective_date DESC
    """
    cur.execute(stmt, (municipality, system_id, modality.value.lower()))
    return cur.fetchall()
