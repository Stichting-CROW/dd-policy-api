from pydantic import BaseModel
from typing import Optional


class Operator(BaseModel):
    system_id: str
    name: str
    color: str 
    operator_url: Optional[str]
    logo_url: Optional[str]

class OperatorResponse(BaseModel):
    operators: list[Operator]
