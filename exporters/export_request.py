from pydantic import BaseModel
from uuid import UUID

class ExportRequest(BaseModel):
    geography_ids: list[UUID]