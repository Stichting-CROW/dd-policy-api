from pydantic import BaseModel

class Municipality(BaseModel):
    gmcode: str
    name: str