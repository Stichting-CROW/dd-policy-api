import psycopg2
from authorization import access_control
from model.kpi import KPIThreshold
from db_helper import db_helper
from fastapi import HTTPException
from datetime import datetime
import traceback
from psycopg2 import errorcodes


def create_kpi_threshold(threshold: KPIThreshold, current_user: access_control.User):
    """Create a new KPI threshold configuration."""
    if not check_if_user_has_edit_permission(threshold.municipality, current_user.acl):
        raise HTTPException(status_code=403, detail="This user is not allowed to change KPI thresholds.")
    if threshold.effective_date < datetime.now().date() and not current_user.acl.allowed_to_change_permit_limit_historically:
        raise HTTPException(status_code=403, detail="This user is not allowed to change KPI thresholds historically.")

    with db_helper.get_resource() as (cur, conn):
        try:
            res = insert_kpi_threshold(cur, threshold)
            conn.commit()
            return res
        except HTTPException as e:
            conn.rollback()
            raise e
        except psycopg2.IntegrityError as e:
            conn.rollback()
            if e.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise HTTPException(status_code=400, detail="A KPI threshold for the same municipality, system, modality and effective date already exists.")
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
    return


def insert_kpi_threshold(cur, threshold: KPIThreshold):
    """Insert a new KPI threshold into the database."""
    stmt = """
    INSERT INTO permit_limit(municipality, system_id, modality, effective_date, minimum_vehicles, maximum_vehicles, minimal_number_of_trips_per_vehicle, max_parking_duration)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING permit_limit_id
    """
    cur.execute(stmt, (
        threshold.municipality,
        threshold.system_id,
        threshold.modality.value.lower(),
        threshold.effective_date,
        threshold.min_vehicles,
        threshold.max_vehicles,
        threshold.min_trips_per_vehicle,
        threshold.max_parking_duration
    ))
    result = cur.fetchone()
    threshold.kpi_threshold_id = result["permit_limit_id"]
    return threshold


def check_if_user_has_edit_permission(municipality, acl):
    """Check if user has permission to edit KPI thresholds."""
    if acl.is_admin:
        return True
    if not acl.allowed_to_change_permit_limit:
        raise HTTPException(status_code=403, detail="This user is not allowed to change KPI thresholds.")
    if municipality in acl.municipalities:
        return True
    raise HTTPException(status_code=403, detail="This user is not allowed to change KPI thresholds in this municipality.")


# Backwards compatibility aliases
create_permit_limit = create_kpi_threshold
insert_permit_limit = insert_kpi_threshold
check_if_user_has_edit_permit_permission = check_if_user_has_edit_permission
