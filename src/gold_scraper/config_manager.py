#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金爬虫配置管理器
集成到TrendRadar现有配置系统
"""

import os
import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path


class GoldScraperConfig:
    """黄金爬虫配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 config/config.yaml
        """
        self.logger = logging.getLogger("GoldScraperConfig")
        
        # 确定配置文件路径
        if config_path:
            self.config_path = Path(config_path)
        else:
            # 尝试多个可能的路径
            possible_paths = [
                Path("config/config.yaml"),
                Path("../config/config.yaml"),
                Path("../../config/config.yaml"),
                Path(os.path.join(os.path.dirname(__file__), "../../config/config.yaml"))
            ]
            
            self.config_path = None
            for path in possible_paths:
                if path.exists():
                    self.config_path = path
                    break
            
            if not self.config_path:
                raise FileNotFoundError("无法找到配置文件 config.yaml")
        
        # 加载配置
        self._config = self._load_config()
        self._gold_config = self._config.get("gold_scraper", {})
        
        self.logger.info(f"配置加载成功: {self.config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载YAML配置文件
        
        Returns:
            配置字典
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict):
                raise ValueError("配置文件格式错误")
            
            return config
            
        except Exception as e:
            self.logger.error(f"配置文件加载失败: {e}")
            raise
    
    def is_enabled(self) -> bool:
        """检查黄金爬虫是否启用"""
        return self._gold_config.get("enable_gold_scraper", False)
    
    def is_fallback_mode(self) -> bool:
        """检查是否为备用模式"""
        return self._gold_config.get("fallback_mode", True)
    
    def get_execution_config(self) -> Dict[str, Any]:
        """获取执行配置"""
        default_config = {
            "max_concurrent_parsers": 2,
            "parser_timeout": 60,
            "retry_attempts": 2,
            "delay_between_parsers": [5, 10],
            "request_interval": 5000
        }
        
        execution_config = self._gold_config.get("execution", {})
        default_config.update(execution_config)
        
        return default_config
    
    def get_anti_detection_config(self) -> Dict[str, Any]:
        """获取反爬虫配置"""
        default_config = {
            "enable_user_agent_rotation": True,
            "enable_random_delays": True,
            "min_delay": 5,
            "max_delay": 10
        }
        
        anti_detection_config = self._gold_config.get("anti_detection", {})
        default_config.update(anti_detection_config)
        
        return default_config
    
    def get_validation_config(self) -> Dict[str, Any]:
        """获取数据验证配置"""
        default_config = {
            "price_range": [100.0, 10000.0],
            "change_range": [-1000.0, 1000.0],
            "enable_data_validation": True
        }
        
        validation_config = self._gold_config.get("validation", {})
        default_config.update(validation_config)
        
        return default_config
    
    def get_websites_config(self) -> List[Dict[str, Any]]:
        """获取网站配置列表"""
        default_websites = [
            {
                "name": "SGE",
                "url": "https://www.sge.com.cn/",
                "enabled": True,
                "priority": 1,
                "description": "上海黄金交易所",
                "target_contracts": ["Au99.99", "Au(T+D)", "mAu(T+D)", "Au99.95", "Au100g"]
            },
            {
                "name": "Cngold",
                "url": "https://gold.cngold.org/",
                "enabled": True,
                "priority": 2,
                "description": "金投网",
                "target_products": ["黄金T+D", "现货黄金", "黄金9999", "纸黄金(人民币)", "纸黄金(美元)"]
            },
            {
                "name": "Sina",
                "url": "https://finance.sina.com.cn/nmetal/",
                "enabled": True,
                "priority": 3,
                "description": "新浪财经",
                "target_products": ["XAUUSD", "沪金主力", "黄金T+D", "XAGUSD", "沪银主力", "白银T+D"]
            }
        ]
        
        websites_config = self._gold_config.get("websites", default_websites)
        
        # 按优先级排序并过滤启用的网站
        enabled_websites = [site for site in websites_config if site.get("enabled", True)]
        enabled_websites.sort(key=lambda x: x.get("priority", 99))
        
        return enabled_websites
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        default_config = {
            "enable_performance_monitoring": True,
            "enable_error_tracking": True,
            "log_level": "INFO",
            "metrics_collection_interval": 300
        }
        
        monitoring_config = self._gold_config.get("monitoring", {})
        default_config.update(monitoring_config)
        
        return default_config
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """获取健康检查配置"""
        default_config = {
            "enable_health_check": True,
            "check_interval": 600,
            "failure_threshold": 3,
            "recovery_threshold": 2
        }
        
        health_check_config = self._gold_config.get("health_check", {})
        default_config.update(health_check_config)
        
        return default_config
    
    def get_proxy_config(self) -> Dict[str, Any]:
        """获取代理配置（从现有crawler配置继承）"""
        crawler_config = self._config.get("crawler", {})
        
        return {
            "use_proxy": crawler_config.get("use_proxy", False),
            "proxy_url": crawler_config.get("default_proxy", "http://127.0.0.1:10086")
        }
    
    def get_log_level(self) -> str:
        """获取日志级别"""
        monitoring_config = self.get_monitoring_config()
        return monitoring_config.get("log_level", "INFO")
    
    def setup_logging(self) -> None:
        """设置日志配置"""
        log_level = self.get_log_level()
        
        # 配置黄金爬虫相关的日志记录器
        loggers = [
            "GoldScraperConfig",
            "WebScrapingManager", 
            "Parser.SGE",
            "Parser.Cngold",
            "Parser.Sina",
            "DataFetcherExtension"
        ]
        
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            
            # 如果没有处理器，添加控制台处理器
            if not logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)
    
    def validate_config(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            配置是否有效
        """
        try:
            # 检查必要的配置段
            if not self.is_enabled():
                self.logger.warning("黄金爬虫功能未启用")
                return False
            
            # 验证执行配置
            execution_config = self.get_execution_config()
            if execution_config["max_concurrent_parsers"] <= 0:
                self.logger.error("max_concurrent_parsers 必须大于 0")
                return False
            
            if execution_config["parser_timeout"] <= 0:
                self.logger.error("parser_timeout 必须大于 0")
                return False
            
            # 验证网站配置
            websites = self.get_websites_config()
            if not websites:
                self.logger.error("没有启用的网站配置")
                return False
            
            # 验证数据验证配置
            validation_config = self.get_validation_config()
            price_range = validation_config["price_range"]
            if len(price_range) != 2 or price_range[0] >= price_range[1]:
                self.logger.error("price_range 配置无效")
                return False
            
            self.logger.info("配置验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            return False
    
    def get_full_config(self) -> Dict[str, Any]:
        """获取完整的黄金爬虫配置"""
        return {
            "enabled": self.is_enabled(),
            "fallback_mode": self.is_fallback_mode(),
            "execution": self.get_execution_config(),
            "anti_detection": self.get_anti_detection_config(),
            "validation": self.get_validation_config(),
            "websites": self.get_websites_config(),
            "monitoring": self.get_monitoring_config(),
            "health_check": self.get_health_check_config(),
            "proxy": self.get_proxy_config()
        }
    
    def reload_config(self) -> None:
        """重新加载配置"""
        try:
            self._config = self._load_config()
            self._gold_config = self._config.get("gold_scraper", {})
            self.logger.info("配置重新加载成功")
        except Exception as e:
            self.logger.error(f"配置重新加载失败: {e}")
            raise


# 全局配置实例
_config_instance = None


def get_gold_scraper_config(config_path: Optional[str] = None) -> GoldScraperConfig:
    """
    获取黄金爬虫配置实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置管理器实例
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = GoldScraperConfig(config_path)
    
    return _config_instance


def reload_gold_scraper_config() -> None:
    """重新加载配置"""
    global _config_instance
    
    if _config_instance:
        _config_instance.reload_config()


# 导出主要类和函数
__all__ = [
    'GoldScraperConfig',
    'get_gold_scraper_config',
    'reload_gold_scraper_config'
]