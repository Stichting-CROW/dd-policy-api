from db_helper import db_helper
from fastapi import HTTPException
import json
from datetime import timezone

from pydantic import BaseModel
from typing import Optional, List
from geojson_pydantic import FeatureCollection, Feature, geometries
from uuid import UUID

from geojson_pydantic import Feature, Point, Polygon
from pydantic import BaseModel
from typing import Dict
from redis_helper import redis_helper

PointFeatureModel = Feature[Point, Dict]
PolygonFeatureModel = Feature[Polygon, Dict]
class MDSStop(BaseModel):
    stop_id: str
    name: str
    last_reported: int
    location: PointFeatureModel
    status: Dict[str, bool]
    capacity: Dict[str, int]
    num_vehicles_available: Dict[str, int] = {}
    num_vehicles_disabled: Dict[str, int] = {}
    num_places_available: Dict[str, int] = {}
    geography_id: str

class MDSStopData(BaseModel):
    stops: List[MDSStop]

class MDSStops(BaseModel):
    version: str = "1.2.0"
    data: MDSStopData
    last_updated: int
    ttl: int = 30

def get_stop(stop_uuid):
    last_updated = 0
    stops = []
    with redis_helper.get_resource() as r:
        stop = r.get("stop:" + str(stop_uuid))
        if stop == None:
            raise HTTPException(status_code=404, detail="stop_id doesn't exists.")
        stop_dict = json.loads(stop)
        stops.append(MDSStop(**stop_dict))
        last_updated = r.get("stops_last_updated")

    return MDSStops(
        last_updated=last_updated,
        data = MDSStopData(
            stops = stops
        )
    )
        


