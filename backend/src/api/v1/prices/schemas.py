from pydantic import BaseModel
from typing import Optional

class PriceQueryRequest(BaseModel):
    category: Optional[str] = None
    commodity: Optional[str] = None

