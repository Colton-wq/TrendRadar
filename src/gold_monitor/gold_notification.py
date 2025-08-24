"""
Gold Monitor Notification Adapter

This module provides notification functionality for gold price monitoring,
integrating with TrendRadar's existing notification system.
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .price_analyzer import PriceAlert, PriceTrend
from .gold_price_collector import GoldPriceData

@dataclass
class NotificationConfig:
    """Notification configuration"""
    feishu_url: str = ""
    dingtalk_url: str = ""
    wework_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    message_batch_size: int = 4000
    batch_send_interval: int = 1
    enabled: bool = True

class GoldNotificationFormatter:
    """Formats gold price data for different notification platforms"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def format_price_alert(self, alert: PriceAlert) -> Dict[str, str]:
        """Format a single price alert for notifications"""
        severity_emoji = {
            "low": "🟡",
            "medium": "🟠", 
            "high": "🔴",
            "critical": "🚨"
        }
        
        emoji = severity_emoji.get(alert.severity, "⚠️")
        direction = "📈" if alert.change_percent > 0 else "📉"
        
        # Basic message format
        basic_message = (
            f"{emoji} **黄金价格预警**\n"
            f"{direction} {alert.symbol}: ${alert.current_price:.2f}\n"
            f"变动: {alert.change_percent:+.2f}%\n"
            f"时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Rich message format (for platforms supporting markdown)
        rich_message = (
            f"{emoji} **黄金价格{alert.severity.upper()}预警**\n\n"
            f"**品种**: {alert.symbol}\n"
            f"**当前价格**: ${alert.current_price:.2f}\n"
            f"**价格变动**: {alert.change_percent:+.2f}% {direction}\n"
            f"**前期价格**: ${alert.previous_price:.2f}\n"
            f"**预警级别**: {alert.severity.upper()}\n"
            f"**时间**: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"💡 {alert.message}"
        )
        
        return {
            "basic": basic_message,
            "rich": rich_message,
            "title": f"{alert.symbol}价格{alert.severity}预警"
        }
    
    def format_price_summary(self, summaries: Dict[str, Dict]) -> Dict[str, str]:
        """Format price summaries for notifications"""
        if not summaries:
            return {"basic": "暂无黄金价格数据", "rich": "暂无黄金价格数据"}
        
        basic_lines = ["📊 **黄金价格监控报告**"]
        rich_lines = ["📊 **黄金价格监控报告**\n"]
        
        for symbol, summary in summaries.items():
            current_price = summary.get('current_price', 0)
            currency = summary.get('currency', 'USD')
            
            # Get latest change
            changes = summary.get('changes', {})
            latest_change = 0
            if '1h' in changes:
                latest_change = changes['1h']['change_percent']
            
            direction = "📈" if latest_change > 0 else "📉" if latest_change < 0 else "➡️"
            
            basic_line = f"{direction} {symbol}: ${current_price:.2f} ({latest_change:+.2f}%)"
            basic_lines.append(basic_line)
            
            # Rich format with more details
            rich_lines.append(f"### {symbol}")
            rich_lines.append(f"**当前价格**: ${current_price:.2f} {currency}")
            rich_lines.append(f"**1小时变动**: {latest_change:+.2f}% {direction}")
            
            # Add trend information if available
            trend = summary.get('trend')
            if trend:
                trend_emoji = {
                    'rising': '📈',
                    'falling': '📉', 
                    'stable': '➡️',
                    'volatile': '🌊'
                }.get(trend['direction'], '❓')
                rich_lines.append(f"**趋势**: {trend['direction']} {trend_emoji}")
                rich_lines.append(f"**波动率**: {trend['volatility']:.2f}%")
            
            # Add alerts if any
            alerts = summary.get('alerts', [])
            if alerts:
                rich_lines.append(f"**活跃预警**: {len(alerts)}个")
            
            rich_lines.append("")  # Empty line for spacing
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        basic_lines.append(f"\n⏰ 更新时间: {timestamp}")
        rich_lines.append(f"⏰ **更新时间**: {timestamp}")
        
        return {
            "basic": "\n".join(basic_lines),
            "rich": "\n".join(rich_lines),
            "title": "黄金价格监控报告"
        }
    
    def format_trend_analysis(self, symbol: str, trend: PriceTrend) -> Dict[str, str]:
        """Format trend analysis for notifications"""
        trend_emoji = {
            'rising': '📈',
            'falling': '📉',
            'stable': '➡️', 
            'volatile': '🌊'
        }.get(trend.direction.value, '❓')
        
        strength_desc = "强" if trend.strength > 0.7 else "中" if trend.strength > 0.3 else "弱"
        
        basic_message = (
            f"{trend_emoji} **{symbol}趋势分析**\n"
            f"方向: {trend.direction.value} ({strength_desc})\n"
            f"波动率: {trend.volatility:.2f}%\n"
            f"持续时间: {trend.duration_hours:.1f}小时"
        )
        
        rich_message = (
            f"{trend_emoji} **{symbol}趋势分析报告**\n\n"
            f"**趋势方向**: {trend.direction.value}\n"
            f"**趋势强度**: {trend.strength:.2f} ({strength_desc})\n"
            f"**平均变动**: {trend.average_change_percent:+.2f}%\n"
            f"**波动率**: {trend.volatility:.2f}%\n"
            f"**持续时间**: {trend.duration_hours:.1f}小时\n\n"
            f"💡 趋势分析基于最近{trend.duration_hours:.0f}小时的价格数据"
        )
        
        return {
            "basic": basic_message,
            "rich": rich_message,
            "title": f"{symbol}趋势分析"
        }

class GoldNotificationSender:
    """Sends gold price notifications to various platforms"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.formatter = GoldNotificationFormatter()
        
    def _send_feishu(self, message: str, title: str = "") -> bool:
        """Send message to Feishu"""
        if not self.config.feishu_url:
            return False
            
        try:
            payload = {
                "msg_type": "text",
                "content": {
                    "text": message
                }
            }
            
            response = requests.post(
                self.config.feishu_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                self.logger.info("Feishu notification sent successfully")
                return True
            else:
                self.logger.error(f"Feishu notification failed: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send Feishu notification: {e}")
            return False
    
    def _send_dingtalk(self, message: str, title: str = "") -> bool:
        """Send message to DingTalk"""
        if not self.config.dingtalk_url:
            return False
            
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            
            response = requests.post(
                self.config.dingtalk_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("errcode") == 0:
                self.logger.info("DingTalk notification sent successfully")
                return True
            else:
                self.logger.error(f"DingTalk notification failed: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send DingTalk notification: {e}")
            return False
    
    def _send_wework(self, message: str, title: str = "") -> bool:
        """Send message to WeWork (Enterprise WeChat)"""
        if not self.config.wework_url:
            return False
            
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            
            response = requests.post(
                self.config.wework_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("errcode") == 0:
                self.logger.info("WeWork notification sent successfully")
                return True
            else:
                self.logger.error(f"WeWork notification failed: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send WeWork notification: {e}")
            return False
    
    def _send_telegram(self, message: str, title: str = "") -> bool:
        """Send message to Telegram"""
        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
            
            payload = {
                "chat_id": self.config.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                self.logger.info("Telegram notification sent successfully")
                return True
            else:
                self.logger.error(f"Telegram notification failed: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def send_alert(self, alert: PriceAlert) -> Dict[str, bool]:
        """Send price alert to all configured platforms"""
        if not self.config.enabled:
            self.logger.info("Notifications disabled, skipping alert")
            return {}
        
        formatted = self.formatter.format_price_alert(alert)
        results = {}
        
        # Send to all platforms
        results['feishu'] = self._send_feishu(formatted['rich'], formatted['title'])
        results['dingtalk'] = self._send_dingtalk(formatted['basic'], formatted['title'])
        results['wework'] = self._send_wework(formatted['basic'], formatted['title'])
        results['telegram'] = self._send_telegram(formatted['rich'], formatted['title'])
        
        # Log summary
        successful = sum(1 for success in results.values() if success)
        total = len([url for url in [self.config.feishu_url, self.config.dingtalk_url, 
                                   self.config.wework_url, self.config.telegram_bot_token] if url])
        
        self.logger.info(f"Alert sent to {successful}/{total} platforms successfully")
        return results
    
    def send_summary(self, summaries: Dict[str, Dict]) -> Dict[str, bool]:
        """Send price summary to all configured platforms"""
        if not self.config.enabled:
            self.logger.info("Notifications disabled, skipping summary")
            return {}
        
        formatted = self.formatter.format_price_summary(summaries)
        results = {}
        
        # Send to all platforms
        results['feishu'] = self._send_feishu(formatted['rich'], formatted['title'])
        results['dingtalk'] = self._send_dingtalk(formatted['basic'], formatted['title'])
        results['wework'] = self._send_wework(formatted['basic'], formatted['title'])
        results['telegram'] = self._send_telegram(formatted['rich'], formatted['title'])
        
        # Log summary
        successful = sum(1 for success in results.values() if success)
        total = len([url for url in [self.config.feishu_url, self.config.dingtalk_url,
                                   self.config.wework_url, self.config.telegram_bot_token] if url])
        
        self.logger.info(f"Summary sent to {successful}/{total} platforms successfully")
        return results
    
    def send_trend_analysis(self, symbol: str, trend: PriceTrend) -> Dict[str, bool]:
        """Send trend analysis to all configured platforms"""
        if not self.config.enabled:
            self.logger.info("Notifications disabled, skipping trend analysis")
            return {}
        
        formatted = self.formatter.format_trend_analysis(symbol, trend)
        results = {}
        
        # Send to all platforms
        results['feishu'] = self._send_feishu(formatted['rich'], formatted['title'])
        results['dingtalk'] = self._send_dingtalk(formatted['basic'], formatted['title'])
        results['wework'] = self._send_wework(formatted['basic'], formatted['title'])
        results['telegram'] = self._send_telegram(formatted['rich'], formatted['title'])
        
        # Log summary
        successful = sum(1 for success in results.values() if success)
        total = len([url for url in [self.config.feishu_url, self.config.dingtalk_url,
                                   self.config.wework_url, self.config.telegram_bot_token] if url])
        
        self.logger.info(f"Trend analysis sent to {successful}/{total} platforms successfully")
        return results
    
    def send_batch_alerts(self, alerts: List[PriceAlert]) -> Dict[str, int]:
        """Send multiple alerts in batches"""
        if not alerts or not self.config.enabled:
            return {}
        
        results = {'feishu': 0, 'dingtalk': 0, 'wework': 0, 'telegram': 0}
        
        for alert in alerts:
            alert_results = self.send_alert(alert)
            for platform, success in alert_results.items():
                if success:
                    results[platform] += 1
        
        self.logger.info(f"Batch alerts sent: {results}")
        return results
    
    def test_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all configured platforms"""
        test_message = "🧪 TrendRadar黄金监控系统连接测试"
        test_title = "连接测试"
        
        results = {}
        results['feishu'] = self._send_feishu(test_message, test_title)
        results['dingtalk'] = self._send_dingtalk(test_message, test_title)
        results['wework'] = self._send_wework(test_message, test_title)
        results['telegram'] = self._send_telegram(test_message, test_title)
        
        return results

class GoldNotificationManager:
    """Main notification manager for gold price monitoring"""
    
    def __init__(self, config: Dict):
        self.config = NotificationConfig(
            feishu_url=config.get('feishu_url', ''),
            dingtalk_url=config.get('dingtalk_url', ''),
            wework_url=config.get('wework_url', ''),
            telegram_bot_token=config.get('telegram_bot_token', ''),
            telegram_chat_id=config.get('telegram_chat_id', ''),
            message_batch_size=config.get('message_batch_size', 4000),
            batch_send_interval=config.get('batch_send_interval', 1),
            enabled=config.get('enabled', True)
        )
        
        self.sender = GoldNotificationSender(self.config)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def notify_alert(self, alert: PriceAlert) -> bool:
        """Send a single price alert notification"""
        try:
            results = self.sender.send_alert(alert)
            return any(results.values())
        except Exception as e:
            self.logger.error(f"Failed to send alert notification: {e}")
            return False
    
    def notify_summary(self, summaries: Dict[str, Dict]) -> bool:
        """Send price summary notification"""
        try:
            results = self.sender.send_summary(summaries)
            return any(results.values())
        except Exception as e:
            self.logger.error(f"Failed to send summary notification: {e}")
            return False
    
    def notify_trend(self, symbol: str, trend: PriceTrend) -> bool:
        """Send trend analysis notification"""
        try:
            results = self.sender.send_trend_analysis(symbol, trend)
            return any(results.values())
        except Exception as e:
            self.logger.error(f"Failed to send trend notification: {e}")
            return False
    
    def notify_batch_alerts(self, alerts: List[PriceAlert]) -> int:
        """Send multiple alerts and return success count"""
        try:
            results = self.sender.send_batch_alerts(alerts)
            return sum(results.values())
        except Exception as e:
            self.logger.error(f"Failed to send batch alerts: {e}")
            return 0
    
    def test_notifications(self) -> Dict[str, bool]:
        """Test all notification channels"""
        return self.sender.test_connectivity()

# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example configuration
    config = {
        'feishu_url': '',  # Add your Feishu webhook URL
        'dingtalk_url': '',  # Add your DingTalk webhook URL
        'wework_url': '',  # Add your WeWork webhook URL
        'telegram_bot_token': '',  # Add your Telegram bot token
        'telegram_chat_id': '',  # Add your Telegram chat ID
        'enabled': True
    }
    
    manager = GoldNotificationManager(config)
    
    # Test connectivity
    print("Testing notification connectivity...")
    test_results = manager.test_notifications()
    for platform, success in test_results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {platform}: {status}")
    
    # Example alert
    from datetime import datetime
    from .price_analyzer import PriceAlert
    
    example_alert = PriceAlert(
        symbol="XAUUSD",
        alert_type="major_change",
        message="Gold price increased significantly",
        current_price=2050.0,
        previous_price=1950.0,
        change_percent=5.13,
        timestamp=datetime.now(),
        severity="high"
    )
    
    # Send example alert
    print("\nSending example alert...")
    success = manager.notify_alert(example_alert)
    print(f"Alert sent: {'✅ Success' if success else '❌ Failed'}")