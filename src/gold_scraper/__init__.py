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

# 降级管理
from .fallback_manager import (
    FallbackManager,
    DataSourceWrapper,
    DataSourceType,
    DataSourceStatus,
    get_fallback_manager
)

# 数据验证
from .data_validator import (
    DataValidator,
    ValidationResult,
    get_data_validator
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
    'GoldScraperTimer',
    
    # 降级管理
    'FallbackManager',
    'DataSourceWrapper',
    'DataSourceType',
    'DataSourceStatus',
    'get_fallback_manager',
    
    # 数据验证
    'DataValidator',
    'ValidationResult',
    'get_data_validator'
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
        
        # 初始化降级管理器
        fallback_manager = get_fallback_manager()
        
        # 初始化数据验证器
        data_validator = get_data_validator()
        
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
        fallback_manager = get_fallback_manager()
        
        return {
            "config_loaded": True,
            "enabled": config.is_enabled(),
            "fallback_mode": config.is_fallback_mode(),
            "websites_count": len(config.get_websites_config()),
            "error_stats": error_handler.get_error_stats(),
            "performance_stats": performance_monitor.get_statistics(),
            "fallback_status": fallback_manager.get_status_summary()
        }
        
    except Exception as e:
        return {
            "config_loaded": False,
            "error": str(e)
        }


async def fetch_gold_data_with_fallback(api_fetcher=None, scraper_fetcher=None):
    """
    使用降级策略获取黄金数据的便捷函数
    
    Args:
        api_fetcher: API数据获取函数
        scraper_fetcher: 爬虫数据获取函数
        
    Returns:
        Tuple[数据, 数据源, 是否使用了降级]
    """
    try:
        fallback_manager = get_fallback_manager()
        data_wrapper = DataSourceWrapper(fallback_manager)
        
        return await data_wrapper.fetch_data_with_fallback(api_fetcher, scraper_fetcher)
        
    except Exception as e:
        print(f"降级数据获取失败: {e}")
        return None, "error", False