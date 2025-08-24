"""
Gold Price Analyzer

This module provides price analysis and trend detection functionality
for gold price monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

from .gold_price_collector import GoldPriceData

class TrendDirection(Enum):
    """Price trend directions"""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"

@dataclass
class PriceAlert:
    """Price alert data structure"""
    symbol: str
    alert_type: str
    message: str
    current_price: float
    previous_price: float
    change_percent: float
    timestamp: datetime
    severity: str = "medium"  # low, medium, high, critical
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "alert_type": self.alert_type,
            "message": self.message,
            "current_price": self.current_price,
            "previous_price": self.previous_price,
            "change_percent": self.change_percent,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity
        }

@dataclass
class PriceTrend:
    """Price trend analysis result"""
    symbol: str
    direction: TrendDirection
    strength: float  # 0-1, where 1 is strongest trend
    duration_hours: float
    average_change_percent: float
    volatility: float
    
class PriceAnalyzer:
    """Analyzes gold price data for trends and alerts"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.price_history = {}  # symbol -> list of price data
        self.max_history_size = config.get("max_history_size", 100)
        
        # Alert thresholds
        self.alert_thresholds = {
            "minor_change": config.get("minor_change_threshold", 2.0),  # 2%
            "major_change": config.get("major_change_threshold", 5.0),  # 5%
            "critical_change": config.get("critical_change_threshold", 10.0),  # 10%
            "volatility_threshold": config.get("volatility_threshold", 3.0)  # 3%
        }
        
    def add_price_data(self, price_data: GoldPriceData):
        """Add new price data to history"""
        symbol = price_data.symbol
        
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            
        self.price_history[symbol].append(price_data)
        
        # Maintain history size limit
        if len(self.price_history[symbol]) > self.max_history_size:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history_size:]
            
    def calculate_price_change(self, symbol: str, hours_back: int = 1) -> Optional[Tuple[float, float]]:
        """Calculate price change over specified time period"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return None
            
        current_data = self.price_history[symbol][-1]
        current_time = current_data.timestamp
        target_time = current_time - timedelta(hours=hours_back)
        
        # Find the closest price data to target time
        previous_data = None
        min_time_diff = float('inf')
        
        for data in self.price_history[symbol][:-1]:
            time_diff = abs((data.timestamp - target_time).total_seconds())
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                previous_data = data
                
        if not previous_data:
            # Fallback to previous data point
            previous_data = self.price_history[symbol][-2]
            
        current_price = current_data.price
        previous_price = previous_data.price
        
        if previous_price == 0:
            return None
            
        change_percent = ((current_price - previous_price) / previous_price) * 100
        return change_percent, previous_price
        
    def analyze_trend(self, symbol: str, hours_back: int = 24) -> Optional[PriceTrend]:
        """Analyze price trend over specified time period"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 3:
            return None
            
        current_time = self.price_history[symbol][-1].timestamp
        target_time = current_time - timedelta(hours=hours_back)
        
        # Filter data within time range
        relevant_data = [
            data for data in self.price_history[symbol]
            if data.timestamp >= target_time
        ]
        
        if len(relevant_data) < 3:
            return None
            
        prices = [data.price for data in relevant_data]
        timestamps = [data.timestamp for data in relevant_data]
        
        # Calculate trend direction and strength
        price_changes = []
        for i in range(1, len(prices)):
            change = ((prices[i] - prices[i-1]) / prices[i-1]) * 100
            price_changes.append(change)
            
        if not price_changes:
            return None
            
        avg_change = statistics.mean(price_changes)
        volatility = statistics.stdev(price_changes) if len(price_changes) > 1 else 0
        
        # Determine trend direction
        if abs(avg_change) < 0.5:
            direction = TrendDirection.STABLE
        elif volatility > self.alert_thresholds["volatility_threshold"]:
            direction = TrendDirection.VOLATILE
        elif avg_change > 0:
            direction = TrendDirection.RISING
        else:
            direction = TrendDirection.FALLING
            
        # Calculate trend strength (0-1)
        strength = min(abs(avg_change) / 5.0, 1.0)  # Normalize to 5% max
        
        # Calculate actual duration
        duration_hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
        
        return PriceTrend(
            symbol=symbol,
            direction=direction,
            strength=strength,
            duration_hours=duration_hours,
            average_change_percent=avg_change,
            volatility=volatility
        )
        
    def check_alerts(self, symbol: str) -> List[PriceAlert]:
        """Check for price alerts based on current data"""
        alerts = []
        
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return alerts
            
        current_data = self.price_history[symbol][-1]
        
        # Check short-term changes (1 hour)
        change_result = self.calculate_price_change(symbol, hours_back=1)
        if change_result:
            change_percent, previous_price = change_result
            
            alert_type = None
            severity = "low"
            
            if abs(change_percent) >= self.alert_thresholds["critical_change"]:
                alert_type = "critical_change"
                severity = "critical"
            elif abs(change_percent) >= self.alert_thresholds["major_change"]:
                alert_type = "major_change"
                severity = "high"
            elif abs(change_percent) >= self.alert_thresholds["minor_change"]:
                alert_type = "minor_change"
                severity = "medium"
                
            if alert_type:
                direction = "increased" if change_percent > 0 else "decreased"
                message = f"{symbol} price {direction} by {abs(change_percent):.2f}% to ${current_data.price:.2f}"
                
                alert = PriceAlert(
                    symbol=symbol,
                    alert_type=alert_type,
                    message=message,
                    current_price=current_data.price,
                    previous_price=previous_price,
                    change_percent=change_percent,
                    timestamp=current_data.timestamp,
                    severity=severity
                )
                alerts.append(alert)
                
        # Check for high volatility
        trend = self.analyze_trend(symbol, hours_back=6)
        if trend and trend.volatility > self.alert_thresholds["volatility_threshold"]:
            message = f"{symbol} showing high volatility: {trend.volatility:.2f}% standard deviation"
            
            alert = PriceAlert(
                symbol=symbol,
                alert_type="high_volatility",
                message=message,
                current_price=current_data.price,
                previous_price=current_data.price,
                change_percent=0,
                timestamp=current_data.timestamp,
                severity="medium"
            )
            alerts.append(alert)
            
        return alerts
        
    def get_price_summary(self, symbol: str) -> Optional[Dict]:
        """Get comprehensive price summary for symbol"""
        if symbol not in self.price_history or not self.price_history[symbol]:
            return None
            
        current_data = self.price_history[symbol][-1]
        
        # Calculate various time period changes
        changes = {}
        for period in [1, 6, 24]:  # 1 hour, 6 hours, 24 hours
            change_result = self.calculate_price_change(symbol, hours_back=period)
            if change_result:
                changes[f"{period}h"] = {
                    "change_percent": change_result[0],
                    "previous_price": change_result[1]
                }
                
        # Get trend analysis
        trend = self.analyze_trend(symbol, hours_back=24)
        
        # Get recent alerts
        alerts = self.check_alerts(symbol)
        
        return {
            "symbol": symbol,
            "current_price": current_data.price,
            "currency": current_data.currency,
            "timestamp": current_data.timestamp.isoformat(),
            "source": current_data.source,
            "changes": changes,
            "trend": {
                "direction": trend.direction.value if trend else "unknown",
                "strength": trend.strength if trend else 0,
                "volatility": trend.volatility if trend else 0
            } if trend else None,
            "alerts": [alert.to_dict() for alert in alerts],
            "data_points": len(self.price_history[symbol])
        }
        
    def get_all_summaries(self) -> Dict[str, Dict]:
        """Get price summaries for all tracked symbols"""
        summaries = {}
        for symbol in self.price_history.keys():
            summary = self.get_price_summary(symbol)
            if summary:
                summaries[symbol] = summary
        return summaries

# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example configuration
    config = {
        "minor_change_threshold": 2.0,
        "major_change_threshold": 5.0,
        "critical_change_threshold": 10.0,
        "volatility_threshold": 3.0,
        "max_history_size": 100
    }
    
    analyzer = PriceAnalyzer(config)
    
    # Example: Add some test data
    from datetime import datetime
    
    test_data = GoldPriceData(
        symbol="XAUUSD",
        price=2000.0,
        timestamp=datetime.now(),
        change_percent=0.0,
        currency="USD",
        source="test"
    )
    
    analyzer.add_price_data(test_data)
    
    # Add another data point with price change
    test_data2 = GoldPriceData(
        symbol="XAUUSD",
        price=2100.0,  # 5% increase
        timestamp=datetime.now(),
        change_percent=5.0,
        currency="USD",
        source="test"
    )
    
    analyzer.add_price_data(test_data2)
    
    # Check for alerts
    alerts = analyzer.check_alerts("XAUUSD")
    for alert in alerts:
        print(f"Alert: {alert.message} (Severity: {alert.severity})")
        
    # Get summary
    summary = analyzer.get_price_summary("XAUUSD")
    print("Summary:", summary)