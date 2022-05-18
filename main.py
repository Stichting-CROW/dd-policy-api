from typing import List, Union
from uuid import UUID
from fastapi import FastAPI, Depends, Header, Query
from zones import create_zone, zone, get_zones
from db_helper import db_helper
from mds import geographies, geography
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from authorization import access_control

app = FastAPI()

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.post("/admin/zone")
def create_zone_route(zone: zone.Zone, current_user: access_control.User = Depends(access_control.get_current_user)):
    return create_zone.create_zone(zone, current_user)

@app.get("/admin/zones")
def get_zones_private(municipality: Union[str, None] = None, geography_types: list[zone.GeographyType] = Query(default=[])):
    print(geography_types)
    return get_zones.get_private_zones(municipality=municipality, geography_types=geography_types)

@app.get("/public/zones")
def get_zones_public(municipality: Union[str, None] = None, geography_types: list[zone.GeographyType] = Query(default=[])):
    return get_zones.get_public_zones(municipality=municipality, geography_types=geography_types)

@app.put("/admin/zones/{geography_uuid}")
def update_zone(geography_uuid: UUID):
    return get_zones.get_zones()

@app.get("/geographies")
def get_geographies_route(response_model=geographies.MDSGeographies):
    return geographies.get_geographies()

@app.get("/geographies/{geography_uuid}")
def get_geographies_route(geography_uuid: UUID, response_model=geography.MDSGeography):
    return geography.get_geography(geography_uuid)

@app.on_event("shutdown")
def shutdown_event():
    db_helper.shutdown_connection_pool()