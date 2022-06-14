from typing import Optional
from pydantic import BaseModel
import datetime

class NoParking(BaseModel):
    start_date: Optional[datetime.datetime] = datetime.datetime.now().astimezone()
    end_date: Optional[datetime.datetime]