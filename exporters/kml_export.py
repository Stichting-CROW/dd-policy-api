import simplekml
import io
import zipfile
import shapely.wkt
from shapely.geometry import mapping
from fastapi import HTTPException
from db_helper import db_helper
from pydantic import BaseModel
from zones import get_zones, zone
from exporters.export_request import ExportRequest
import json
from datetime import datetime

def add_polygon(kml_file, zone, mds_base_url: str, background_color: str):
    pol = kml_file.newpolygon(name=zone.name, description=zone.description)
        
    pol.outerboundaryis.coords = zone.area.geometry.coordinates[0]
    pol.extendeddata.newdata(name='_geography_id', value=zone.geography_id)
    pol.extendeddata.newdata(name='internal_id', value=zone.internal_id)
    pol.extendeddata.newdata(name='geography_type', value=zone.geography_type.value)
    pol.extendeddata.newdata(name='_prev_geographies', value=json.dumps([str(prev_geography_id) for prev_geography_id in zone.prev_geographies]))

    if zone.phase != "concept":
        pol.extendeddata.newdata(name='_effective_date', value=zone.effective_date)
        pol.extendeddata.newdata(name='_published_date', value=zone.published_date)
    
    if zone.phase not in ["concept", "commited_concept"]:
        pol.extendeddata.newdata(name='_mds_geography_url', value=mds_base_url + "/geographies/" + str(zone.geography_id))
    

    if zone.phase in ["", "", ""]:
        pol.extendeddata.newdata(name='_published_retire_date', value=zone.published_retire_date)
        pol.extendeddata.newdata(name='_retire_date', value=zone.retire_date)
    if zone.stop:
        pol.extendeddata.newdata(name='_stop_id', value=str(zone.stop.stop_id))
        pol.extendeddata.newdata(name='_mds_stop_url', value=mds_base_url + "/stops/" + str(zone.stop.stop_id))
    
    
    pol.extendeddata.newdata(name='_created_at', value=zone.created_at)
    pol.extendeddata.newdata(name='_modified_at', value=zone.modified_at)
    pol.extendeddata.newdata(name='_phase', value=zone.phase)     

    pol.style.polystyle.color = background_color
    pol.style.polystyle.fill = 1
    pol.style.linestyle.color = 'FF000000'
    pol.linestyle.width = 1
    return kml_file

def add_multi_polygon(kml_file: simplekml.Kml, zone: zone.Zone, mds_base_url: str, background_color: str):
    multi_polygon = kml_file.newmultigeometry(name=zone.name, description=zone.description)

    for polygon in zone.area.geometry.coordinates:
        pol = multi_polygon.newpolygon()
        print(polygon)
        pol.outerboundaryis.coords = polygon[0]
    multi_polygon.extendeddata.newdata(name='_geography_id', value=zone.geography_id)
    multi_polygon.extendeddata.newdata(name='internal_id', value=zone.internal_id)
    multi_polygon.extendeddata.newdata(name='geography_type', value=zone.geography_type.value)
    multi_polygon.extendeddata.newdata(name='_prev_geographies', value=json.dumps([str(prev_geography_id) for prev_geography_id in zone.prev_geographies]))

    if zone.phase != "concept":
        multi_polygon.extendeddata.newdata(name='_effective_date', value=zone.effective_date)
        multi_polygon.extendeddata.newdata(name='_published_date', value=zone.published_date)
    
    if zone.phase not in ["concept", "commited_concept"]:
        multi_polygon.extendeddata.newdata(name='_mds_geography_url', value=mds_base_url + "/geographies/" + str(zone.geography_id))
    

    if zone.phase in ["", "", ""]:
        multi_polygon.extendeddata.newdata(name='_published_retire_date', value=zone.published_retire_date)
        multi_polygon.extendeddata.newdata(name='_retire_date', value=zone.retire_date)
    if zone.stop:
        multi_polygon.extendeddata.newdata(name='_stop_id', value=str(zone.stop.stop_id))
        multi_polygon.extendeddata.newdata(name='_mds_stop_url', value=mds_base_url + "/stops/" + str(zone.stop.stop_id))
    
    
    multi_polygon.extendeddata.newdata(name='_created_at', value=zone.created_at)
    multi_polygon.extendeddata.newdata(name='_modified_at', value=zone.modified_at)
    multi_polygon.extendeddata.newdata(name='_phase', value=zone.phase)     

    multi_polygon.style.polystyle.color = background_color
    multi_polygon.style.polystyle.fill = 1
    multi_polygon.style.linestyle.color = 'FF000000'
    multi_polygon.linestyle.width = 1
    return kml_file


def create_kml(zones: list[zone.Zone], background_color = "7F2471FA"):
    mds_base_url = "https://mds.dashboarddeelmobiliteit.nl"
    kml_file = simplekml.Kml()
    for zone in zones:
        if zone.area.geometry.type == "MultiPolygon":
            kml_file = add_multi_polygon(kml_file=kml_file, zone=zone, mds_base_url=mds_base_url, background_color=background_color)
        else:
            kml_file = add_polygon(kml_file=kml_file, zone=zone, mds_base_url=mds_base_url, background_color=background_color)

    return kml_file.kml()



def export(export_kml_request: ExportRequest):
    zones = []
    if len(export_kml_request.geography_ids) < 1:
        raise HTTPException(status_code=400, detail="You should specify at least one geography_uuid")
    with db_helper.get_resource() as (cur, conn): 
        zones = get_zones.get_zones_by_ids(cur, export_kml_request.geography_ids)

    microhubs = filter(lambda zone: zone.geography_type == "stop", zones)
    exported_microhubs = create_kml(microhubs, "7F2471FA")
    no_parking = filter(lambda zone: zone.geography_type == "no_parking", zones)
    exported_no_parking = create_kml(no_parking, "7F3B24F9")
    monitoring = filter(lambda zone: zone.geography_type == "monitoring", zones)
    exported_monitoring = create_kml(monitoring, "7FEB9D1A")
    
    file_name = f"dashboarddeelmobiliteit_kml_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return create_zip([
        ("microhubs.kml", exported_microhubs),
        ("no_parking.kml", exported_no_parking),
        ("monitoring.kml", exported_monitoring),
        ("README.md", get_readme())
    ]), file_name
    

def create_zip(files: list[tuple]):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file_name, data in files:
            zip_file.writestr(file_name, data)
    return zip_buffer

    
def get_readme():
    return """
# KML export
This KML export is developed as a step in between manual data exchange and fully automated data exchange.

It consists of three files:
- microhubs.kml, the locations of all microhubs
- no_parking.kml, zones where parking for shared mobility is prohibited
- monitoring.kml, zones with a special interest for municipalities
This KML export can be downloaded by anyone via the GUI

If you want to import this data fully automatically and in real time (including real-time available parking spots)
it's recommended to use the MDS feed of dashboarddeelmobiliteit instead of this kml export.

1. stops(/microhubs) https://mds.dashboarddeelmobiliteit.nl/stops?municipality=<municipality_code>
2. Parking prohibited areas https://mds.dashboarddeelmobiliteit.nl/policies?municipality=<municipality_code>
3. Geographies https://mds.dashboarddeelmobiliteit.nl/geographies/<geography_id>

Example url's for the municipality of The Hague:
- https://mds.dashboarddeelmobiliteit.nl/stops?municipality=GM0518
- https://mds.dashboarddeelmobiliteit.nl/policies?municipality=GM0518
- https://mds.dashboarddeelmobiliteit.nl/geographies/6c2f08d4-5070-11ed-94a7-22d0d35466d6 

All these endpoints are based on the MDS standard https://github.com/openmobilityfoundation/mobility-data-specification   
    """