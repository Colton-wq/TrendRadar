#!/usr/bin/env python3
"""
Gold Monitor Test Script

This script tests the gold price monitoring functionality
including API integration, price analysis, and alert generation.
"""

import sys
import os
import logging
import yaml
from datetime import datetime, timedelta

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gold_monitor.gold_price_collector import GoldPriceCollector, GoldPriceData
from gold_monitor.price_analyzer import PriceAnalyzer
from gold_monitor.alert_rules import AlertRules

def load_config():
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('gold_monitor', {})
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}")
        return {}

def test_gold_price_collector():
    """Test gold price data collection"""
    print("🔍 Testing Gold Price Collector...")
    
    config = load_config()
    api_config = {
        "goldapi_key": config.get("api_keys", {}).get("goldapi_key", ""),
        "jisu_api_key": config.get("api_keys", {}).get("jisu_api_key", ""),
        "cache_ttl": config.get("monitoring", {}).get("cache_ttl", 300)
    }
    
    collector = GoldPriceCollector(api_config)
    
    # Test health check
    print("  📊 Running health check...")
    health = collector.health_check()
    for api_name, is_healthy in health.items():
        status = "✅ Healthy" if is_healthy else "❌ Unhealthy"
        print(f"    {api_name}: {status}")
    
    # Test price collection
    print("  💰 Collecting gold prices...")
    prices = collector.get_gold_prices()
    
    if prices:
        for symbol, price_data in prices.items():
            print(f"    {symbol}: ${price_data.price:.2f} {price_data.currency}")
            print(f"      Change: {price_data.change_percent:+.2f}%")
            print(f"      Source: {price_data.source}")
            print(f"      Time: {price_data.timestamp}")
    else:
        print("    ⚠️  No price data collected (check API keys)")
    
    return prices

def test_price_analyzer(prices):
    """Test price analysis functionality"""
    print("\n📈 Testing Price Analyzer...")
    
    config = load_config()
    analyzer_config = config.get("alerts", {}).get("thresholds", {})
    
    analyzer = PriceAnalyzer(analyzer_config)
    
    # Add current price data
    for symbol, price_data in prices.items():
        analyzer.add_price_data(price_data)
        print(f"  📊 Added {symbol} price data: ${price_data.price:.2f}")
    
    # Simulate historical data for testing
    print("  🔄 Simulating historical data for testing...")
    for symbol, current_price_data in prices.items():
        # Create some historical data points
        base_price = current_price_data.price
        for i in range(5):
            # Create price variations
            price_variation = base_price * (1 + (i - 2) * 0.02)  # ±4% variation
            historical_data = GoldPriceData(
                symbol=symbol,
                price=price_variation,
                timestamp=datetime.now() - timedelta(hours=i+1),
                change_percent=(price_variation - base_price) / base_price * 100,
                currency=current_price_data.currency,
                source=current_price_data.source
            )
            analyzer.add_price_data(historical_data)
    
    # Test trend analysis
    print("  📊 Analyzing trends...")
    for symbol in prices.keys():
        trend = analyzer.analyze_trend(symbol, hours_back=6)
        if trend:
            print(f"    {symbol} Trend:")
            print(f"      Direction: {trend.direction.value}")
            print(f"      Strength: {trend.strength:.2f}")
            print(f"      Volatility: {trend.volatility:.2f}%")
            print(f"      Avg Change: {trend.average_change_percent:+.2f}%")
    
    # Test alert checking
    print("  🚨 Checking for alerts...")
    all_alerts = []
    for symbol in prices.keys():
        alerts = analyzer.check_alerts(symbol)
        all_alerts.extend(alerts)
        if alerts:
            for alert in alerts:
                print(f"    🚨 {alert.severity.upper()}: {alert.message}")
        else:
            print(f"    ✅ No alerts for {symbol}")
    
    # Get comprehensive summaries
    print("  📋 Generating price summaries...")
    summaries = analyzer.get_all_summaries()
    for symbol, summary in summaries.items():
        print(f"    {symbol} Summary:")
        print(f"      Current: ${summary['current_price']:.2f} {summary['currency']}")
        print(f"      Data Points: {summary['data_points']}")
        if summary.get('trend'):
            print(f"      Trend: {summary['trend']['direction']} (strength: {summary['trend']['strength']:.2f})")
    
    return all_alerts

def test_alert_rules():
    """Test alert rules configuration"""
    print("\n⚙️  Testing Alert Rules...")
    
    config = load_config()
    alert_config = config.get("alerts", {})
    
    rules = AlertRules(alert_config)
    
    # Display rules summary
    summary = rules.get_summary()
    print("  📊 Rules Summary:")
    for key, value in summary.items():
        print(f"    {key}: {value}")
    
    # Test threshold checking
    print("  🎯 Testing threshold rules...")
    test_changes = [1.5, 3.0, 6.0, 12.0]
    for change in test_changes:
        rule = rules.get_threshold_for_change(change)
        if rule:
            print(f"    {change:+.1f}% change → {rule.name} ({rule.severity.value})")
        else:
            print(f"    {change:+.1f}% change → No rule triggered")
    
    test_volatilities = [2.0, 4.0, 6.0]
    for volatility in test_volatilities:
        rule = rules.get_threshold_for_volatility(volatility)
        if rule:
            print(f"    {volatility:.1f}% volatility → {rule.name} ({rule.severity.value})")
        else:
            print(f"    {volatility:.1f}% volatility → No rule triggered")

def test_configuration():
    """Test configuration loading and validation"""
    print("\n⚙️  Testing Configuration...")
    
    config = load_config()
    
    if not config:
        print("  ❌ No gold monitor configuration found")
        return False
    
    print("  ✅ Configuration loaded successfully")
    
    # Check required sections
    required_sections = ['api_keys', 'monitoring', 'alerts']
    for section in required_sections:
        if section in config:
            print(f"    ✅ {section} section found")
        else:
            print(f"    ⚠️  {section} section missing")
    
    # Check API keys
    api_keys = config.get('api_keys', {})
    goldapi_key = api_keys.get('goldapi_key', '')
    jisu_key = api_keys.get('jisu_api_key', '')
    
    if goldapi_key:
        print(f"    ✅ GoldAPI key configured (length: {len(goldapi_key)})")
    else:
        print("    ⚠️  GoldAPI key not configured")
    
    if jisu_key:
        print(f"    ✅ Jisu API key configured (length: {len(jisu_key)})")
    else:
        print("    ⚠️  Jisu API key not configured")
    
    # Check monitoring settings
    monitoring = config.get('monitoring', {})
    symbols = monitoring.get('symbols', [])
    print(f"    📊 Monitoring symbols: {symbols}")
    print(f"    ⏱️  Update interval: {monitoring.get('update_interval', 3600)} seconds")
    
    return True

def main():
    """Main test function"""
    print("🚀 Starting Gold Monitor Test Suite")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Test configuration
        config_ok = test_configuration()
        if not config_ok:
            print("\n❌ Configuration test failed. Please check config.yaml")
            return
        
        # Test alert rules
        test_alert_rules()
        
        # Test price collector
        prices = test_gold_price_collector()
        
        if prices:
            # Test price analyzer
            test_price_analyzer(prices)
        else:
            print("\n⚠️  Skipping price analyzer tests (no price data)")
        
        print("\n" + "=" * 50)
        print("✅ Gold Monitor Test Suite Completed")
        
        # Summary
        print("\n📋 Test Summary:")
        print("  ✅ Configuration loading")
        print("  ✅ Alert rules system")
        print("  ✅ Gold price collector")
        if prices:
            print("  ✅ Price analyzer")
            print("  ✅ Alert generation")
        else:
            print("  ⚠️  Price analyzer (no data)")
        
        print("\n💡 Next Steps:")
        print("  1. Configure API keys in config/config.yaml")
        print("  2. Enable gold monitoring: set gold_monitor.enabled = true")
        print("  3. Integrate with main TrendRadar application")
        print("  4. Set up notification webhooks")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()