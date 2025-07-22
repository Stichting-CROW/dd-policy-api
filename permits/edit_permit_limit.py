from authorization import access_control
from db_helper import db_helper
from fastapi import HTTPException
import traceback
from model import permit_limit as pm
from permits.queries import check_existing_permit_limit
from permits.create_permit_limit import check_if_user_has_edit_permit_permission
from psycopg2 import errorcodes
import psycopg2

def edit_permit_limit(new_permit_limit: pm.PermitLimit, current_user: access_control.User):
    if not new_permit_limit.permit_limit_id:
        raise HTTPException(status_code=400, detail="Permit limit ID is required.")
    check_if_user_has_edit_permit_permission(new_permit_limit.municipality, current_user.acl)

    with db_helper.get_resource() as (cur, conn):
        try:
            checks_current_permit = check_existing_permit_limit(cur, new_permit_limit.permit_limit_id)
            if checks_current_permit is None:
                raise HTTPException(status_code=404, detail="Permit limit not found.")
            
            permit_limit_in_past, municipality = checks_current_permit
            check_if_user_has_edit_permit_permission(municipality, current_user.acl)
            if permit_limit_in_past and not current_user.acl.allowed_to_change_permit_limit_historically:
                raise HTTPException(status_code=403, detail="This user is not allowed to change permit limits historically.")
            
            update_permit_limit(cur, new_permit_limit)
            conn.commit()
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

def update_permit_limit(cur, permit_limit: pm.PermitLimit):
    stmt = """
    UPDATE permit_limit
    SET 
        municipality = %s,
        system_id = %s,
        modality = %s,
        effective_date = %s,
        minimum_vehicles = %s,
        maximum_vehicles = %s,
        minimal_number_of_trips_per_vehicle = %s,
        max_parking_duration = %s
    WHERE permit_limit_id = %s
    """
    cur.execute(stmt, (
        permit_limit.municipality,
        permit_limit.system_id,
        permit_limit.modality.value.lower(),
        permit_limit.effective_date,
        permit_limit.minimum_vehicles,
        permit_limit.maximum_vehicles,
        permit_limit.minimal_number_of_trips_per_vehicle,
        permit_limit.max_parking_duration,
        permit_limit.permit_limit_id
    ))
    return permit_limit
