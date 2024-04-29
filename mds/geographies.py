from db_helper import db_helper
from fastapi import HTTPException
import time

from pydantic import BaseModel
from typing import List
from mds.geography import Geography, convert_geography_row

class MDSGeographies(BaseModel):
    version: str = "1.2.0"
    updated: int
    geographies: List[Geography]

def get_geographies(municipality: str):
    with db_helper.get_resource() as (cur, _):
        try:
            result = query_geographies(cur, municipality)
            return generate_geographies_response(result=result)
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def query_geographies(cur, municipality: str):
    stmt = """
        SELECT geography_id, zone_id, geographies.name, description, 
        effective_date, published_date, retire_date, published_retire_date, ST_AsGeoJSON(area) as geojson
        FROM geographies
        JOIN zones
        USING(zone_id)
        WHERE NOW() >= published_date
        AND ((true = %s) or  municipality = %s)
    """
    cur.execute(stmt, (municipality == None, municipality))
    return cur.fetchall()

def generate_geographies_response(result):
    return MDSGeographies(
        updated=time.time_ns() // 1_000_000,
        geographies=list(map(convert_geography_row, result))
    )

