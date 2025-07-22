from tempfile import NamedTemporaryFile
from typing import List, Union
from uuid import UUID
from typing import Annotated
from fastapi import FastAPI, Depends, Header, Query, File, UploadFile, Body, HTTPException
from fastapi.responses import StreamingResponse

from zones import create_zone, zone, get_zones, delete_zone, edit_zone, publish_zones, make_concept, propose_retirement
from db_helper import db_helper
from mds import geographies, geography, stops, stop, policies, policy
from exporters import kml_export, geopackage_export, geopackage_import, export_request
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from authorization import access_control
from service_areas import get_available_operators, get_service_areas, get_service_area_history, get_service_area_delta, generate_service_area
from datetime import date
from modalities import Modality
from operators import get_operators
from model import operator
from model.permit_limit import PermitLimit
from model.permit_limit_overview import PermitLimitOverview
from permits import create_permit_limit, delete_permit_limit, edit_permit_limit, get_permit_limit_history, permit_overview

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
    phases: Annotated[list[zone.Phase], Query()] = [zone.Phase.active, zone.Phase.retirement_concept, zone.Phase.published_retirement, zone.Phase.committed_retire_concept],
    affected_modalities: Annotated[list[Modality], Query()] = [Modality.bicycle, Modality.car, Modality.moped, Modality.cargo_bicycle]
):
    if len(phases) == 0:
        raise HTTPException(status_code=400, detail="At least one phase in query parameter phases should be specified.")
    return get_zones.get_private_zones(municipality=municipality, geography_types=geography_types, phases=phases, affected_modalities=affected_modalities)

@app.get("/public/zones")
def get_zones_public(
    municipality: Union[str, None] = None, 
    geography_types: list[zone.GeographyType] = Query(default=[]),
    phases: Annotated[list[zone.Phase], Query()] = [zone.Phase.active, zone.Phase.retirement_concept, zone.Phase.published_retirement, zone.Phase.committed_retire_concept],
    affected_modalities: Annotated[list[Modality], Query()] = [Modality.bicycle, Modality.car, Modality.moped, Modality.cargo_bicycle]
):
    return get_zones.get_public_zones(municipality=municipality, geography_types=geography_types, phases=phases, affected_modalities=affected_modalities)

@app.get("/public/service_area")
def get_service_area(municipalities: list[str] = Query(), operators: list[str] = Query()):
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
def get_geography_route(geography_uuid: UUID):
    return geography.get_geography(geography_uuid)

@app.get("/stops", response_model=stop.MDSStops)
def get_stops_route(municipality: Union[str, None] = None):
    return stops.get_stops(municipality)

@app.get("/stops/{stop_uuid}", response_model=stop.MDSStops)
def get_stop_route(stop_uuid: UUID):
    return stop.get_stop(stop_uuid)

@app.get("/policies", response_model=policies.MDSPolicies, response_model_exclude_none=True)
def get_policies_route(municipality: Union[str, None] = None):
    return policies.get_policies(municipality)

@app.get("/policies/{policy_uuid}", response_model=policies.MDSPolicies, response_model_exclude_none=True)
def get_policy_route(policy_uuid: UUID):
    return policies.get_policy(policy_uuid)

# This api generates a service area based on a desired service area from an operator minus all no parking zones + 
@app.post("/public/generate_service_area")
def generate_service_area_route(
    request: generate_service_area.GenerateServiceAreaRequest,
):
    return generate_service_area.generate_service_area(request)

@app.post("/kml/export")
def get_kml_route(export_request: export_request.ExportRequest):
    result, zip_file_name = kml_export.export(export_request)
    return StreamingResponse(
            iter([result.getvalue()]), 
            media_type="application/x-zip-compressed",
            headers={'Content-Disposition': 'attachment; filename="{}"'.format(zip_file_name)}
        )

@app.post("/gpkg/export")
def export_gkpg_route(export_request: export_request.ExportRequest):
    result, zip_file_name = geopackage_export.export(export_request)
    return StreamingResponse(
            iter([result.getvalue()]), 
            media_type="application/x-zip-compressed",
            headers={'Content-Disposition': 'attachment; filename="{}"'.format(zip_file_name)}
        )

@app.post("/admin/gpkg/import")
async def export_gpkg_route(file: UploadFile, municipality: str, current_user: access_control.User = Depends(access_control.get_current_user)):
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

@app.get("/operators", response_model=operator.OperatorResponse, response_model_exclude_none=True)
def get_operators_route():
    return get_operators.get_operators()

@app.post("/admin/permit_limit", status_code=201, response_model=PermitLimit, response_model_exclude_unset=True)
def create_permit_limit_route(permit_limit: PermitLimit, current_user: access_control.User = Depends(access_control.get_current_user)):
    return create_permit_limit.create_permit_limit(permit_limit=permit_limit, current_user=current_user)

@app.put("/admin/permit_limit", status_code=204)
def update_permit_limit_route(permit_limit: PermitLimit, current_user: access_control.User = Depends(access_control.get_current_user)):
    return edit_permit_limit.edit_permit_limit(new_permit_limit=permit_limit, current_user=current_user)

@app.delete("/admin/permit_limit/{permit_limit_id}", status_code=204)
def delete_permit_limit_route(permit_limit_id: int, current_user: access_control.User = Depends(access_control.get_current_user)):
    delete_permit_limit.delete_permit_limit(permit_limit_id=permit_limit_id, current_user=current_user)

@app.get("/public/permit_limit_history", response_model=List[PermitLimit], response_model_exclude_none=True)
def get_permit_limit_history_route(municipality: str, system_id: str, modality: Modality):
    return get_permit_limit_history.get_permit_limit_history(municipality=municipality, system_id=system_id, modality=modality)

@app.get("/public/permit_limit_overview", response_model=List[PermitLimitOverview], response_model_exclude_none=True)
def get_permit_limit_overview_public_route(municipality: str | None = None, system_id: str | None = None):
    return permit_overview.get_permit_overview(municipality=municipality, system_id=system_id)

# This will be a non public overview
@app.get("/permit_limit_overview", response_model=List[PermitLimit])
def get_permit_limit_overview_route(): 
    pass

# @app.get("/active_operators")

@app.on_event("shutdown")
def shutdown_event():
    db_helper.shutdown_connection_pool()
