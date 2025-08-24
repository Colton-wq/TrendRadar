#!/usr/bin/env python3
"""
Gold Monitor Integration for TrendRadar

This script integrates gold price monitoring functionality into the main TrendRadar program.
It can be run independently or as part of the main TrendRadar workflow.
"""

import os
import sys
import yaml
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('gold_monitor.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def load_config(config_path: str = 'config/config.yaml') -> Optional[Dict[str, Any]]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        return None
    except yaml.YAMLError as e:
        logging.error(f"Error parsing configuration file: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}")
        return None

def update_config_with_env(config: Dict[str, Any]) -> Dict[str, Any]:
    """Update configuration with environment variables"""
    if not config:
        return config
    
    # Update gold monitor configuration
    gold_config = config.setdefault('gold_monitor', {})
    
    # Update API keys from environment variables
    api_keys = gold_config.setdefault('api_keys', {})
    
    if os.getenv('GOLDAPI_KEY'):
        api_keys['goldapi_key'] = os.getenv('GOLDAPI_KEY')
        logging.info("✅ GoldAPI密钥已从环境变量加载")
    
    if os.getenv('JISU_API_KEY'):
        api_keys['jisu_api_key'] = os.getenv('JISU_API_KEY')
        logging.info("✅ 极速数据API密钥已从环境变量加载")
    
    # Update notification webhooks from environment variables
    notification_config = config.setdefault('notification', {})
    webhooks = notification_config.setdefault('webhooks', {})
    
    env_webhooks = {
        'feishu_url': 'FEISHU_WEBHOOK_URL',
        'dingtalk_url': 'DINGTALK_WEBHOOK_URL',
        'wework_url': 'WEWORK_WEBHOOK_URL',
        'telegram_bot_token': 'TELEGRAM_BOT_TOKEN',
        'telegram_chat_id': 'TELEGRAM_CHAT_ID'
    }
    
    for config_key, env_key in env_webhooks.items():
        if os.getenv(env_key):
            webhooks[config_key] = os.getenv(env_key)
    
    # Enable gold monitor if running in gold monitor mode
    if os.getenv('GOLD_MONITOR_MODE') == 'true':
        gold_config['enabled'] = True
        logging.info("🔧 黄金监控已通过环境变量启用")
    
    return config

def validate_gold_monitor_config(config: Dict[str, Any]) -> bool:
    """Validate gold monitor configuration"""
    try:
        from gold_monitor import validate_gold_monitor_config
        
        gold_config = config.get('gold_monitor', {})
        is_valid, errors, warnings = validate_gold_monitor_config(gold_config)
        
        if errors:
            logging.error("❌ 黄金监控配置验证失败:")
            for error in errors:
                logging.error(f"  - {error}")
            return False
        
        if warnings:
            logging.warning("⚠️  黄金监控配置警告:")
            for warning in warnings:
                logging.warning(f"  - {warning}")
        
        logging.info("✅ 黄金监控配置验证通过")
        return True
        
    except ImportError:
        logging.error("❌ 无法导入黄金监控配置验证模块")
        return False
    except Exception as e:
        logging.error(f"❌ 配置验证失败: {e}")
        return False

def run_gold_monitor(config: Dict[str, Any]) -> bool:
    """Run gold price monitoring"""
    logger = logging.getLogger(__name__)
    
    try:
        # Import gold monitor modules
        from gold_monitor import (
            GoldPriceCollector,
            PriceAnalyzer,
            GoldNotificationManager,
            GoldReportGenerator,
            GoldReportData
        )
        
        gold_config = config.get('gold_monitor', {})
        
        # Check if gold monitoring is enabled
        if not gold_config.get('enabled', False):
            logger.info("⏭️  黄金监控功能未启用，跳过执行")
            return True
        
        logger.info("🚀 启动黄金价格监控...")
        
        # Initialize components
        logger.info("📊 初始化黄金价格采集器...")
        collector_config = {
            'goldapi_key': gold_config.get('api_keys', {}).get('goldapi_key', ''),
            'jisu_api_key': gold_config.get('api_keys', {}).get('jisu_api_key', ''),
            'cache_ttl': gold_config.get('monitoring', {}).get('cache_ttl', 300)
        }
        collector = GoldPriceCollector(collector_config)
        
        logger.info("📈 初始化价格分析器...")
        analyzer_config = gold_config.get('alerts', {}).get('thresholds', {})
        analyzer = PriceAnalyzer(analyzer_config)
        
        logger.info("📱 初始化通知管理器...")
        notification_config = config.get('notification', {}).get('webhooks', {})
        notification_manager = GoldNotificationManager(notification_config)
        
        logger.info("📋 初始化报告生成器...")
        report_generator = GoldReportGenerator()
        
        # Test API connectivity
        logger.info("🔗 测试API连接...")
        health = collector.health_check()
        healthy_apis = sum(1 for status in health.values() if status)
        total_apis = len(health)
        logger.info(f"API健康状态: {healthy_apis}/{total_apis} 正常")
        
        if healthy_apis == 0:
            logger.warning("⚠️  所有API连接失败，请检查API密钥配置")
            return True  # Don't fail the entire process
        
        # Collect price data
        logger.info("💰 采集黄金价格数据...")
        symbols = gold_config.get('monitoring', {}).get('symbols', ['XAUUSD', 'AU9999'])
        prices = {}
        
        for symbol in symbols:
            try:
                price_data = collector.get_price(symbol)
                if price_data:
                    prices[symbol] = price_data
                    logger.info(f"✅ {symbol}: ${price_data.price:.2f} {price_data.currency}")
                else:
                    logger.warning(f"⚠️  无法获取 {symbol} 价格数据")
            except Exception as e:
                logger.error(f"❌ 获取 {symbol} 价格失败: {e}")
        
        if not prices:
            logger.warning("⚠️  未获取到任何价格数据")
            return True
        
        logger.info(f"✅ 成功获取 {len(prices)} 个品种的价格数据")
        
        # Analyze prices and generate alerts
        alerts = []
        trends = {}
        summaries = {}
        
        for symbol, price_data in prices.items():
            logger.info(f"📊 分析 {symbol} 价格趋势...")
            
            # Add price data to analyzer
            analyzer.add_price_data(price_data)
            
            # Check for alerts
            symbol_alerts = analyzer.check_alerts(symbol)
            alerts.extend(symbol_alerts)
            
            # Get trend analysis
            trend = analyzer.get_trend(symbol)
            if trend:
                trends[symbol] = trend
            
            # Get price summary
            summary = analyzer.get_summary(symbol)
            if summary:
                summaries[symbol] = summary
        
        # Process alerts
        if alerts:
            logger.info(f"🚨 发现 {len(alerts)} 个价格预警")
            for alert in alerts:
                logger.info(f"  - {alert.severity.upper()}: {alert.symbol} - {alert.message}")
            
            # Send alert notifications
            if gold_config.get('alerts', {}).get('enabled', True):
                try:
                    success_count = notification_manager.notify_batch_alerts(alerts)
                    logger.info(f"📱 预警通知发送成功: {success_count}/{len(alerts)} 条")
                except Exception as e:
                    logger.error(f"❌ 预警通知发送失败: {e}")
        else:
            logger.info("✅ 当前无价格预警")
        
        # Generate reports
        if gold_config.get('reporting', {}).get('include_in_main_report', True):
            logger.info("📊 生成黄金监控报告...")
            try:
                report_data = GoldReportData(
                    summaries=summaries,
                    alerts=alerts,
                    trends=trends,
                    timestamp=datetime.now()
                )
                
                # Generate HTML section for integration
                html_section = report_generator.generate_gold_section_html(report_data)
                
                # Save HTML section for main report integration
                with open('gold_monitor_section.html', 'w', encoding='utf-8') as f:
                    f.write(html_section)
                
                logger.info("✅ 黄金监控报告生成完成")
                
            except Exception as e:
                logger.error(f"❌ 报告生成失败: {e}")
        
        # Send summary notifications
        if summaries and gold_config.get('notifications', {}).get('use_main_channels', True):
            logger.info("📋 发送价格摘要通知...")
            try:
                summary_success = notification_manager.notify_summary(summaries)
                if summary_success:
                    logger.info("✅ 价格摘要通知发送成功")
                else:
                    logger.warning("⚠️  价格摘要通知发送失败")
            except Exception as e:
                logger.error(f"❌ 摘要通知发送失败: {e}")
        
        logger.info("🎉 黄金价格监控任务完成")
        return True
        
    except ImportError as e:
        logger.error(f"❌ 模块导入失败: {e}")
        logger.error("请确保黄金监控模块已正确安装")
        return False
    except Exception as e:
        logger.error(f"❌ 黄金监控执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def integrate_with_main_report():
    """Integrate gold monitor section with main TrendRadar report"""
    logger = logging.getLogger(__name__)
    
    try:
        # Check if main report exists
        main_report_path = 'index.html'
        gold_section_path = 'gold_monitor_section.html'
        
        if not os.path.exists(gold_section_path):
            logger.info("📄 未找到黄金监控报告段，跳过集成")
            return True
        
        if not os.path.exists(main_report_path):
            logger.info("📄 未找到主报告，创建独立黄金监控报告")
            
            # Create standalone gold monitor report
            with open(gold_section_path, 'r', encoding='utf-8') as f:
                gold_content = f.read()
            
            standalone_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrendRadar - 黄金价格监控报告</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            margin: 0; 
            padding: 16px; 
            background: #fafafa;
            color: #333;
            line-height: 1.5;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 16px rgba(0,0,0,0.06);
        }}
        .header {{
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            padding: 32px 24px;
            text-align: center;
        }}
        .content {{
            padding: 24px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>TrendRadar - 黄金价格监控报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="content">
            {gold_content}
        </div>
    </div>
</body>
</html>"""
            
            with open(main_report_path, 'w', encoding='utf-8') as f:
                f.write(standalone_html)
            
            logger.info("✅ 独立黄金监控报告创建完成")
            
        else:
            logger.info("📄 集成黄金监控段到主报告")
            
            # Read main report
            with open(main_report_path, 'r', encoding='utf-8') as f:
                main_content = f.read()
            
            # Read gold section
            with open(gold_section_path, 'r', encoding='utf-8') as f:
                gold_content = f.read()
            
            # Insert gold section before closing body tag
            if '</body>' in main_content:
                main_content = main_content.replace('</body>', f'{gold_content}\n</body>')
            else:
                # Append to end if no closing body tag found
                main_content += gold_content
            
            # Write updated main report
            with open(main_report_path, 'w', encoding='utf-8') as f:
                f.write(main_content)
            
            logger.info("✅ 黄金监控段已集成到主报告")
        
        # Clean up temporary file
        if os.path.exists(gold_section_path):
            os.remove(gold_section_path)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 报告集成失败: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='TrendRadar Gold Monitor Integration')
    parser.add_argument('--config', default='config/config.yaml', help='Configuration file path')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Log level')
    parser.add_argument('--gold-only', action='store_true', help='Run gold monitor only (skip main TrendRadar)')
    parser.add_argument('--validate-only', action='store_true', help='Only validate configuration')
    parser.add_argument('--health-check', action='store_true', help='Perform health check only')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    logger.info("🚀 TrendRadar Gold Monitor Integration 启动")
    logger.info(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Load configuration
        logger.info("📋 加载配置文件...")
        config = load_config(args.config)
        if not config:
            logger.error("❌ 配置加载失败")
            return 1
        
        # Update with environment variables
        config = update_config_with_env(config)
        
        # Health check mode
        if args.health_check:
            logger.info("🔍 执行健康检查...")
            try:
                from gold_monitor import health_check
                health_status = health_check()
                
                if health_status['status'] == 'healthy':
                    logger.info("✅ 黄金监控模块健康检查通过")
                    logger.info(f"📦 模块版本: {health_status['version']}")
                    return 0
                else:
                    logger.error(f"❌ 黄金监控模块健康检查失败: {health_status.get('error', 'Unknown error')}")
                    return 1
            except ImportError:
                logger.error("❌ 无法导入黄金监控模块")
                return 1
        
        # Validate configuration
        logger.info("🔍 验证配置...")
        if not validate_gold_monitor_config(config):
            logger.error("❌ 配置验证失败")
            if not args.validate_only:
                logger.info("⚠️  继续执行，但可能遇到问题")
            else:
                return 1
        
        if args.validate_only:
            logger.info("✅ 配置验证完成")
            return 0
        
        # Run gold monitor
        logger.info("💰 执行黄金价格监控...")
        gold_success = run_gold_monitor(config)
        
        if not gold_success:
            logger.error("❌ 黄金监控执行失败")
            return 1
        
        # Integrate with main report
        logger.info("📊 集成报告...")
        report_success = integrate_with_main_report()
        
        if not report_success:
            logger.warning("⚠️  报告集成失败，但黄金监控执行成功")
        
        logger.info("🎉 TrendRadar Gold Monitor Integration 完成")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⏹️  用户中断执行")
        return 130
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())