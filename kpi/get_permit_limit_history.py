from db_helper import db_helper
from fastapi import HTTPException
import traceback
from modalities import Modality


def get_kpi_threshold_history(municipality: str, system_id: str, modality: Modality):
    """Get the history of KPI threshold changes for a specific operator/modality."""
    with db_helper.get_resource() as (cur, conn):
        try:
            res = query_kpi_threshold_history(cur, municipality, system_id, modality)
            for index, row in enumerate(res):
                res[index]["modality"] = row["modality"].lower()

            return res
        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")


def query_kpi_threshold_history(cur, municipality: str, system_id: str, modality: Modality):
    """Query the database for KPI threshold history."""
    stmt = """
    SELECT 
        permit_limit_id as kpi_threshold_id,
        municipality,
        system_id,
        modality,
        effective_date,
        minimum_vehicles as min_vehicles,
        maximum_vehicles as max_vehicles,
        minimal_number_of_trips_per_vehicle as min_trips_per_vehicle,
        max_parking_duration,
        LEAD(effective_date, 1) OVER (
            PARTITION BY municipality, system_id, modality
            ORDER BY effective_date
        ) AS end_date
    FROM permit_limit
    WHERE municipality = %s
    AND system_id = %s
    AND modality = %s
    ORDER BY effective_date DESC
    """
    cur.execute(stmt, (municipality, system_id, modality.value.lower()))
    return cur.fetchall()


# Backwards compatibility aliases
get_permit_limit_history = get_kpi_threshold_history
query_permit_limit_history = query_kpi_threshold_history
