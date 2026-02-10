from authorization import access_control
from db_helper import db_helper
from fastapi import HTTPException
import traceback
from model.geometry_operator_modality_limit import GeometryOperatorModalityLimit
from kpi.queries import check_existing_geometry_operator_modality_limit
from kpi.create_geometry_operator_modality_limit import check_if_user_has_edit_permission
from psycopg2 import errorcodes
import psycopg2


def edit_geometry_operator_modality_limit(limit: GeometryOperatorModalityLimit, current_user: access_control.User):
    """Edit an existing geometry operator modality limit configuration."""
    if not limit.geometry_operator_modality_limit_id:
        raise HTTPException(status_code=400, detail="Geometry operator modality limit ID is required.")
    check_if_user_has_edit_permission(limit.geometry_ref, current_user.acl)

    with db_helper.get_resource() as (cur, conn):
        try:
            is_in_past, geometry_ref = check_existing_geometry_operator_modality_limit(cur, limit.geometry_operator_modality_limit_id)
            if is_in_past is None:
                raise HTTPException(status_code=404, detail="Geometry operator modality limit not found.")
            
            if geometry_ref and not check_if_user_has_edit_permission(geometry_ref, current_user.acl):
                raise HTTPException(status_code=403, detail="This user is not allowed to change geometry operator modality limits historically.")   
            
            
            update_geometry_operator_modality_limit(cur, limit)
            conn.commit()
        except HTTPException as e:
            conn.rollback()
            raise e
        except psycopg2.IntegrityError as e:
            conn.rollback()
            if e.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise HTTPException(status_code=400, detail="A geometry operator modality limit for the same geometry_ref, operator, form_factor, propulsion_type and effective date already exists.")
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
    return


def update_geometry_operator_modality_limit(cur, limit: GeometryOperatorModalityLimit):
    """Update an existing geometry operator modality limit in the database."""
    stmt = """
    UPDATE geometry_operator_modality_limit
    SET 
        geometry_ref = %s,
        operator = %s,
        form_factor = %s,
        propulsion_type = %s,
        effective_date = %s,
        limits = %s
    WHERE geometry_operator_modality_limit_id = %s
    """
    db_data = limit.to_db_dict()
    cur.execute(stmt, (
        db_data['geometry_ref'],
        db_data['operator'],
        db_data['form_factor'],
        db_data['propulsion_type'],
        db_data['effective_date'],
        db_data['limits'],
        limit.geometry_operator_modality_limit_id
    ))
    return limit


