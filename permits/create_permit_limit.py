import psycopg2
from authorization import access_control
from model import permit_limit as pm
from db_helper import db_helper
from fastapi import HTTPException
from datetime import datetime
import traceback
from psycopg2 import errorcodes

def create_permit_limit(permit_limit: pm.PermitLimit, current_user: access_control.User):
    if not check_if_user_has_edit_permit_permission(permit_limit.municipality, current_user.acl):
        raise HTTPException(status_code=403, detail="This user is not allowed to change permit limits.")
    if permit_limit.effective_date < datetime.now().date() and not current_user.acl.allowed_to_change_permit_limit_historically:
        raise HTTPException(status_code=403, detail="This user is not allowed to change permit limits historically.")

    with db_helper.get_resource() as (cur, conn):
        try:
            res = insert_permit_limit(cur, permit_limit)
            conn.commit()
            return res
        except HTTPException as e:
            conn.rollback()
            raise e
        except psycopg2.IntegrityError as e:
            conn.rollback()
            if e.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise HTTPException(status_code=400, detail="A permit limit for the same municipality, system, modality and effective date already exists.")
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
    return

def insert_permit_limit(cur, permit_limit: pm.PermitLimit):
    stmt = """
    INSERT INTO permit_limit(municipality, system_id, modality, effective_date, minimum_vehicles, maximum_vehicles, minimal_number_of_trips_per_vehicle, max_parking_duration)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING permit_limit_id
    """
    cur.execute(stmt, (
        permit_limit.municipality,
        permit_limit.system_id,
        permit_limit.modality.value.lower(),
        permit_limit.effective_date,
        permit_limit.minimum_vehicles,
        permit_limit.maximum_vehicles,
        permit_limit.minimal_number_of_trips_per_vehicle,
        permit_limit.max_parking_duration
    ))
    permit_limit_id = cur.fetchone()
    permit_limit.permit_limit_id = permit_limit_id["permit_limit_id"]
    return permit_limit

def check_if_user_has_edit_permit_permission(municipality, acl):
    if acl.is_admin:
        return True
    if not acl.allowed_to_change_permit_limit:
        raise HTTPException(status_code=403, detail="This user is not allowed to change permit limits.")
    if municipality in acl.municipalities:
        return True
    raise HTTPException(status_code=403, detail="This user is not allowed to change permit limits in this municipality.")
