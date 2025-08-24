"""
TrendRadar Gold Price Monitor Module

This module provides gold price monitoring functionality for TrendRadar.
It integrates with multiple free APIs to collect real-time gold price data
and provides analysis and alerting capabilities.
"""

__version__ = "1.0.0"
__author__ = "TrendRadar Team"

from .gold_price_collector import GoldPriceCollector, GoldAPICollector, JisuAPICollector
from .price_analyzer import PriceAnalyzer
from .alert_rules import AlertRules

__all__ = [
    "GoldPriceCollector",
    "GoldAPICollector", 
    "JisuAPICollector",
    "PriceAnalyzer",
    "AlertRules"
]