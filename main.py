from typing import List, Union
from uuid import UUID
from typing import Annotated
from fastapi import FastAPI, Depends, Header, Query, File, UploadFile
from fastapi.responses import StreamingResponse

from zones import create_zone, zone, get_zones, delete_zone, edit_zone
from db_helper import db_helper
from mds import geographies, geography, stops, stop, policies, policy
from kml import kml_export, kml_import
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from authorization import access_control

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

# /admin endpoints
@app.post("/admin/zone", status_code=201)
def create_zone_route(zone: zone.Zone, current_user: access_control.User = Depends(access_control.get_current_user)):
    return create_zone.create_zone(zone, current_user)

# /admin endpoints
@app.post("/admin/bulk_insert_zones", status_code=201)
def create_bulk_zone_route(zones: list[zone.Zone], current_user: access_control.User = Depends(access_control.get_current_user)):
    return create_zone.create_zones(zones, current_user)

# Edit zone
# When not published, an existing geography can be edited.
# When published the current geography will be replaced by a new geography, the old one will be retired. 
# If only the stop and no_parking objects are edited the geography isn't replaced. 
@app.put("/admin/zone")
def update_zone(zone: zone.Zone, current_user: access_control.User = Depends(access_control.get_current_user)):
    return edit_zone.edit_zone(zone, current_user)

@app.delete("/admin/zone/{geography_uuid}", status_code=204)
def update_zone(geography_uuid: UUID, current_user: access_control.User = Depends(access_control.get_current_user)):
    return delete_zone.delete_zone(geography_uuid=geography_uuid, user=current_user)

@app.get("/admin/zones")
def get_zones_private(municipality: Union[str, None] = None, geography_types: list[zone.GeographyType] = Query(default=[])):
    print(geography_types)
    return get_zones.get_private_zones(municipality=municipality, geography_types=geography_types)

@app.get("/public/zones")
def get_zones_public(municipality: Union[str, None] = None, geography_types: list[zone.GeographyType] = Query(default=[])):
    return get_zones.get_public_zones(municipality=municipality, geography_types=geography_types)

# MDS - endpoints.

@app.get("/geographies", response_model=geographies.MDSGeographies)
def get_geographies_route():
    return geographies.get_geographies()

@app.get("/geographies/{geography_uuid}", response_model=geography.MDSGeography)
def get_geographies_route(geography_uuid: UUID):
    return geography.get_geography(geography_uuid)

@app.get("/stops", response_model=stop.MDSStops)
def get_stops_route(municipality: Union[str, None] = None):
    return stops.get_stops(municipality)

@app.get("/stops/{stop_uuid}", response_model=stop.MDSStops)
def get_stop_route(stop_uuid: UUID):
    return stop.get_stop(stop_uuid)

@app.get("/policies", response_model=policies.MDSPolicies)
def get_stops_route(municipality: Union[str, None] = None):
    return policies.get_policies(municipality)

@app.get("/policies/{policy_uuid}", response_model=policies.MDSPolicies)
def get_stop_route(policy_uuid: UUID):
    return policies.get_policy(policy_uuid)

@app.get("/kml/export")
def get_kml_route(municipality: Union[str, None] = None):
    result = kml_export.export(municipality)
    return StreamingResponse(
            iter([result.getvalue()]), 
            media_type="application/x-zip-compressed",
            headers={'Content-Disposition': 'attachment; filename="{}"'.format("dashboarddeelmobiliteit_kml_export.zip")}
        )

@app.post("/admin/kml/pre_import")
def get_pre_import_kml(file: Annotated[bytes, File()], municipality: str, current_user: access_control.User = Depends(access_control.get_current_user)):
    return kml_import.kml_import(file, municipality)

@app.on_event("shutdown")
def shutdown_event():
    db_helper.shutdown_connection_pool()