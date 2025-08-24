#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金价格爬虫模块
为TrendRadar系统提供备用黄金价格数据源
"""

# 核心爬虫组件
from .web_scraper import (
    WebScrapingManager,
    AntiDetectionManager
)

# 解析器组件
try:
    from .parsers import (
        BaseParser,
        SGEParser,
        CngoldParser,
        SinaParser,
        GoldPriceData
    )
except ImportError:
    # 兼容性处理
    BaseParser = None
    SGEParser = None
    CngoldParser = None
    SinaParser = None
    GoldPriceData = None

# 配置管理
from .config_manager import (
    GoldScraperConfig,
    get_gold_scraper_config,
    reload_gold_scraper_config
)

# 错误处理
from .error_handler import (
    GoldScraperError,
    NetworkError,
    ParserError,
    DataValidationError,
    ConfigError,
    TimeoutError,
    BrowserError,
    get_gold_scraper_error_handler,
    handle_gold_scraper_error
)

# 性能监控
from .performance_monitor import (
    PerformanceMetric,
    GoldScraperPerformanceMonitor,
    get_gold_scraper_performance_monitor,
    record_gold_scraper_metric,
    GoldScraperTimer
)

__version__ = "1.0.0"
__author__ = "TrendRadar Team"

# 主要导出
__all__ = [
    # 核心组件
    'WebScrapingManager',
    'AntiDetectionManager',
    
    # 解析器
    'BaseParser',
    'SGEParser',
    'CngoldParser', 
    'SinaParser',
    'GoldPriceData',
    
    # 配置管理
    'GoldScraperConfig',
    'get_gold_scraper_config',
    'reload_gold_scraper_config',
    
    # 错误处理
    'GoldScraperError',
    'NetworkError',
    'ParserError',
    'DataValidationError',
    'ConfigError',
    'TimeoutError',
    'BrowserError',
    'get_gold_scraper_error_handler',
    'handle_gold_scraper_error',
    
    # 性能监控
    'PerformanceMetric',
    'GoldScraperPerformanceMonitor',
    'get_gold_scraper_performance_monitor',
    'record_gold_scraper_metric',
    'GoldScraperTimer'
]


def initialize_gold_scraper(config_path=None):
    """
    初始化黄金爬虫系统
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        初始化是否成功
    """
    try:
        # 加载配置
        config = get_gold_scraper_config(config_path)
        
        # 设置日志
        config.setup_logging()
        
        # 验证配置
        if not config.validate_config():
            return False
        
        # 初始化错误处理器
        error_handler = get_gold_scraper_error_handler()
        
        # 初始化性能监控器
        performance_monitor = get_gold_scraper_performance_monitor()
        
        print("黄金爬虫系统初始化成功")
        return True
        
    except Exception as e:
        print(f"黄金爬虫系统初始化失败: {e}")
        return False


def get_system_status():
    """
    获取系统状态
    
    Returns:
        系统状态信息
    """
    try:
        config = get_gold_scraper_config()
        error_handler = get_gold_scraper_error_handler()
        performance_monitor = get_gold_scraper_performance_monitor()
        
        return {
            "config_loaded": True,
            "enabled": config.is_enabled(),
            "fallback_mode": config.is_fallback_mode(),
            "websites_count": len(config.get_websites_config()),
            "error_stats": error_handler.get_error_stats(),
            "performance_stats": performance_monitor.get_statistics()
        }
        
    except Exception as e:
        return {
            "config_loaded": False,
            "error": str(e)
        }