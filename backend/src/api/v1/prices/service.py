import requests
from typing import Optional, List
from fastapi import HTTPException, status
from src.api.v1.prices.schemas import NecessitiesPriceResponse


class PriceService:
    BASE_URL = "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice"
    
    @staticmethod
    def get_necessities_prices(category: Optional[str] = None, commodity: Optional[str] = None) -> List[NecessitiesPriceResponse]:
        """查詢民生物資價格
        
        Args:
            category: 類別 (e.g., "鮮乳")
            commodity: 產品名稱 (e.g., "統一瑞德高優質鮮乳")
        
        Returns:
            List of price data
            
        Raises:
            HTTPException: If API request fails
        """
        params = {}
        if category:
            params["CategoryName"] = category
        if commodity:
            params["Name"] = commodity
        
        try:
            response = requests.get(PriceService.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            raw_list = []
            # Ensure data is always a list
            if isinstance(data, list):
                raw_list = data
            elif isinstance(data, dict) and "data" in data:
                raw_list = data.get("data", [])
            else:
                raw_list = [data] if data else []
            
            # Validate and parse using Pydantic
            # Note: The API returns Chinese keys, which matches our schema
            return [NecessitiesPriceResponse(**item) for item in raw_list]
                
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"External price API unavailable: {str(e)}"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Invalid response from external API: {str(e)}"
            )

