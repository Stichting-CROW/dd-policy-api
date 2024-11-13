from tempfile import NamedTemporaryFile
from typing import List, Union
from uuid import UUID
from typing import Annotated
from fastapi import FastAPI, Depends, Header, Query, File, UploadFile, Body, HTTPException
from fastapi.responses import StreamingResponse

from zones import create_zone, zone, get_zones, delete_zone, edit_zone, publish_zones, make_concept, propose_retirement
from db_helper import db_helper
from mds import geographies, geography, stops, stop, policies, policy
from exporters import kml_export, kml_import, geopackage_export, geopackage_import, export_request
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from authorization import access_control
from service_areas import get_available_operators, get_service_areas, get_service_area_history, get_service_area_delta
from datetime import date

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

# /admin endpoints
@app.post("/admin/zone", status_code=201)
def create_zone_route(zone: zone.Zone, current_user: access_control.User = Depends(access_control.get_current_user)):
    return create_zone.create_zone(zone, current_user)

# /admin endpoints
@app.post("/admin/bulk_insert_zones", status_code=201)
def create_bulk_zone_route(zones: list[zone.Zone], current_user: access_control.User = Depends(access_control.get_current_user)):
    return create_zone.create_zones(zones, current_user)[0]

# /admin endpoints
@app.post("/admin/zones/publish", status_code=204)
def publish_zones_route(publish_zone_request: publish_zones.PublishZoneRequest, current_user: access_control.User = Depends(access_control.get_current_user)):
    return publish_zones.publish_zones_route(publish_zone_request, current_user)

@app.post("/admin/zones/make_concept", status_code=204)
def make_concept_route(make_concept_request: make_concept.MakeConceptRequest, current_user: access_control.User = Depends(access_control.get_current_user)):
    return make_concept.make_concept_route(make_concept_request=make_concept_request, current_user=current_user)

@app.post("/admin/zones/propose_retirement", status_code=204)
def propose_retirement_route(propose_retirement_request: propose_retirement.ProposeRetirementRequest, current_user: access_control.User = Depends(access_control.get_current_user)):
    return propose_retirement.propose_retirement_route(propose_retirement_request= propose_retirement_request, current_user=current_user)

@app.patch("/admin/zone")
def update_zone_route(zone: zone.EditZone, current_user: access_control.User = Depends(access_control.get_current_user)):
    return edit_zone.edit_zone(zone, current_user)

@app.patch("/admin/zone/bulk_edit")
def update_zones_route(bulk_edit_zone_request: edit_zone.BulkEditZonesRequest, current_user: access_control.User = Depends(access_control.get_current_user)):
    return edit_zone.edit_zones(bulk_edit_zone_request, current_user)

@app.delete("/admin/zone/{geography_uuid}", status_code=204)
def delete_zone_route(geography_uuid: UUID, current_user: access_control.User = Depends(access_control.get_current_user)):
    return delete_zone.delete_zone(geography_uuid=geography_uuid, user=current_user)

@app.post("/admin/zones/bulk_delete", status_code=204)
def delete_zones_route(delete_request: delete_zone.DeleteZonesRequest, current_user: access_control.User = Depends(access_control.get_current_user)):
    return delete_zone.delete_zones(request=delete_request, user=current_user)

@app.get("/admin/zones")
def get_zones_private(
    municipality: Union[str, None] = None, 
    geography_types: list[zone.GeographyType] = Query(default=[]),
    phases: Annotated[list[zone.Phase], Query()] = [zone.Phase.active, zone.Phase.retirement_concept, zone.Phase.published_retirement, zone.Phase.committed_retire_concept]):
    if len(phases) == 0:
        raise HTTPException(status_code=400, detail="At least one phase in query parameter phases should be specified.")
    return get_zones.get_private_zones(municipality=municipality, geography_types=geography_types, phases=phases)

@app.get("/public/zones")
def get_zones_public(
    municipality: Union[str, None] = None, 
    geography_types: list[zone.GeographyType] = Query(default=[]),
    phases: Annotated[list[zone.Phase], Query()] = [zone.Phase.active, zone.Phase.retirement_concept, zone.Phase.published_retirement, zone.Phase.committed_retire_concept]):
    return get_zones.get_public_zones(municipality=municipality, geography_types=geography_types, phases=phases)

@app.get("/public/service_area")
def get_zones_public(municipalities: list[str] = Query(), operators: list[str] = Query()):
    return get_service_areas.get_service_areas(municipalities=municipalities, operators=operators)

@app.get("/public/service_area/available_operators")
def get_operators_with_service_area_route(municipalities: list[str] = Query()):
    return get_available_operators.get_available_operators(municipalities=municipalities)

@app.get("/public/service_area/history")
def get_service_area_history_route(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    municipalities: list[str] = Query(), 
    operators: list[str] = Query(),
):
    return get_service_area_history.get_service_area_history(municipalities, operators, start_date, end_date)

@app.get("/public/service_area/delta/{service_area_version_id}")
def get_zones_public_route(service_area_version_id: int):
    return get_service_area_delta.get_service_area_delta(service_area_version_id)

# MDS - endpoints.
@app.get("/geographies", response_model=geographies.MDSGeographies)
def get_geographies_route(municipality: Union[str, None] = None):
    return geographies.get_geographies(municipality)

@app.get("/geographies/{geography_uuid}", response_model=geography.MDSGeography)
def get_geographies_route(geography_uuid: UUID):
    return geography.get_geography(geography_uuid)

@app.get("/stops", response_model=stop.MDSStops)
def get_stops_route(municipality: Union[str, None] = None):
    return stops.get_stops(municipality)

@app.get("/stops/{stop_uuid}", response_model=stop.MDSStops)
def get_stop_route(stop_uuid: UUID):
    return stop.get_stop(stop_uuid)

@app.get("/policies", response_model=policies.MDSPolicies, response_model_exclude_none=True)
def get_stops_route(municipality: Union[str, None] = None):
    return policies.get_policies(municipality)

@app.get("/policies/{policy_uuid}", response_model=policies.MDSPolicies, response_model_exclude_none=True)
def get_stop_route(policy_uuid: UUID):
    return policies.get_policy(policy_uuid)

@app.post("/kml/export")
def get_kml_route(export_request: export_request.ExportRequest):
    result = kml_export.export(export_request)
    return StreamingResponse(
            iter([result.getvalue()]), 
            media_type="application/x-zip-compressed",
            headers={'Content-Disposition': 'attachment; filename="{}"'.format("dashboarddeelmobiliteit_kml_export.zip")}
        )

@app.post("/admin/kml/import")
def get_pre_import_kml(file: Annotated[bytes, File()], municipality: str, current_user: access_control.User = Depends(access_control.get_current_user)):
    return kml_import.kml_import(file, municipality, current_user)

@app.post("/gpkg/export")
def export_gkpg_route(export_request: export_request.ExportRequest):
    result, zip_file_name = geopackage_export.export(export_request)
    return StreamingResponse(
            iter([result.getvalue()]), 
            media_type="application/x-zip-compressed",
            headers={'Content-Disposition': 'attachment; filename="{}"'.format(zip_file_name)}
        )

@app.post("/admin/gpkg/import")
async def export_gkpg_route(file: UploadFile, municipality: str, current_user: access_control.User = Depends(access_control.get_current_user)):
    temp = NamedTemporaryFile(delete=False)
    try:
        try:
            contents = file.file.read()
            with temp as f:
                f.write(contents);
        except Exception:
            raise HTTPException(status_code=500, detail='Error on geopackage')
        finally:
            file.file.close()
        return geopackage_import.gpkg_import(temp.name, municipality, current_user)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail='Something went wrong')

    

 
@app.on_event("shutdown")
def shutdown_event():
    db_helper.shutdown_connection_pool()