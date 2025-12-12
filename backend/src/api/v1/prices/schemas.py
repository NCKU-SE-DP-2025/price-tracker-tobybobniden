from pydantic import BaseModel
from typing import Optional, List


class PriceQueryRequest(BaseModel):
    category: Optional[str] = None
    commodity: Optional[str] = None


class NecessitiesPriceResponse(BaseModel):
    """Schema for necessities price data from government API"""
    類別: str
    編號: int
    產品名稱: str
    規格: str
    統計值: str
    時間起點: str
    時間終點: str
    
    class Config:
        populate_by_name = True


class NecessitiesPricesListResponse(List[NecessitiesPriceResponse]):
    """List of necessities prices"""
    pass
