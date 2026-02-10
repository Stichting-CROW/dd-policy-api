from db_helper import db_helper
from fastapi import HTTPException
import traceback
from modalities import Modality, PropulsionType


def get_geometry_operator_modality_limit_history(geometry_ref: str, operator: str, form_factor: Modality, propulsion_type: PropulsionType):
    """Get the history of geometry operator modality limit changes for a specific combination."""
    with db_helper.get_resource() as (cur, conn):
        try:
            res = query_geometry_operator_modality_limit_history(cur, geometry_ref, operator, form_factor, propulsion_type)
            return res
        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")


def query_geometry_operator_modality_limit_history(cur, geometry_ref: str, operator: str, form_factor: Modality, propulsion_type: PropulsionType):
    """Query the database for geometry operator modality limit history."""
    stmt = """
    SELECT 
        geometry_operator_modality_limit_id,
        geometry_ref,
        operator,
        form_factor,
        propulsion_type,
        effective_date,
        limits->>'minimum_vehicles' as minimum_vehicles,
        limits->>'maximum_vehicles' as maximum_vehicles,
        limits->>'minimal_number_of_trips_per_vehicle' as minimal_number_of_trips_per_vehicle,
        limits->>'max_parking_duration' as max_parking_duration,
        LEAD(effective_date, 1) OVER (
            PARTITION BY geometry_ref, operator, form_factor, propulsion_type
            ORDER BY effective_date
        ) - interval '1 day' AS end_date
    FROM geometry_operator_modality_limit
    WHERE geometry_ref = %s
    AND operator = %s
    AND form_factor = %s
    AND propulsion_type = %s
    ORDER BY effective_date DESC
    """
    cur.execute(stmt, (geometry_ref, operator, form_factor.value.lower(), propulsion_type.value.lower()))
    return cur.fetchall()

