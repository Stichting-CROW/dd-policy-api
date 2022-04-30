from typing import Optional
from fastapi import FastAPI
import zone

from pydantic import BaseModel

app = FastAPI()

@app.post("/zone")
def update_item(zone: zone.Zone):
    return zone