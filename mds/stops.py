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
from mds.stop import MDSStop, MDSStops, MDSStopData

def get_stops(municipality):
    key = "all_stops"
    if municipality != None:
        key = "stops_per_municipality:" + municipality

    results = []
    last_updated = 0
    with redis_helper.get_resource() as r:
        lua_script_to_get_stops = """
        local stops = redis.call('SMEMBERS', KEYS[1])
        local result = {}
        for index, stop_id in ipairs(stops) do
        result[index] = redis.call('GET', 'stop:' .. stop_id)
        end
        return result"""
        get_stops = r.register_script(lua_script_to_get_stops)
        last_updated = r.get("stops_last_updated")
        result = get_stops(keys=[key])
        for stop in result:
            print(stop)
            stop_dict = json.loads(stop)
            results.append(MDSStop(**stop_dict))

    return MDSStops(
        last_updated=last_updated,
        data = MDSStopData(
            stops = results
        )
    )
    