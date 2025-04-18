from db_helper import db_helper
from fastapi import HTTPException
import json
from datetime import timezone, datetime

from pydantic import BaseModel
from typing import Optional, List
from geojson_pydantic import FeatureCollection, Feature, geometries
from uuid import UUID


class Geography(BaseModel):
    name: str
    description: str
    geography_id: UUID
    geography_json: FeatureCollection
    effective_date: Optional[int]
    published_date: int
    retire_date: Optional[int] = None

class MDSGeography(BaseModel):
    version: str = "1.2.0"
    geographies: Geography

def get_geography(geography_uuid):
    with db_helper.get_resource() as (cur, _):
        try:
            result = query_geography(cur, geography_uuid)
            return generate_geography_response(result=result)
        except HTTPException as e:
            raise e
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def query_geography(cur, geography_uuid):
    stmt = """
        SELECT geography_id, zone_id, geographies.name, description, 
        effective_date, published_date, retire_date, published_retire_date, ST_AsGeoJSON(area) as geojson
        FROM geographies
        JOIN zones
        USING(zone_id)
        WHERE NOW() >= published_date AND geography_id = %s
    """
    cur.execute(stmt, (str(geography_uuid),))
    return cur.fetchone()

def generate_geography_response(result):
    if result == None:
        raise HTTPException(status_code=404, detail="No geography found with this uuid.")

    return MDSGeography(
        geographies=convert_geography_row(result)
    )

def convert_geography_row(row):
    retire_date = row["retire_date"]
    published_retire_date = row["published_retire_date"]
    if published_retire_date and published_retire_date <= datetime.now(timezone.utc):
        retire_date = None
    return Geography(
        name=row["name"],
        description=row["description"],
        geography_id=row["geography_id"],
        geography_json=convert_record_to_feature_collection(row["geojson"]),
        effective_date=convert_datetime_to_millis(row["effective_date"]),
        published_date=convert_datetime_to_millis(row["published_date"]),
        retire_data=convert_datetime_to_millis(retire_date)
    )

def convert_datetime_to_millis(dt):
    if dt == None:
        return None
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

def convert_record_to_feature_collection(geojson):
    geometry = geometries.parse_geometry_obj(json.loads(geojson))
    feature = Feature(type="Feature", geometry=geometry, properties={})
    return FeatureCollection(type="FeatureCollection", features=[feature])
    