from kml import db
import simplekml
import io
import zipfile
import shapely.wkt
from shapely.geometry import mapping
from fastapi import HTTPException
from uuid import UUID
from db_helper import db_helper
from pydantic import BaseModel
from zones import get_zones, zone
import json

def create_kml(zones: list[zone.Zone], background_color = "7F2471FA"):
    mds_base_url = "https://mds.dashboarddeelmobiliteit.nl"
    kml_file = simplekml.Kml()
    for zone in zones:
        pol = kml_file.newpolygon(name=zone.name)
        pol.outerboundaryis = zone.area.geometry.coordinates[0][0]
        pol.extendeddata.newdata(name='_geography_id', value=zone.geography_id)
        pol.extendeddata.newdata(name='internal_id', value=zone.internal_id)
        pol.extendeddata.newdata(name='geography_type', value=zone.geography_type)
        pol.extendeddata.newdata(name='description', value=zone.description)
        pol.extendeddata.newdata(name='_prev_geographies', value=json.dumps(zone.prev_geographies))

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
        pol.extendeddata.newdata(name='_created_by', value=zone.created_by)
        pol.extendeddata.newdata(name='_last_modified_by', value=zone.last_modified_by)
        pol.extendeddata.newdata(name='_phase', value=zone.phase)     

        pol.style.polystyle.color = background_color
        pol.style.polystyle.fill = 1
        pol.style.linestyle.color = 'FF000000'
        pol.linestyle.width = 1
    return kml_file.kml()

class ExportKMLRequest(BaseModel):
    geography_ids: list[UUID]

def export(export_kml_request: ExportKMLRequest):
    zones = []
    with db_helper.get_resource() as (cur, conn): 
        zones = get_zones.get_zones_by_ids(cur, export_kml_request.geography_ids)

    microhubs = filter(lambda zone: zone.geography_type == "stop", zones)
    exported_microhubs = create_kml(microhubs, "7F2471FA")
    no_parking = filter(lambda zone: zone.geography_type == "no_parking", zones)
    exported_no_parking = create_kml(no_parking, "7F3B24F9")
    monitoring = filter(lambda zone: zone.geography_type == "monitoring", zones)
    exported_monitoring = create_kml(monitoring, "7FEB9D1A")
    
    return create_zip([
        ("microhubs.kml", exported_microhubs),
        ("no_parking.kml", exported_no_parking),
        ("monitoring.kml", exported_monitoring),
        ("README.md", get_readme())
    ])
    

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