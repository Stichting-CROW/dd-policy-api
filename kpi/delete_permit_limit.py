from authorization import access_control
from db_helper import db_helper
from fastapi import HTTPException
import traceback
from permits.queries import check_existing_kpi_threshold
from permits.create_permit_limit import check_if_user_has_edit_permission


def delete_kpi_threshold(threshold_id: int, current_user: access_control.User):
    """Delete an existing KPI threshold configuration."""
    if not current_user.acl.allowed_to_change_permit_limit:
        raise HTTPException(status_code=403, detail="This user is not allowed to change KPI thresholds.")

    with db_helper.get_resource() as (cur, conn):
        try:
            checks_current = check_existing_kpi_threshold(cur, threshold_id)
            if checks_current is None:
                raise HTTPException(status_code=404, detail="KPI threshold not found.")
            
            threshold_in_past, municipality = checks_current
            check_if_user_has_edit_permission(municipality, current_user.acl)
            if threshold_in_past and not current_user.acl.allowed_to_change_permit_limit_historically:
                raise HTTPException(status_code=403, detail="This user is not allowed to change KPI thresholds historically.")
            
            delete_kpi_threshold_query(cur, threshold_id)
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


def delete_kpi_threshold_query(cur, threshold_id: int):
    """Delete a KPI threshold from the database."""
    stmt = """
    DELETE 
    FROM permit_limit
    WHERE permit_limit_id = %s
    """
    cur.execute(stmt, (threshold_id,))


# Backwards compatibility aliases
delete_permit_limit = delete_kpi_threshold
delete_permit_limit_query = delete_kpi_threshold_query
