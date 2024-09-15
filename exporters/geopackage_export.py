from fudgeo.geopkg import GeoPackage

from exporters.export_request import ExportRequest
from fastapi import HTTPException
from db_helper import db_helper
from zones import get_zones, zone
import zipfile
import io
from datetime import datetime

def create_zip(file_name: str):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.write(file_name)
    return zip_buffer

def export(export_request: ExportRequest):
    zones = []
    if len(export_request.geography_ids) < 1:
        raise HTTPException(status_code=400, detail="You should specify at least one geography_uuid")
    with db_helper.get_resource() as (cur, conn): 
        zones = get_zones.get_zones_by_ids(cur, export_request.geography_ids)

    file_name = f"/tmp/export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.gpkg"
    gpkg: GeoPackage = GeoPackage.create(file_name)
    res = create_zip(file_name)
    return res