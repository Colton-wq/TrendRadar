"""
Gold Monitor Configuration Validator

This module provides validation functionality for gold monitoring configuration,
ensuring all required parameters are present and valid.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Configuration validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, message: str):
        """Add validation error"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add validation warning"""
        self.warnings.append(message)

class GoldMonitorConfigValidator:
    """Validates gold monitor configuration"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Required configuration keys
        self.required_keys = {
            'enabled': bool,
            'api_keys': dict,
            'monitoring': dict,
            'alerts': dict,
            'reporting': dict,
            'notifications': dict
        }
        
        # Required API keys
        self.api_key_fields = ['goldapi_key', 'jisu_api_key']
        
        # Required monitoring fields
        self.monitoring_fields = {
            'symbols': list,
            'update_interval': int,
            'cache_ttl': int,
            'max_history_size': int
        }
        
        # Required alert fields
        self.alert_fields = {
            'enabled': bool,
            'thresholds': dict,
            'global_settings': dict
        }
        
        # Required threshold fields
        self.threshold_fields = {
            'minor_change': (float, int),
            'major_change': (float, int),
            'critical_change': (float, int),
            'volatility_threshold': (float, int)
        }
        
        # Valid symbols
        self.valid_symbols = ['XAUUSD', 'AU9999', 'XAGUSD', 'XPTUSD', 'XPDUSD']
        
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate complete gold monitor configuration"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not config:
            result.add_error("Gold monitor configuration is empty")
            return result
        
        # Validate top-level structure
        self._validate_structure(config, result)
        
        if not result.is_valid:
            return result
        
        # Validate individual sections
        self._validate_api_keys(config.get('api_keys', {}), result)
        self._validate_monitoring(config.get('monitoring', {}), result)
        self._validate_alerts(config.get('alerts', {}), result)
        self._validate_reporting(config.get('reporting', {}), result)
        self._validate_notifications(config.get('notifications', {}), result)
        
        # Cross-validation checks
        self._validate_cross_dependencies(config, result)
        
        return result
    
    def _validate_structure(self, config: Dict[str, Any], result: ValidationResult):
        """Validate top-level configuration structure"""
        for key, expected_type in self.required_keys.items():
            if key not in config:
                result.add_error(f"Missing required configuration key: {key}")
            elif not isinstance(config[key], expected_type):
                result.add_error(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(config[key]).__name__}")
    
    def _validate_api_keys(self, api_keys: Dict[str, Any], result: ValidationResult):
        """Validate API keys configuration"""
        if not api_keys:
            result.add_warning("No API keys configured - gold monitoring will not work")
            return
        
        # Check if at least one API key is provided
        has_valid_key = False
        for key_field in self.api_key_fields:
            if key_field in api_keys and api_keys[key_field]:
                has_valid_key = True
                
                # Validate key format (basic check)
                key_value = api_keys[key_field]
                if not isinstance(key_value, str):
                    result.add_error(f"API key {key_field} must be a string")
                elif len(key_value.strip()) < 10:
                    result.add_warning(f"API key {key_field} seems too short (less than 10 characters)")
        
        if not has_valid_key:
            result.add_warning("No valid API keys configured - gold monitoring will not work")
    
    def _validate_monitoring(self, monitoring: Dict[str, Any], result: ValidationResult):
        """Validate monitoring configuration"""
        for field, expected_type in self.monitoring_fields.items():
            if field not in monitoring:
                result.add_error(f"Missing monitoring field: {field}")
            elif not isinstance(monitoring[field], expected_type):
                result.add_error(f"Invalid type for monitoring.{field}: expected {expected_type.__name__}")
            else:
                # Field-specific validation
                if field == 'symbols':
                    self._validate_symbols(monitoring[field], result)
                elif field == 'update_interval':
                    self._validate_update_interval(monitoring[field], result)
                elif field == 'cache_ttl':
                    self._validate_cache_ttl(monitoring[field], result)
                elif field == 'max_history_size':
                    self._validate_history_size(monitoring[field], result)
    
    def _validate_symbols(self, symbols: List[str], result: ValidationResult):
        """Validate monitoring symbols"""
        if not symbols:
            result.add_error("At least one symbol must be configured for monitoring")
            return
        
        for symbol in symbols:
            if not isinstance(symbol, str):
                result.add_error(f"Symbol must be a string: {symbol}")
            elif symbol not in self.valid_symbols:
                result.add_warning(f"Unknown symbol: {symbol}. Valid symbols: {', '.join(self.valid_symbols)}")
    
    def _validate_update_interval(self, interval: int, result: ValidationResult):
        """Validate update interval"""
        if interval < 60:
            result.add_warning("Update interval less than 60 seconds may hit API rate limits")
        elif interval > 86400:  # 24 hours
            result.add_warning("Update interval greater than 24 hours may provide stale data")
    
    def _validate_cache_ttl(self, ttl: int, result: ValidationResult):
        """Validate cache TTL"""
        if ttl < 30:
            result.add_warning("Cache TTL less than 30 seconds may cause excessive API calls")
        elif ttl > 3600:  # 1 hour
            result.add_warning("Cache TTL greater than 1 hour may provide stale data")
    
    def _validate_history_size(self, size: int, result: ValidationResult):
        """Validate history size"""
        if size < 10:
            result.add_warning("History size less than 10 may not provide enough data for trend analysis")
        elif size > 1000:
            result.add_warning("History size greater than 1000 may consume excessive memory")
    
    def _validate_alerts(self, alerts: Dict[str, Any], result: ValidationResult):
        """Validate alerts configuration"""
        for field, expected_type in self.alert_fields.items():
            if field not in alerts:
                result.add_error(f"Missing alerts field: {field}")
            elif not isinstance(alerts[field], expected_type):
                result.add_error(f"Invalid type for alerts.{field}: expected {expected_type.__name__}")
        
        # Validate thresholds
        if 'thresholds' in alerts:
            self._validate_thresholds(alerts['thresholds'], result)
        
        # Validate global settings
        if 'global_settings' in alerts:
            self._validate_global_settings(alerts['global_settings'], result)
    
    def _validate_thresholds(self, thresholds: Dict[str, Any], result: ValidationResult):
        """Validate alert thresholds"""
        for field, expected_types in self.threshold_fields.items():
            if field not in thresholds:
                result.add_error(f"Missing threshold field: {field}")
            elif not isinstance(thresholds[field], expected_types):
                type_names = [t.__name__ for t in expected_types] if isinstance(expected_types, tuple) else [expected_types.__name__]
                result.add_error(f"Invalid type for thresholds.{field}: expected {' or '.join(type_names)}")
            else:
                # Validate threshold values
                value = thresholds[field]
                if value <= 0:
                    result.add_error(f"Threshold {field} must be positive: {value}")
                elif value > 100:
                    result.add_warning(f"Threshold {field} greater than 100% seems unusual: {value}")
        
        # Validate threshold relationships
        if all(field in thresholds for field in ['minor_change', 'major_change', 'critical_change']):
            minor = thresholds['minor_change']
            major = thresholds['major_change']
            critical = thresholds['critical_change']
            
            if minor >= major:
                result.add_error(f"Minor change threshold ({minor}) should be less than major change threshold ({major})")
            if major >= critical:
                result.add_error(f"Major change threshold ({major}) should be less than critical change threshold ({critical})")
    
    def _validate_global_settings(self, settings: Dict[str, Any], result: ValidationResult):
        """Validate global alert settings"""
        if 'notification_cooldown' in settings:
            cooldown = settings['notification_cooldown']
            if not isinstance(cooldown, int) or cooldown < 0:
                result.add_error("notification_cooldown must be a non-negative integer")
            elif cooldown > 3600:
                result.add_warning("notification_cooldown greater than 1 hour may delay important alerts")
        
        if 'max_alerts_per_hour' in settings:
            max_alerts = settings['max_alerts_per_hour']
            if not isinstance(max_alerts, int) or max_alerts <= 0:
                result.add_error("max_alerts_per_hour must be a positive integer")
            elif max_alerts > 100:
                result.add_warning("max_alerts_per_hour greater than 100 may cause notification spam")
        
        if 'quiet_hours' in settings:
            self._validate_quiet_hours(settings['quiet_hours'], result)
    
    def _validate_quiet_hours(self, quiet_hours: Dict[str, Any], result: ValidationResult):
        """Validate quiet hours configuration"""
        if not isinstance(quiet_hours, dict):
            result.add_error("quiet_hours must be a dictionary")
            return
        
        if 'enabled' in quiet_hours and not isinstance(quiet_hours['enabled'], bool):
            result.add_error("quiet_hours.enabled must be a boolean")
        
        if quiet_hours.get('enabled', False):
            for time_field in ['start', 'end']:
                if time_field not in quiet_hours:
                    result.add_error(f"Missing quiet_hours.{time_field}")
                else:
                    time_value = quiet_hours[time_field]
                    if not self._is_valid_time_format(time_value):
                        result.add_error(f"Invalid time format for quiet_hours.{time_field}: {time_value} (expected HH:MM)")
    
    def _is_valid_time_format(self, time_str: str) -> bool:
        """Validate time format (HH:MM)"""
        if not isinstance(time_str, str):
            return False
        
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, IndexError):
            return False
    
    def _validate_reporting(self, reporting: Dict[str, Any], result: ValidationResult):
        """Validate reporting configuration"""
        if 'include_in_main_report' in reporting:
            if not isinstance(reporting['include_in_main_report'], bool):
                result.add_error("reporting.include_in_main_report must be a boolean")
        
        if 'generate_charts' in reporting:
            if not isinstance(reporting['generate_charts'], bool):
                result.add_error("reporting.generate_charts must be a boolean")
        
        if 'chart_time_range' in reporting:
            time_range = reporting['chart_time_range']
            if not isinstance(time_range, int) or time_range <= 0:
                result.add_error("reporting.chart_time_range must be a positive integer")
            elif time_range > 168:  # 1 week
                result.add_warning("chart_time_range greater than 168 hours (1 week) may affect performance")
    
    def _validate_notifications(self, notifications: Dict[str, Any], result: ValidationResult):
        """Validate notifications configuration"""
        if 'use_main_channels' in notifications:
            if not isinstance(notifications['use_main_channels'], bool):
                result.add_error("notifications.use_main_channels must be a boolean")
        
        if 'custom_template' in notifications:
            if not isinstance(notifications['custom_template'], bool):
                result.add_error("notifications.custom_template must be a boolean")
        
        for bool_field in ['include_trend_analysis', 'include_price_history']:
            if bool_field in notifications:
                if not isinstance(notifications[bool_field], bool):
                    result.add_error(f"notifications.{bool_field} must be a boolean")
    
    def _validate_cross_dependencies(self, config: Dict[str, Any], result: ValidationResult):
        """Validate cross-dependencies between configuration sections"""
        # If gold monitoring is enabled, ensure at least one API key is configured
        if config.get('enabled', False):
            api_keys = config.get('api_keys', {})
            has_api_key = any(api_keys.get(key) for key in self.api_key_fields)
            
            if not has_api_key:
                result.add_error("Gold monitoring is enabled but no API keys are configured")
        
        # If alerts are enabled, ensure monitoring is properly configured
        alerts = config.get('alerts', {})
        if alerts.get('enabled', False):
            monitoring = config.get('monitoring', {})
            if not monitoring.get('symbols'):
                result.add_error("Alerts are enabled but no symbols are configured for monitoring")
        
        # If notifications use main channels, warn if no webhook URLs are configured
        notifications = config.get('notifications', {})
        if notifications.get('use_main_channels', True):
            # This would need to check the main notification configuration
            # For now, just add a note
            result.add_warning("Notifications use main channels - ensure webhook URLs are configured in main notification section")

def validate_gold_monitor_config(config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate gold monitor configuration
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = GoldMonitorConfigValidator()
    result = validator.validate_config(config)
    return result.is_valid, result.errors, result.warnings

# Example usage
if __name__ == "__main__":
    # Example configuration for testing
    test_config = {
        'enabled': True,
        'api_keys': {
            'goldapi_key': 'test_key_123456789',
            'jisu_api_key': ''
        },
        'monitoring': {
            'symbols': ['XAUUSD', 'AU9999'],
            'update_interval': 3600,
            'cache_ttl': 300,
            'max_history_size': 100
        },
        'alerts': {
            'enabled': True,
            'thresholds': {
                'minor_change': 2.0,
                'major_change': 5.0,
                'critical_change': 10.0,
                'volatility_threshold': 3.0
            },
            'global_settings': {
                'notification_cooldown': 300,
                'max_alerts_per_hour': 10,
                'quiet_hours': {
                    'enabled': True,
                    'start': '22:00',
                    'end': '08:00'
                }
            }
        },
        'reporting': {
            'include_in_main_report': True,
            'generate_charts': True,
            'chart_time_range': 24
        },
        'notifications': {
            'use_main_channels': True,
            'custom_template': False,
            'include_trend_analysis': True,
            'include_price_history': True
        }
    }
    
    # Test validation
    is_valid, errors, warnings = validate_gold_monitor_config(test_config)
    
    print(f"Configuration valid: {is_valid}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")