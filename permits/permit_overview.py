from typing import Optional
from db_helper import db_helper
from fastapi import HTTPException
import traceback
from model import permit_limit_overview, permit_limit

def get_permit_overview(municipality: Optional[str], system_id: Optional[str]):
    if municipality is None and system_id is None:
        raise HTTPException(status_code=400, detail="Either municipality or system_id must be provided.")
    with db_helper.get_resource() as (cur, conn):
        try:
            permits = query_permits(cur, municipality, system_id)
            stats = query_stats(cur, municipality, system_id)
            res = []
            for row in permits:
                res.append(
                    permit_limit_overview.PermitLimitOverview(
                        permit_limit = row, 
                        stats=None, 
                        operator=row['operator'], 
                        municipality=row['municipality_json']
                        )
                    )
            permit_lookup = {
                (p.permit_limit.system_id, p.permit_limit.municipality, p.permit_limit.modality): p
                for p in res
            }
            for row in stats:
                key = (
                    row['system_id'],
                    row['municipality_json']['gmcode'],
                    row['form_factor']
                )
                permit = permit_lookup.get(key)
                if permit:
                    permit.stats = permit_limit_overview.PermitLimitStats(
                        number_of_vehicles_in_public_space=row['number_of_vehicles'],
                        number_of_vehicles_in_public_space_parked_to_long=row['number_of_vehicles_parked_to_long'],
                    )
                else:
                    # If no permit found, create a new one with stats
                    res.append(
                        permit_limit_overview.PermitLimitOverview(
                            stats=permit_limit_overview.PermitLimitStats(
                                number_of_vehicles_in_public_space=row['number_of_vehicles'],
                                number_of_vehicles_in_public_space_parked_to_long=row['number_of_vehicles_parked_to_long'],
                            ),
                            operator=row['operator'],
                            municipality=row['municipality_json']
                        )
                    )
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
                    'modality', modality,
                    'effective_date', effective_date,
                    'municipality', municipality,
                    'system_id', system_id,
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
        ) AS future_permit ON TRUE
        LEFT JOIN LATERAL (
                SELECT  json_build_object(
                    'system_id', operators.system_id,
                    'name', operators.name,
                    'color', operators.color,
                    'operator_url', operators.operator_url,
                    'logo_url', operators.logo_url
                ) as operator
                FROM operators
                WHERE operators.system_id  = merged.system_id
        ) AS operator ON TRUE
        LEFT JOIN LATERAL (
                SELECT  json_build_object(
                    'gmcode', municipality,
                    'name', zones.name
                ) as municipality_json
                FROM zones
                WHERE zones.municipality  = merged.municipality
                AND zones.zone_type = 'municipality'
        ) AS municipality_json ON TRUE;
    """
    cur.execute(stmt, { 
        'municipality': municipality,
        'system_id': system_id
    })
    return cur.fetchall()

def query_stats(cur, municipality: Optional[str], system_id: Optional[str]):
    # Maybe a bit too complicated, but it works and it is quick.
    # When we want to make this work internationally it is not good. 
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
        )

    SELECT *
    FROM
        (SELECT
            park_events.system_id,
            vehicle_type.form_factor,
            park_event_zone.zone_stats_ref AS zone_stats_ref,
            COUNT(*) AS number_of_vehicles,
            COUNT(CASE WHEN NOW() - start_time > max_parking_duration THEN 1 ELSE NULL  END) AS number_of_vehicles_parked_to_long
        FROM
            park_events
        JOIN
            park_event_zone USING (park_event_id)
        JOIN
            vehicle_type USING (vehicle_type_id)
        LEFT JOIN
            currently_active
            ON currently_active.system_id = park_events.system_id
            AND modality = form_factor
            AND zone_stats_ref = CONCAT('cbs:', currently_active.municipality)
        WHERE
            park_events.end_time IS NULL
        AND (%(municipality)s IS NULL OR park_event_zone.zone_stats_ref = CONCAT('cbs:', %(municipality)s))
        AND (%(system_id)s IS NULL OR park_events.system_id = %(system_id)s)
        AND zone_stats_ref like %(municipality_cbs)s
        GROUP BY
            park_events.system_id,
            vehicle_type.form_factor,
            park_event_zone.zone_stats_ref
        ) AS zone_stats
    LEFT JOIN LATERAL (
            SELECT  json_build_object(
                'system_id', operators.system_id,
                'name', operators.name,
                'color', operators.color,
                'operator_url', operators.operator_url,
                'logo_url', operators.logo_url
            ) as operator
            FROM operators
            WHERE operators.system_id  = zone_stats.system_id
    ) AS operator ON TRUE
    LEFT JOIN LATERAL (
            SELECT  json_build_object(
                'gmcode', municipality,
                'name', zones.name
            ) as municipality_json
            FROM zones
            WHERE zones.stats_ref = zone_stats.zone_stats_ref 
    ) AS municipality_json ON TRUE;
    """
    cur.execute(stmt, {'municipality': municipality, 'system_id': system_id, 'municipality_cbs': 'cbs:GM%'})
    return cur.fetchall()