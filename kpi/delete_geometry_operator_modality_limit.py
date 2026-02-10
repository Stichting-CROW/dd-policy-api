from authorization import access_control
from db_helper import db_helper
from fastapi import HTTPException
import traceback
from kpi.queries import check_existing_geometry_operator_modality_limit
from kpi.create_geometry_operator_modality_limit import check_if_user_has_edit_permission


def delete_geometry_operator_modality_limit(limit_id: int, current_user: access_control.User):
    """Delete an existing geometry operator modality limit configuration."""
    if not current_user.acl.allowed_to_change_geometry_operator_modality_limit:
        raise HTTPException(status_code=403, detail="This user is not allowed to change geometry operator modality limits.")

    with db_helper.get_resource() as (cur, conn):
        try:
            is_in_past, geometry_ref = check_existing_geometry_operator_modality_limit(cur, limit_id)
            if is_in_past is None:
                raise HTTPException(status_code=404, detail="Geometry operator modality limit not found.")
            
            if geometry_ref and not check_if_user_has_edit_permission(geometry_ref, current_user.acl):
                raise HTTPException(status_code=403, detail="This user is not allowed to change geometry operator modality limits historically.")
        
            delete_geometry_operator_modality_limit_query(cur, limit_id)
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


def delete_geometry_operator_modality_limit_query(cur, limit_id: int):
    """Delete a geometry operator modality limit from the database."""
    stmt = """
    DELETE 
    FROM geometry_operator_modality_limit
    WHERE geometry_operator_modality_limit_id = %s
    """
    cur.execute(stmt, (limit_id,))