from db_helper import db_helper
from fastapi import HTTPException
import zones.zone as zone
import zones.stop as stop
from datetime import date

from service_areas.service_area import ServiceAreaVersion

def get_service_area_history(
    municipalities: list[str],
    operators: list[str],
    start_date: date,
    end_date: date,
) -> list[str]:
    with db_helper.get_resource() as (cur, conn):
        try:
            res = query_service_area_history(cur, municipalities=municipalities, operators=operators, start_date=start_date, end_date=end_date)
            response = []
            for historical_service_area in res:
                response.append(ServiceAreaVersion(
                    service_area_version_id=historical_service_area["service_area_version_id"],
                    municipality=historical_service_area["municipality"],
                    operator=historical_service_area["operator"],
                    valid_from=historical_service_area["valid_from"],
                    valid_until=historical_service_area["valid_until"]
                ))
            return response
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")


def query_service_area_history(cur, municipalities: list[str], operators: list[str], start_date: date, end_date: date):
    stmt = """
        SELECT service_area_version_id, municipality, operator, valid_from, valid_until  
        FROM service_area 
        WHERE operator = ANY(%s) 
        AND municipality = ANY(%s)
        AND valid_from >= %s and valid_from <= %s
        ORDER BY valid_from;
    """
    cur.execute(stmt, (operators, municipalities, start_date, end_date))
    return cur.fetchall()