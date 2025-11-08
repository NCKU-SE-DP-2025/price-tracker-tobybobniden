import requests
from typing import Optional


class PriceService:
    BASE_URL = "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice"
    
    @staticmethod
    def get_necessities_prices(category: Optional[str] = None, commodity: Optional[str] = None) -> dict:
        """查詢民生物資價格"""
        params = {}
        if category:
            params["CategoryName"] = category
        if commodity:
            params["Name"] = commodity
        
        try:
            response = requests.get(PriceService.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}