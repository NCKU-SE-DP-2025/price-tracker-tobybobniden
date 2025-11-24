import requests
from typing import Optional, List, Union


class PriceService:
    BASE_URL = "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice"
    
    @staticmethod
    def get_necessities_prices(category: Optional[str] = None, commodity: Optional[str] = None) -> Union[List[dict], dict]:
        """查詢民生物資價格
        
        Args:
            category: 類別 (e.g., "鮮乳")
            commodity: 產品名稱 (e.g., "統一瑞德高優質鮮乳")
        
        Returns:
            List of price data or error dict
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
            
            # Ensure data is always a list
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                # Handle case where API returns {"data": [...]}
                return data.get("data", [])
            else:
                # Wrap single object in list if needed
                return [data] if data else []
                
        except requests.RequestException as e:
            return {"error": str(e)}
        except ValueError as e:
            # JSON decode error
            return {"error": f"Invalid response format: {str(e)}"}
