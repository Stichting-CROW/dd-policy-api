from authorization import access_control
from db_helper import db_helper
from fastapi import HTTPException
import traceback
from permits.queries import check_existing_permit_limit
from permits.create_permit_limit import check_if_user_has_edit_permit_permission

def delete_permit_limit(permit_limit_id: int, current_user: access_control.User):
    if not current_user.acl.allowed_to_change_permit_limit:
        raise HTTPException(status_code=403, detail="This user is not allowed to change permit limits.")

    with db_helper.get_resource() as (cur, conn):
        try:
            checks_current_permit = check_existing_permit_limit(cur, permit_limit_id)
            if checks_current_permit is None:
                raise HTTPException(status_code=404, detail="Permit limit not found.")
            
            permit_limit_in_past, municipality = checks_current_permit
            check_if_user_has_edit_permit_permission(municipality, current_user.acl)
            if permit_limit_in_past and not current_user.acl.allowed_to_change_permit_limit_historically:
                raise HTTPException(status_code=403, detail="This user is not allowed to change permit limits historically.")
            
            delete_permit_limit_query(cur, permit_limit_id)
            conn.commit()
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
    return

def delete_permit_limit_query(cur, permit_limit_id: int):
    stmt = """
    DELETE 
    FROM permit_limit
    WHERE permit_limit_id = %s
    """
    cur.execute(stmt, (
        permit_limit_id,
    ))
