import psycopg2
from authorization import access_control
from model.geometry_operator_modality_limit import GeometryOperatorModalityLimit, GeometryOperatorModalityLimitResponse
from db_helper import db_helper
from fastapi import HTTPException
from datetime import datetime
import traceback
from psycopg2 import errorcodes


def create_geometry_operator_modality_limit(limit: GeometryOperatorModalityLimit, current_user: access_control.User):
    """Create a new geometry operator modality limit configuration."""
    if not check_if_user_has_edit_permission(limit.geometry_ref, current_user.acl):
        raise HTTPException(status_code=403, detail="This user is not allowed to change geometry operator modality limits.")

    with db_helper.get_resource() as (cur, conn):
        try:
            res = insert_geometry_operator_modality_limit(cur, limit)
            conn.commit()
            return res
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


def insert_geometry_operator_modality_limit(cur, limit: GeometryOperatorModalityLimit):
    """Insert a new geometry operator modality limit into the database."""
    stmt = """
    INSERT INTO geometry_operator_modality_limit(geometry_ref, operator, form_factor, propulsion_type, effective_date, limits)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING geometry_operator_modality_limit_id
    """
    db_data = limit.to_db_dict()
    cur.execute(stmt, (
        db_data['geometry_ref'],
        db_data['operator'],
        db_data['form_factor'],
        db_data['propulsion_type'],
        db_data['effective_date'],
        db_data['limits']
    ))
    result = cur.fetchone()
    return GeometryOperatorModalityLimitResponse(
        geometry_operator_modality_limit_id=result["geometry_operator_modality_limit_id"],
        geometry_ref=limit.geometry_ref,
        operator=limit.operator,
        form_factor=limit.form_factor,
        propulsion_type=limit.propulsion_type,
        effective_date=limit.effective_date,
        limits=limit.limits
    )


def check_if_user_has_edit_permission(geometry_ref: str, acl):
    """Check if user has permission to edit geometry operator modality limits."""
    if acl.is_admin:
        return True
    if not acl.allowed_to_change_geometry_operator_modality_limit:
        raise HTTPException(status_code=403, detail="This user is not allowed to change geometry operator modality limits.")
    # Extract municipality from geometry_ref (e.g., 'cbs:GM0014' -> 'GM0014')
    municipality = geometry_ref.split(':')[-1] if ':' in geometry_ref else geometry_ref
    if municipality in acl.municipalities:
        return True
    raise HTTPException(status_code=403, detail="This user is not allowed to change geometry operator modality limits in this municipality.")

