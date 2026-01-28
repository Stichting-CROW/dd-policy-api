from authorization import access_control
from db_helper import db_helper
from fastapi import HTTPException
import traceback
from model.kpi import KPIThreshold
from permits.queries import check_existing_kpi_threshold
from permits.create_permit_limit import check_if_user_has_edit_permission
from psycopg2 import errorcodes
import psycopg2


def edit_kpi_threshold(threshold: KPIThreshold, current_user: access_control.User):
    """Edit an existing KPI threshold configuration."""
    if not threshold.kpi_threshold_id:
        raise HTTPException(status_code=400, detail="KPI threshold ID is required.")
    check_if_user_has_edit_permission(threshold.municipality, current_user.acl)

    with db_helper.get_resource() as (cur, conn):
        try:
            checks_current = check_existing_kpi_threshold(cur, threshold.kpi_threshold_id)
            if checks_current is None:
                raise HTTPException(status_code=404, detail="KPI threshold not found.")
            
            threshold_in_past, municipality = checks_current
            check_if_user_has_edit_permission(municipality, current_user.acl)
            if threshold_in_past and not current_user.acl.allowed_to_change_permit_limit_historically:
                raise HTTPException(status_code=403, detail="This user is not allowed to change KPI thresholds historically.")
            
            update_kpi_threshold(cur, threshold)
            conn.commit()
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


def update_kpi_threshold(cur, threshold: KPIThreshold):
    """Update an existing KPI threshold in the database."""
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
        threshold.municipality,
        threshold.system_id,
        threshold.modality.value.lower(),
        threshold.effective_date,
        threshold.min_vehicles,
        threshold.max_vehicles,
        threshold.min_trips_per_vehicle,
        threshold.max_parking_duration,
        threshold.kpi_threshold_id
    ))
    return threshold


# Backwards compatibility aliases
edit_permit_limit = edit_kpi_threshold
update_permit_limit = update_kpi_threshold
