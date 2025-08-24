"""
Gold Monitor Module

This module provides gold price monitoring functionality for TrendRadar,
including price collection, analysis, alerting, and reporting.
"""

from .gold_price_collector import GoldPriceCollector, GoldPriceData
from .price_analyzer import PriceAnalyzer, PriceAlert, PriceTrend, TrendDirection
from .notification_manager import GoldNotificationManager
from .report_generator import GoldReportGenerator, GoldReportData
from .config_validator import GoldMonitorConfigValidator, validate_gold_monitor_config

__version__ = "1.0.0"
__author__ = "TrendRadar Team"

# Export main classes for easy import
__all__ = [
    # Core functionality
    'GoldPriceCollector',
    'PriceAnalyzer', 
    'GoldNotificationManager',
    'GoldReportGenerator',
    
    # Data structures
    'GoldPriceData',
    'PriceAlert',
    'PriceTrend',
    'TrendDirection',
    'GoldReportData',
    
    # Configuration
    'GoldMonitorConfigValidator',
    'validate_gold_monitor_config',
]

def get_version():
    """Get the version of the gold monitor module"""
    return __version__

def health_check():
    """Perform a basic health check of the gold monitor module"""
    try:
        # Test imports
        from .gold_price_collector import GoldPriceCollector
        from .price_analyzer import PriceAnalyzer
        from .notification_manager import GoldNotificationManager
        from .report_generator import GoldReportGenerator
        
        return {
            'status': 'healthy',
            'version': __version__,
            'modules': {
                'collector': True,
                'analyzer': True,
                'notification': True,
                'reporter': True
            }
        }
    except ImportError as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'version': __version__
        }