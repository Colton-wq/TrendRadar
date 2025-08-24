"""
Gold Price Alert Rules Configuration

This module defines configurable alert rules for gold price monitoring.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Types of price alerts"""
    PRICE_CHANGE = "price_change"
    VOLATILITY = "volatility"
    TREND_REVERSAL = "trend_reversal"
    SUPPORT_RESISTANCE = "support_resistance"
    VOLUME_SPIKE = "volume_spike"

@dataclass
class AlertRule:
    """Individual alert rule configuration"""
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    threshold: float
    enabled: bool = True
    description: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "threshold": self.threshold,
            "enabled": self.enabled,
            "description": self.description
        }

class AlertRules:
    """Manages alert rules configuration"""
    
    def __init__(self, config: Dict = None):
        self.rules = {}
        self.global_settings = {
            "enabled": True,
            "notification_cooldown": 300,  # 5 minutes between same alerts
            "max_alerts_per_hour": 10,
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "08:00"
            }
        }
        
        if config:
            self.load_from_config(config)
        else:
            self._load_default_rules()
            
    def _load_default_rules(self):
        """Load default alert rules"""
        default_rules = [
            AlertRule(
                name="minor_price_change",
                alert_type=AlertType.PRICE_CHANGE,
                severity=AlertSeverity.LOW,
                threshold=2.0,  # 2% change
                description="Minor price change alert (2%)"
            ),
            AlertRule(
                name="major_price_change",
                alert_type=AlertType.PRICE_CHANGE,
                severity=AlertSeverity.HIGH,
                threshold=5.0,  # 5% change
                description="Major price change alert (5%)"
            ),
            AlertRule(
                name="critical_price_change",
                alert_type=AlertType.PRICE_CHANGE,
                severity=AlertSeverity.CRITICAL,
                threshold=10.0,  # 10% change
                description="Critical price change alert (10%)"
            ),
            AlertRule(
                name="high_volatility",
                alert_type=AlertType.VOLATILITY,
                severity=AlertSeverity.MEDIUM,
                threshold=3.0,  # 3% standard deviation
                description="High volatility alert"
            ),
            AlertRule(
                name="extreme_volatility",
                alert_type=AlertType.VOLATILITY,
                severity=AlertSeverity.HIGH,
                threshold=5.0,  # 5% standard deviation
                description="Extreme volatility alert"
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.name] = rule
            
    def load_from_config(self, config: Dict):
        """Load rules from configuration dictionary"""
        # Load global settings
        if "global_settings" in config:
            self.global_settings.update(config["global_settings"])
            
        # Load individual rules
        if "rules" in config:
            for rule_name, rule_config in config["rules"].items():
                rule = AlertRule(
                    name=rule_name,
                    alert_type=AlertType(rule_config.get("alert_type", "price_change")),
                    severity=AlertSeverity(rule_config.get("severity", "medium")),
                    threshold=rule_config.get("threshold", 5.0),
                    enabled=rule_config.get("enabled", True),
                    description=rule_config.get("description", "")
                )
                self.rules[rule_name] = rule
        else:
            self._load_default_rules()
            
    def get_rule(self, name: str) -> Optional[AlertRule]:
        """Get specific alert rule"""
        return self.rules.get(name)
        
    def get_rules_by_type(self, alert_type: AlertType) -> List[AlertRule]:
        """Get all rules of specific type"""
        return [rule for rule in self.rules.values() if rule.alert_type == alert_type]
        
    def get_rules_by_severity(self, severity: AlertSeverity) -> List[AlertRule]:
        """Get all rules of specific severity"""
        return [rule for rule in self.rules.values() if rule.severity == severity]
        
    def get_enabled_rules(self) -> List[AlertRule]:
        """Get all enabled rules"""
        return [rule for rule in self.rules.values() if rule.enabled]
        
    def enable_rule(self, name: str) -> bool:
        """Enable specific rule"""
        if name in self.rules:
            self.rules[name].enabled = True
            return True
        return False
        
    def disable_rule(self, name: str) -> bool:
        """Disable specific rule"""
        if name in self.rules:
            self.rules[name].enabled = False
            return True
        return False
        
    def add_rule(self, rule: AlertRule) -> bool:
        """Add new alert rule"""
        if rule.name not in self.rules:
            self.rules[rule.name] = rule
            return True
        return False
        
    def update_rule(self, name: str, **kwargs) -> bool:
        """Update existing rule"""
        if name not in self.rules:
            return False
            
        rule = self.rules[name]
        for key, value in kwargs.items():
            if hasattr(rule, key):
                if key == "alert_type" and isinstance(value, str):
                    value = AlertType(value)
                elif key == "severity" and isinstance(value, str):
                    value = AlertSeverity(value)
                setattr(rule, key, value)
        return True
        
    def remove_rule(self, name: str) -> bool:
        """Remove alert rule"""
        if name in self.rules:
            del self.rules[name]
            return True
        return False
        
    def get_threshold_for_change(self, change_percent: float) -> Optional[AlertRule]:
        """Get the appropriate rule for a price change percentage"""
        price_change_rules = self.get_rules_by_type(AlertType.PRICE_CHANGE)
        price_change_rules = [r for r in price_change_rules if r.enabled]
        
        # Sort by threshold descending to get the highest applicable threshold
        price_change_rules.sort(key=lambda x: x.threshold, reverse=True)
        
        for rule in price_change_rules:
            if abs(change_percent) >= rule.threshold:
                return rule
        return None
        
    def get_threshold_for_volatility(self, volatility: float) -> Optional[AlertRule]:
        """Get the appropriate rule for volatility"""
        volatility_rules = self.get_rules_by_type(AlertType.VOLATILITY)
        volatility_rules = [r for r in volatility_rules if r.enabled]
        
        # Sort by threshold descending to get the highest applicable threshold
        volatility_rules.sort(key=lambda x: x.threshold, reverse=True)
        
        for rule in volatility_rules:
            if volatility >= rule.threshold:
                return rule
        return None
        
    def is_alerts_enabled(self) -> bool:
        """Check if alerts are globally enabled"""
        return self.global_settings.get("enabled", True)
        
    def get_notification_cooldown(self) -> int:
        """Get notification cooldown period in seconds"""
        return self.global_settings.get("notification_cooldown", 300)
        
    def get_max_alerts_per_hour(self) -> int:
        """Get maximum alerts per hour limit"""
        return self.global_settings.get("max_alerts_per_hour", 10)
        
    def is_quiet_hours(self) -> bool:
        """Check if current time is in quiet hours"""
        quiet_config = self.global_settings.get("quiet_hours", {})
        if not quiet_config.get("enabled", False):
            return False
            
        from datetime import datetime
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        start_time = quiet_config.get("start", "22:00")
        end_time = quiet_config.get("end", "08:00")
        
        # Handle overnight quiet hours (e.g., 22:00 to 08:00)
        if start_time > end_time:
            return current_time >= start_time or current_time <= end_time
        else:
            return start_time <= current_time <= end_time
            
    def to_dict(self) -> Dict:
        """Convert all rules to dictionary"""
        return {
            "global_settings": self.global_settings,
            "rules": {name: rule.to_dict() for name, rule in self.rules.items()}
        }
        
    def get_summary(self) -> Dict:
        """Get summary of current rules configuration"""
        enabled_count = len(self.get_enabled_rules())
        total_count = len(self.rules)
        
        by_severity = {}
        for severity in AlertSeverity:
            count = len(self.get_rules_by_severity(severity))
            by_severity[severity.value] = count
            
        by_type = {}
        for alert_type in AlertType:
            count = len(self.get_rules_by_type(alert_type))
            by_type[alert_type.value] = count
            
        return {
            "total_rules": total_count,
            "enabled_rules": enabled_count,
            "disabled_rules": total_count - enabled_count,
            "global_enabled": self.is_alerts_enabled(),
            "quiet_hours_active": self.is_quiet_hours(),
            "by_severity": by_severity,
            "by_type": by_type,
            "notification_cooldown": self.get_notification_cooldown(),
            "max_alerts_per_hour": self.get_max_alerts_per_hour()
        }

# Example usage
if __name__ == "__main__":
    # Test with default rules
    rules = AlertRules()
    
    print("Default rules summary:")
    summary = rules.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
        
    print("\nTesting price change thresholds:")
    for change in [1.5, 3.0, 6.0, 12.0]:
        rule = rules.get_threshold_for_change(change)
        if rule:
            print(f"  {change}% change -> {rule.name} ({rule.severity.value})")
        else:
            print(f"  {change}% change -> No rule triggered")
            
    print("\nTesting volatility thresholds:")
    for volatility in [2.0, 4.0, 6.0]:
        rule = rules.get_threshold_for_volatility(volatility)
        if rule:
            print(f"  {volatility}% volatility -> {rule.name} ({rule.severity.value})")
        else:
            print(f"  {volatility}% volatility -> No rule triggered")
            
    # Test custom configuration
    custom_config = {
        "global_settings": {
            "enabled": True,
            "notification_cooldown": 600,  # 10 minutes
            "quiet_hours": {
                "enabled": True,
                "start": "23:00",
                "end": "07:00"
            }
        },
        "rules": {
            "custom_major_change": {
                "alert_type": "price_change",
                "severity": "high",
                "threshold": 3.0,
                "enabled": True,
                "description": "Custom 3% change alert"
            }
        }
    }
    
    print("\nTesting custom configuration:")
    custom_rules = AlertRules(custom_config)
    custom_summary = custom_rules.get_summary()
    for key, value in custom_summary.items():
        print(f"  {key}: {value}")