"""
Gold Price Data Collector

This module provides unified interface for collecting gold price data
from multiple free APIs including GoldAPI.io and Jisu API.
"""

import requests
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import json

@dataclass
class GoldPriceData:
    """Standardized gold price data structure"""
    symbol: str
    price: float
    timestamp: datetime
    change_percent: Optional[float] = None
    currency: str = "USD"
    source: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "change_percent": self.change_percent,
            "currency": self.currency,
            "source": self.source
        }

class BaseGoldCollector:
    """Base class for gold price collectors"""
    
    def __init__(self, api_key: str = "", timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)
        self.last_request_time = 0
        self.min_request_interval = 1  # Minimum 1 second between requests
        
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Dict = None, headers: Dict = None) -> Optional[Dict]:
        """Make HTTP request with error handling and retries"""
        self._rate_limit()
        
        try:
            response = requests.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return None
    
    def get_price(self, symbol: str) -> Optional[GoldPriceData]:
        """Get price for specific symbol - to be implemented by subclasses"""
        raise NotImplementedError

class GoldAPICollector(BaseGoldCollector):
    """Collector for GoldAPI.io (Free: 100 requests/month)"""
    
    BASE_URL = "https://www.goldapi.io/api"
    
    def __init__(self, api_key: str, timeout: int = 30):
        super().__init__(api_key, timeout)
        self.min_request_interval = 2  # 2 seconds for free tier
        
    def get_price(self, symbol: str = "XAU") -> Optional[GoldPriceData]:
        """Get gold price from GoldAPI.io"""
        if not self.api_key:
            self.logger.error("GoldAPI.io API key not provided")
            return None
            
        url = f"{self.BASE_URL}/{symbol}/USD"
        headers = {"x-access-token": self.api_key}
        
        data = self._make_request(url, headers=headers)
        if not data:
            return None
            
        try:
            return GoldPriceData(
                symbol="XAUUSD",
                price=float(data.get("price", 0)),
                timestamp=datetime.fromtimestamp(data.get("timestamp", time.time())),
                change_percent=float(data.get("chp", 0)),
                currency="USD",
                source="GoldAPI.io"
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Data parsing error: {e}")
            return None

class JisuAPICollector(BaseGoldCollector):
    """Collector for Jisu API (Free: 100 requests/day)"""
    
    BASE_URL = "https://api.jisuapi.com/gold"
    
    def __init__(self, api_key: str, timeout: int = 30):
        super().__init__(api_key, timeout)
        self.min_request_interval = 1  # 1 second for free tier
        
    def get_shanghai_gold_price(self) -> Optional[List[GoldPriceData]]:
        """Get Shanghai Gold Exchange prices"""
        if not self.api_key:
            self.logger.error("Jisu API key not provided")
            return None
            
        url = f"{self.BASE_URL}/shgold"
        params = {"appkey": self.api_key}
        
        data = self._make_request(url, params=params)
        if not data or data.get("status") != 0:
            self.logger.error(f"Jisu API error: {data.get('msg', 'Unknown error') if data else 'No response'}")
            return None
            
        results = []
        for item in data.get("result", []):
            try:
                # Focus on AU9999 (万足金)
                if item.get("type") == "AU9999":
                    price_data = GoldPriceData(
                        symbol="AU9999",
                        price=float(item.get("price", 0)),
                        timestamp=datetime.now(),
                        change_percent=float(item.get("changepercent", "0").replace("%", "")),
                        currency="CNY",
                        source="Jisu API"
                    )
                    results.append(price_data)
            except (ValueError, KeyError) as e:
                self.logger.error(f"Data parsing error for item {item}: {e}")
                continue
                
        return results if results else None
    
    def get_price(self, symbol: str = "AU9999") -> Optional[GoldPriceData]:
        """Get specific gold price"""
        prices = self.get_shanghai_gold_price()
        if prices:
            for price in prices:
                if price.symbol == symbol:
                    return price
        return None

class GoldPriceCollector:
    """Main collector that aggregates data from multiple sources"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collectors = {}
        
        # Initialize collectors based on config
        if config.get("goldapi_key"):
            self.collectors["goldapi"] = GoldAPICollector(config["goldapi_key"])
            
        if config.get("jisu_api_key"):
            self.collectors["jisu"] = JisuAPICollector(config["jisu_api_key"])
            
        self.cache = {}
        self.cache_ttl = config.get("cache_ttl", 300)  # 5 minutes default
        
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached data is still valid"""
        if symbol not in self.cache:
            return False
        cache_time = self.cache[symbol].get("timestamp", 0)
        return (time.time() - cache_time) < self.cache_ttl
    
    def get_gold_prices(self) -> Dict[str, GoldPriceData]:
        """Get all available gold prices"""
        results = {}
        
        # Get XAUUSD from GoldAPI
        if "goldapi" in self.collectors:
            if not self._is_cache_valid("XAUUSD"):
                xau_price = self.collectors["goldapi"].get_price("XAU")
                if xau_price:
                    results["XAUUSD"] = xau_price
                    self.cache["XAUUSD"] = {
                        "data": xau_price,
                        "timestamp": time.time()
                    }
            else:
                results["XAUUSD"] = self.cache["XAUUSD"]["data"]
                
        # Get AU9999 from Jisu API
        if "jisu" in self.collectors:
            if not self._is_cache_valid("AU9999"):
                au_price = self.collectors["jisu"].get_price("AU9999")
                if au_price:
                    results["AU9999"] = au_price
                    self.cache["AU9999"] = {
                        "data": au_price,
                        "timestamp": time.time()
                    }
            else:
                results["AU9999"] = self.cache["AU9999"]["data"]
                
        return results
    
    def get_price_by_symbol(self, symbol: str) -> Optional[GoldPriceData]:
        """Get price for specific symbol"""
        prices = self.get_gold_prices()
        return prices.get(symbol)
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all collectors"""
        health = {}
        for name, collector in self.collectors.items():
            try:
                # Try to get a price to test the API
                if name == "goldapi":
                    result = collector.get_price("XAU")
                elif name == "jisu":
                    result = collector.get_price("AU9999")
                else:
                    result = None
                health[name] = result is not None
            except Exception as e:
                self.logger.error(f"Health check failed for {name}: {e}")
                health[name] = False
        return health

# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example configuration
    config = {
        "goldapi_key": "",  # Add your GoldAPI.io key
        "jisu_api_key": "",  # Add your Jisu API key
        "cache_ttl": 300
    }
    
    collector = GoldPriceCollector(config)
    
    # Test health check
    health = collector.health_check()
    print("Health check:", health)
    
    # Get all prices
    prices = collector.get_gold_prices()
    for symbol, price_data in prices.items():
        print(f"{symbol}: ${price_data.price} ({price_data.change_percent:+.2f}%)")