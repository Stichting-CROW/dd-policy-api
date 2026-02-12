from typing import Optional
from fastapi import HTTPException


from db_helper import db_helper
import traceback
from modalities import Modality, PropulsionType
from model.kpi import KPI, STANDARD_KPI_DESCRIPTIONS, GeometryModalityOperatorKPI, KPIValue, KPIReport
from datetime import date
from authorization import access_control



def get_operator_modality_kpi_overview(start_date: date, end_date: date, municipality: Optional[str], system_id: Optional[str], form_factor: Optional[Modality], propulsion_type: Optional[PropulsionType], current_user: access_control.User) -> KPIReport:
    if municipality is None and system_id is None:
        raise HTTPException(status_code=400, detail="Either municipality or system_id must be provided.")
    
    if not current_user.acl.is_admin and not municipality in current_user.acl.municipalities:
        raise HTTPException(status_code=403, detail="User not authorized to access data for this municipality.")
    
    if propulsion_type is not None and form_factor is None:
        raise HTTPException(status_code=400, detail="If propulsion_type is provided, form_factor must also be provided.")

    all_stats: dict[str, list[GeometryModalityOperatorKPI]] = {}
    with db_helper.get_resource() as (cur, conn):
        try:
            day_stats_res = query_day_stats(cur, municipality, system_id, form_factor, propulsion_type, start_date, end_date)
            all_stats = convert_stats_to_kpi_values(all_stats, day_stats_res)
            query_moment_stats_res = query_moment_stats(cur, municipality, system_id, form_factor, propulsion_type, start_date, end_date)
            all_stats = convert_stats_to_kpi_values(all_stats, query_moment_stats_res)

            return KPIReport(
                performance_indicator_description=STANDARD_KPI_DESCRIPTIONS,
                municipality_modality_operators=list(all_stats.values())
            )
        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")


def convert_stats_to_kpi_values(all_stats: dict[str, list[GeometryModalityOperatorKPI]], rows: list[dict]) -> dict[str, list[GeometryModalityOperatorKPI]]:
    geometry_modality_operator_kpi_key = ""
    kpi_key  = -1
    current_geometry_modality_operator_kpi: GeometryModalityOperatorKPI = None
    current_kpi: KPI = None

    for row in rows:
        current_key = f"{row['geometry_ref']}_{row['system_id']}_{row['vehicle_type']}"
        
        # init if it doesn't exist yet
        if current_key not in all_stats:
            
            modality = Modality._value2member_map_.get(row["vehicle_type"].split(":")[0], Modality.unknown)
            propulsion_type = PropulsionType._value2member_map_.get(row["vehicle_type"].split(":")[1], PropulsionType.unknown) if len(row["vehicle_type"].split(":")) > 1 else PropulsionType.unknown
            all_stats[current_key] = GeometryModalityOperatorKPI(
                operator=row['system_id'],
                form_factor=modality,
                propulsion_type=propulsion_type,
                geometry_ref=row['geometry_ref'],
                kpis=[]
            )

        if geometry_modality_operator_kpi_key != current_key:
            geometry_modality_operator_kpi_key = current_key
            current_geometry_modality_operator_kpi = all_stats[current_key]
            kpi_key = -1  # reset KPI key for new operator/modality/geometry

        if kpi_key != f"{row['indicator']}":
            kpi_key = f"{row['indicator']}"
            current_kpi = KPI(
                kpi_key=kpi_key,
                granularity="day",
                values=[]
            )
            current_geometry_modality_operator_kpi.kpis.append(current_kpi)

        current_kpi.values.append(KPIValue(
            date=row['date'],
            measured=row['value'],
            threshold=row['threshold'],  # Set threshold if available
            complies=row['complies'] # Set compliance if available
        ))      


    return all_stats


def query_moment_stats(cur, municipality: Optional[str], system_id: Optional[str], form_factor: Optional[Modality], propulsion_type: Optional[PropulsionType], start_date: date, end_date: date):
    stmt = """
       WITH limits_with_range AS (
            SELECT
                geometry_operator_modality_limit_id,
                geometry_ref,
                operator,
                form_factor,
                propulsion_type,
                effective_date AS valid_from,
                LEAD(effective_date) OVER (
                    PARTITION BY geometry_ref, form_factor, propulsion_type
                    ORDER BY effective_date
                ) - interval '1 day' AS valid_to,
                limits
            FROM geometry_operator_modality_limit
        ),
        base AS (
            SELECT
                a.date,
                a.geometry_ref,
                a.system_id,
                a.vehicle_type,
                CASE a.indicator
                    WHEN 2 THEN 'percentage_parked_longer_then_24_hours'
                    WHEN 3 THEN 'percentage_parked_longer_then_3_days'
                    WHEN 4 THEN 'percentage_parked_longer_then_7_days'
                    WHEN 5 THEN 'percentage_parked_longer_then_14_days'
                END AS indicator,
                ROUND((a.value / NULLIF(b.value, 0)) * 100, 1) AS value
            FROM moment_statistics a
            JOIN moment_statistics b
                ON a.date = b.date
                AND a.geometry_ref = b.geometry_ref
                AND a.measurement_moment = b.measurement_moment
                AND a.vehicle_type = b.vehicle_type
                AND a.system_id = b.system_id
            WHERE a.date BETWEEN %(start_date)s AND %(end_date)s
            AND a.indicator IN (2, 3, 4, 5)
            AND b.indicator = 1
            AND a.measurement_moment = 0
            AND (%(municipality_cbs)s IS NULL OR a.geometry_ref = %(municipality_cbs)s)
            AND (%(system_id)s IS NULL OR a.system_id = %(system_id)s)
            AND (%(form_factor_like)s IS NULL OR a.vehicle_type LIKE %(form_factor_like)s)
            AND (%(vehicle_type)s IS NULL OR a.vehicle_type LIKE %(vehicle_type)s)
        ),
        dimensions AS (
            SELECT DISTINCT
                geometry_ref,
                system_id,
                vehicle_type,
                indicator
            FROM base
        ),
        dates AS (
            SELECT generate_series(
                %(start_date)s::date,
                %(end_date)s::date,
                interval '1 day'
            )::date AS date
        ),
        s AS (
            SELECT
                d.date,
                dim.geometry_ref,
                dim.system_id,
                dim.vehicle_type,
                dim.indicator,
                COALESCE(b.value, 0) AS value
            FROM dimensions dim
            CROSS JOIN dates d
            LEFT JOIN base b
                ON b.date = d.date
                AND b.geometry_ref = dim.geometry_ref
                AND b.system_id = dim.system_id
                AND b.vehicle_type = dim.vehicle_type
                AND b.indicator = dim.indicator
        )
        SELECT
            s.date,
            s.geometry_ref,
            s.system_id,
            s.vehicle_type,
            s.indicator,
            s.value,
            l.limits->s.indicator AS threshold,
            CASE
                WHEN l.limits IS NULL OR NOT (l.limits ? s.indicator) THEN NULL
                WHEN s.value <= (l.limits->s.indicator)::numeric THEN TRUE
                ELSE FALSE
            END AS complies
        FROM s
        LEFT JOIN limits_with_range l
            ON s.geometry_ref = l.geometry_ref
            AND s.vehicle_type = CONCAT(l.form_factor, ':', l.propulsion_type)
            AND s.system_id = l.operator
            AND s.date BETWEEN l.valid_from AND COALESCE(l.valid_to, s.date)
        ORDER BY
            s.system_id,
            s.vehicle_type,
            s.geometry_ref,
            s.indicator,
            s.date;


    """
    municipality_cbs = f'cbs:{municipality}' if municipality else None
    cur.execute(stmt, {
        'system_id': system_id, 
        'municipality_cbs': municipality_cbs,
        'form_factor_like': f'{form_factor.value}:%' if form_factor and propulsion_type is None else None,
        'vehicle_type': f'{form_factor.value}:{propulsion_type.value}' if propulsion_type else None,
        'start_date': start_date,
        'end_date': end_date  
    })
    return cur.fetchall()

def query_day_stats(cur, municipality: Optional[str], system_id: Optional[str], form_factor: Optional[Modality], propulsion_type: Optional[PropulsionType], start_date: date, end_date: date):
    stmt = """
    WITH limits_with_range AS (
        SELECT
            geometry_operator_modality_limit_id,
            geometry_ref,
            operator,
            form_factor,
            propulsion_type,
            effective_date AS valid_from,
            LEAD(effective_date) OVER (
                PARTITION BY geometry_ref, form_factor, propulsion_type
                ORDER BY effective_date
            ) - interval '1 day' AS valid_to,
            limits
        FROM geometry_operator_modality_limit
    )

      SELECT
        s.date,
        s.geometry_ref,
        s.system_id,
        s.vehicle_type,
        s.indicator,
        s.value,
        l.limits->s.indicator as threshold,
        CASE 
            WHEN l.limits IS NULL or NOT (l.limits ? s.indicator) THEN NULL 
            WHEN s.value <= (l.limits->s.indicator)::numeric  THEN TRUE 
            ELSE FALSE 
        END as complies
    FROM (
        -- Your daily stats query
        WITH base AS (
            SELECT
                date,
                geometry_ref,
                system_id,
                vehicle_type,
                CASE indicator
                    WHEN 1 THEN 'vehicle_cap'
                    WHEN 6 THEN 'number_of_wrongly_parked_vehicles'
                END AS indicator,
                value
            FROM day_statistics
            WHERE date BETWEEN %(start_date)s AND %(end_date)s
            AND (%(municipality_cbs)s IS NULL OR geometry_ref = %(municipality_cbs)s)
            AND (%(system_id)s IS NULL OR system_id = %(system_id)s)
            AND (%(form_factor_like)s IS NULL OR vehicle_type LIKE %(form_factor_like)s)
            AND (%(vehicle_type)s IS NULL OR vehicle_type LIKE %(vehicle_type)s)
            AND indicator IN (1, 6)
        ),
        dimensions AS (
            SELECT DISTINCT
                geometry_ref,
                system_id,
                vehicle_type,
                indicator
            FROM base
        ),
        dates AS (
            SELECT generate_series(
                %(start_date)s::date,
                %(end_date)s::date,
                interval '1 day'
            )::date AS date
        )
        SELECT
            d.date,
            dim.geometry_ref,
            dim.system_id,
            dim.vehicle_type,
            dim.indicator,
            COALESCE(b.value, 0) AS value
        FROM dimensions dim
        CROSS JOIN dates d
        LEFT JOIN base b
            ON b.date = d.date
            AND b.geometry_ref = dim.geometry_ref
            AND b.system_id = dim.system_id
            AND b.vehicle_type = dim.vehicle_type
            AND b.indicator = dim.indicator
    ) s
    LEFT JOIN limits_with_range l
        ON s.geometry_ref = l.geometry_ref
        AND s.vehicle_type = CONCAT(l.form_factor, ':', l.propulsion_type)
        AND s.system_id = l.operator
        AND s.date BETWEEN l.valid_from AND COALESCE(l.valid_to, s.date)
    ORDER BY
        s.system_id,
        s.vehicle_type,
        s.geometry_ref,
        s.indicator,
        s.date;
    """
    municipality_cbs = f'cbs:{municipality}' if municipality else None
    cur.execute(stmt, {
        'system_id': system_id, 
        'municipality_cbs': municipality_cbs,
        'form_factor_like': f'{form_factor.value}:%' if form_factor and propulsion_type is None else None,
        'vehicle_type': f'{form_factor.value}:{propulsion_type.value}' if propulsion_type else None,
        'start_date': start_date,
        'end_date': end_date  
    })
    return cur.fetchall()