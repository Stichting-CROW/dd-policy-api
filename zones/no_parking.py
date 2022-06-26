from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class NoParking(BaseModel):
    start_date: Optional[datetime] = Field(default_factory=datetime.now().astimezone())
    end_date: Optional[datetime]