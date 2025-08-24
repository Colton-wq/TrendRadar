"""
TrendRadar Gold Price Monitor Module

This module provides gold price monitoring functionality for TrendRadar.
It integrates with multiple free APIs to collect real-time gold price data
and provides analysis and alerting capabilities.
"""

__version__ = "1.0.0"
__author__ = "TrendRadar Team"

from .gold_price_collector import GoldPriceCollector, GoldAPICollector, JisuAPICollector, GoldPriceData
from .price_analyzer import PriceAnalyzer, PriceAlert, PriceTrend, TrendDirection
from .alert_rules import AlertRules, AlertRule, AlertType, AlertSeverity
from .gold_notification import GoldNotificationManager, GoldNotificationSender, GoldNotificationFormatter, NotificationConfig

__all__ = [
    # Data Collection
    "GoldPriceCollector",
    "GoldAPICollector", 
    "JisuAPICollector",
    "GoldPriceData",
    
    # Price Analysis
    "PriceAnalyzer",
    "PriceAlert",
    "PriceTrend",
    "TrendDirection",
    
    # Alert Rules
    "AlertRules",
    "AlertRule",
    "AlertType",
    "AlertSeverity",
    
    # Notifications
    "GoldNotificationManager",
    "GoldNotificationSender",
    "GoldNotificationFormatter",
    "NotificationConfig"
]