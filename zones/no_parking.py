from typing import Optional, Dict
from pydantic import BaseModel, Field
import datetime

class NoParking(BaseModel):
    start_date: Optional[datetime.datetime] = datetime.datetime.now().astimezone()
    end_date: Optional[datetime.datetime]