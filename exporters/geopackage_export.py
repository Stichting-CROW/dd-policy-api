from fudgeo.geopkg import GeoPackage

from exporters.export_request import ExportRequest
from fastapi import HTTPException
from db_helper import db_helper
from zones import get_zones, zone
import zipfile
import io
import os
from datetime import datetime
from random import choice, randint
from string import ascii_uppercase, digits

from fudgeo.geometry import MultiPolygon
from fudgeo.geopkg import GeoPackage
from fudgeo.enumeration import GeometryType, SQLFieldType
from fudgeo.geopkg import FeatureClass, Field, GeoPackage, SpatialReferenceSystem
from zones.zone import Zone
from typing import Iterator

def create_zip(file_name: str):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.write(file_name, arcname=os.path.basename(file_name))
    return zip_buffer

def create_layer(name: str, gpkg: GeoPackage, fields: tuple[Field, ...],):
    SRS_WKT: str = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
    SRS: SpatialReferenceSystem = SpatialReferenceSystem(
        name='EPSG4326', organization='EPSG', org_coord_sys_id=4326, definition=SRS_WKT)
    
    gpkg.create_feature_class(
        name=name, srs=SRS, fields=fields, 
        shape_type=GeometryType.multi_polygon, overwrite=True, spatial_index=True)

def add_data_to_monitoring(gpkg: GeoPackage, zones: Iterator[Zone]):
    rows = []
    for zone in zones:
        rows.append((MultiPolygon([zone.area.geometry.coordinates], srs_id=4326), zone.name, zone.internal_id, 
                    zone.description, zone.municipality, str(zone.geography_id), ",".join(str(geography_id) for geography_id in zone.prev_geographies), zone.effective_date,
                    zone.propose_retirement, zone.published_date, zone.published_retire_date, zone.created_at, zone.modified_at,
                    zone.created_by, zone.last_modified_by, zone.phase))

    with gpkg.connection as conn:
        conn.executemany("""
            INSERT INTO monitoring (SHAPE, name, internal_id, description, _municipality, _geography_id,
                         _prev_geographies, _effective_date, _propose_retirement, _published_date, _published_retire_date, _created_at,
                         _modified_at, _created_by, _last_modified_by, _phase) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)

def add_data_to_no_parking(gpkg: GeoPackage, zones: Iterator[Zone]):
    rows = []
    for zone in zones:
        rows.append((MultiPolygon([zone.area.geometry.coordinates], srs_id=4326), zone.name, zone.internal_id, 
                    zone.description, zone.municipality, str(zone.geography_id), ",".join(str(geography_id) for geography_id in zone.prev_geographies), zone.effective_date,
                    zone.propose_retirement, zone.published_date, zone.published_retire_date, zone.created_at, zone.modified_at,
                    zone.created_by, zone.last_modified_by, zone.phase))

    with gpkg.connection as conn:
        conn.executemany("""
            INSERT INTO no_parking (SHAPE, name, internal_id, description, _municipality, _geography_id,
                         _prev_geographies, _effective_date, _propose_retirement, _published_date, _published_retire_date, _created_at,
                         _modified_at, _created_by, _last_modified_by, _phase) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)

def get_microhub_control_status(status: dict):
    if status.get("control_automatic") == True:
        return "control_automatic"
    if status.get("is_returning") == True:
        return "manually_open"
    return "manually_closed"

def add_data_to_microhub(gpkg: GeoPackage, zones: Iterator[Zone]):
    rows = []
    for zone in zones:
        capacity = zone.stop.capacity
        rows.append((MultiPolygon([zone.area.geometry.coordinates], srs_id=4326), zone.name, zone.internal_id, 
                    zone.description, zone.municipality, str(zone.geography_id), ",".join(str(geography_id) for geography_id in zone.prev_geographies), zone.effective_date,
                    zone.propose_retirement, zone.published_date, zone.published_retire_date, zone.created_at, zone.modified_at,
                    zone.created_by, zone.last_modified_by, zone.phase,
                    capacity.get("combined"), capacity.get("bicycle"), capacity.get("moped"), capacity.get("cargo_bicycle"), capacity.get("car"),
                    get_microhub_control_status(zone.stop.status), zone.stop.is_virtual))

    with gpkg.connection as conn:
        conn.executemany("""
            INSERT INTO microhubs (SHAPE, name, internal_id, description, _municipality, _geography_id,
                         _prev_geographies, _effective_date, _propose_retirement, _published_date, _published_retire_date, _created_at,
                         _modified_at, _created_by, _last_modified_by, _phase, 
                        capacity_combined, capacity_bicycle, capacity_moped, capacity_cargo_bicycle, capacity_car,
                        microhub_control_status, is_virtual) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)

def export(export_request: ExportRequest):
    zones = []
    if len(export_request.geography_ids) < 1:
        raise HTTPException(status_code=400, detail="You should specify at least one geography_uuid")
    with db_helper.get_resource() as (cur, conn): 
        zones = get_zones.get_zones_by_ids(cur, export_request.geography_ids)

    file_name = f"/tmp/dashboarddeelmobiliteit_gpkg_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gpkg"
    gpkg: GeoPackage = GeoPackage.create(file_name)

    fields: tuple[Field, ...] = (
        Field('name', SQLFieldType.text),
        Field('internal_id', SQLFieldType.text),
        Field('description', SQLFieldType.text),
        Field('_municipality', SQLFieldType.text),
        Field('_geography_id', SQLFieldType.text),
        Field('_prev_geographies', SQLFieldType.text),
        Field('_effective_date', SQLFieldType.text),
        Field('_propose_retirement', SQLFieldType.boolean),
        Field('_published_date', SQLFieldType.text),
        Field('_published_retire_date', SQLFieldType.text),
        Field('_created_at', SQLFieldType.text),
        Field('_modified_at', SQLFieldType.text),
        Field('_created_by', SQLFieldType.text),
        Field('_last_modified_by', SQLFieldType.text),
        Field('_phase', SQLFieldType.text)
    )
    fields_microhub: tuple[Field, ...] = (
        Field('name', SQLFieldType.text),
        Field('internal_id', SQLFieldType.text),
        Field('description', SQLFieldType.text),
        Field('capacity_combined', SQLFieldType.integer),
        Field('capacity_bicycle', SQLFieldType.integer),
        Field('capacity_moped', SQLFieldType.integer),
        Field('capacity_cargo_bicycle', SQLFieldType.integer),
        Field('capacity_car', SQLFieldType.integer),
        Field('microhub_control_status', SQLFieldType.text),
        Field('is_virtual', SQLFieldType.boolean),
        Field('_municipality', SQLFieldType.text),
        Field('_geography_id', SQLFieldType.text),
        Field('_prev_geographies', SQLFieldType.text),
        Field('_effective_date', SQLFieldType.text),
        Field('_propose_retirement', SQLFieldType.boolean),
        Field('_published_date', SQLFieldType.text),
        Field('_published_retire_date', SQLFieldType.text),
        Field('_created_at', SQLFieldType.text),
        Field('_modified_at', SQLFieldType.text),
        Field('_created_by', SQLFieldType.text),
        Field('_last_modified_by', SQLFieldType.text),
        Field('_phase', SQLFieldType.text)
    )
    create_layer("microhubs", gpkg=gpkg, fields=fields_microhub)
    create_layer("monitoring", gpkg=gpkg, fields=fields)
    create_layer("no_parking", gpkg=gpkg, fields=fields)
    
   
    microhubs = filter(lambda zone: zone.geography_type == "stop", zones)
    add_data_to_microhub(gpkg=gpkg, zones=microhubs)
    
    no_parking = filter(lambda zone: zone.geography_type == "no_parking", zones)
    add_data_to_no_parking(gpkg=gpkg, zones=no_parking)
    
    monitoring = filter(lambda zone: zone.geography_type == "monitoring", zones)
    add_data_to_monitoring(gpkg=gpkg, zones=monitoring)


    # Generate some random points and attributes
    rows: list[tuple[MultiPolygon, str]] = []
    for zone in zones:
        coordinates_list = [[(pos.longitude, pos.latitude) for pos in sublist] for sublist in zone.area.geometry.coordinates]
        print(coordinates_list)
        multi_polygon = MultiPolygon([coordinates_list], srs_id=4326)
        rows.append((multi_polygon, str(zone.geography_id)))

 


    res = create_zip(file_name)
    zip_file_name = f"{os.path.basename(file_name).split(".")[0]}.zip"
    return res, zip_file_name