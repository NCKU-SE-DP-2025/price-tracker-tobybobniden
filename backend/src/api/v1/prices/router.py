from fastapi import APIRouter, Query
from typing import Optional
from src.api.v1.prices.service import PriceService

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/necessities-price")
async def get_necessities_prices(
    category: Optional[str] = Query(None),
    commodity: Optional[str] = Query(None)
):
    return PriceService.get_necessities_prices(category, commodity)