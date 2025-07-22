from typing import Optional
from db_helper import db_helper
from fastapi import HTTPException
import traceback
from model import permit_limit_overview, permit_limit

def get_permit_overview(municipality: Optional[str], system_id: Optional[str]):
    with db_helper.get_resource() as (cur, conn):
        try:
            rows = query_permits(cur, municipality, system_id)
            res = []
            for row in rows:
                print(row)
                res.append(permit_limit_overview.PermitLimitOverview(permit_limit = row, stats=permit_limit_overview.PermitLimitStats(current_vehicle_count=100, number_of_vehicles_illegally_parked_last_month=1000, number_of_rentals_per_vehicle=1.5, duration_correct_percentage=90)))
            return res
        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def query_permits(cur, municipality: Optional[str], system_id: Optional[str]):
    stmt = """
        WITH permit_with_end AS (
            SELECT *,
                LEAD(effective_date, 1) OVER (
                    PARTITION BY municipality, system_id, modality
                    ORDER BY effective_date
                ) AS end_date
            FROM permit_limit
            WHERE (%(system_id)s IS NULL OR system_id = %(system_id)s) 
            AND (%(municipality)s IS NULL OR municipality = %(municipality)s)
        ),
        currently_active AS (
            SELECT * FROM permit_with_end
            WHERE effective_date <= CURRENT_DATE
            AND (end_date IS NULL OR CURRENT_DATE < end_date)
        ),
        next_future AS (
            SELECT DISTINCT ON (municipality, system_id, modality) *
            FROM permit_with_end
            WHERE effective_date > CURRENT_DATE
            ORDER BY municipality, system_id, modality, effective_date
        )
        SELECT *
        FROM (
                SELECT * FROM currently_active
                UNION ALL
                SELECT * FROM next_future as nf
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM currently_active ca
                    WHERE ca.municipality = nf.municipality
                    AND ca.system_id = nf.system_id
                    AND ca.modality = nf.modality
                )
        ) as merged
        LEFT JOIN LATERAL (
                SELECT  json_build_object(
                    'permit_limit_id', permit_limit_id,
                    'municipality', municipality,
                    'system_id', system_id,
                    'modality', modality,
                    'effective_date', effective_date,
                    'minimum_vehicles', minimum_vehicles,
                    'maximum_vehicles', maximum_vehicles,
                    'minimal_number_of_trips_per_vehicle', minimal_number_of_trips_per_vehicle,
                    'max_parking_duration', interval_to_iso8601(max_parking_duration)
                ) as future_permit
                FROM next_future
                WHERE next_future.permit_limit_id != merged.permit_limit_id
                AND next_future.municipality = merged.municipality
                AND next_future.system_id = merged.system_id
                AND next_future.modality = merged.modality
        ) AS future_permit ON TRUE;
    """
    cur.execute(stmt, { 
        'municipality': municipality,
        'system_id': system_id
    })
    return cur.fetchall()