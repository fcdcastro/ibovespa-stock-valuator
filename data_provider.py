import os
import requests
from dotenv import load_dotenv

load_dotenv()

class BrapiProvider:
    BASE_URL = "https://brapi.dev/api/quote"

    def __init__(self):
        self.token = os.getenv("BRAPI_TOKEN")
        if not self.token:
            raise ValueError("BRAPI_TOKEN not found in .env file")

    def get_stock_data(self, ticker, modules="balanceSheetHistory,incomeStatementHistory"):
        """
        Fetches fundamental and market data for a given ticker.
        """
        url = f"{self.BASE_URL}/{ticker}"
        params = {
            "token": self.token,
            "modules": modules
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                print(f"No results found for ticker: {ticker}")
                return None
                
            return data["results"][0]
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None

    def get_available_tickers(self):
        """
        Fetches all available tickers from Brapi.
        """
        url = "https://brapi.dev/api/quote/list"
        params = {"token": self.token}
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return [stock['stock'] for stock in data.get('stocks', [])]
        except requests.exceptions.RequestException as e:
            print(f"Error fetching ticker list: {e}")
            return []

if __name__ == "__main__":
    # Test with VALE3
    provider = BrapiProvider()
    data = provider.get_stock_data("VALE3")
    if data:
        print(f"Successfully fetched data for {data.get('symbol')}")
        print(f"Price: {data.get('regularMarketPrice')}")
