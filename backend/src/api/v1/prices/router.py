from fastapi import APIRouter, Query
from typing import Optional, List
from src.api.v1.prices.service import PriceService
from src.api.v1.prices.schemas import NecessitiesPriceResponse

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/necessities-price", response_model=List[NecessitiesPriceResponse])
async def get_necessities_prices(
    category: Optional[str] = Query(None, alias="CategoryName"),
    commodity: Optional[str] = Query(None, alias="Name")
):
    return PriceService.get_necessities_prices(category, commodity)