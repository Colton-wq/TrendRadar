#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金爬虫错误处理模块
扩展TrendRadar现有错误处理机制
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class GoldScraperErrorType(Enum):
    """黄金爬虫错误类型"""
    NETWORK_ERROR = "network_error"
    PARSER_ERROR = "parser_error"
    DATA_VALIDATION_ERROR = "data_validation_error"
    CONFIG_ERROR = "config_error"
    TIMEOUT_ERROR = "timeout_error"
    BROWSER_ERROR = "browser_error"
    UNKNOWN_ERROR = "unknown_error"


class GoldScraperError(Exception):
    """黄金爬虫基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        error_type: GoldScraperErrorType = GoldScraperErrorType.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.context = context or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message": self.message,
            "error_type": self.error_type.value,
            "context": self.context,
            "timestamp": self.timestamp,
            "original_exception": str(self.original_exception) if self.original_exception else None
        }


class NetworkError(GoldScraperError):
    """网络相关错误"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, GoldScraperErrorType.NETWORK_ERROR, context, original_exception)


class ParserError(GoldScraperError):
    """解析器相关错误"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, GoldScraperErrorType.PARSER_ERROR, context, original_exception)


class DataValidationError(GoldScraperError):
    """数据验证错误"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, GoldScraperErrorType.DATA_VALIDATION_ERROR, context, original_exception)


class ConfigError(GoldScraperError):
    """配置相关错误"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, GoldScraperErrorType.CONFIG_ERROR, context, original_exception)


class TimeoutError(GoldScraperError):
    """超时错误"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, GoldScraperErrorType.TIMEOUT_ERROR, context, original_exception)


class BrowserError(GoldScraperError):
    """浏览器相关错误"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, GoldScraperErrorType.BROWSER_ERROR, context, original_exception)


class GoldScraperErrorHandler:
    """黄金爬虫错误处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger("GoldScraperErrorHandler")
        self.error_stats = {
            "total_errors": 0,
            "error_by_type": {},
            "error_by_source": {},
            "last_error_time": None
        }
    
    def handle_error(
        self, 
        error: Exception, 
        source: str = "unknown",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        处理错误
        
        Args:
            error: 异常对象
            source: 错误来源
            context: 错误上下文
        """
        # 更新统计信息
        self._update_error_stats(error, source)
        
        # 记录错误日志
        self._log_error(error, source, context)
        
        # 根据错误类型执行特定处理
        self._handle_specific_error(error, source, context)
    
    def _update_error_stats(self, error: Exception, source: str) -> None:
        """更新错误统计信息"""
        self.error_stats["total_errors"] += 1
        self.error_stats["last_error_time"] = datetime.now().isoformat()
        
        # 按错误类型统计
        if isinstance(error, GoldScraperError):
            error_type = error.error_type.value
        else:
            error_type = type(error).__name__
        
        if error_type not in self.error_stats["error_by_type"]:
            self.error_stats["error_by_type"][error_type] = 0
        self.error_stats["error_by_type"][error_type] += 1
        
        # 按来源统计
        if source not in self.error_stats["error_by_source"]:
            self.error_stats["error_by_source"][source] = 0
        self.error_stats["error_by_source"][source] += 1
    
    def _log_error(
        self, 
        error: Exception, 
        source: str, 
        context: Optional[Dict[str, Any]]
    ) -> None:
        """记录错误日志"""
        error_info = {
            "source": source,
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context or {}
        }
        
        if isinstance(error, GoldScraperError):
            error_info.update(error.to_dict())
        
        # 记录详细的错误信息
        self.logger.error(
            f"黄金爬虫错误 - 来源: {source}, 类型: {error_info['error_type']}, "
            f"消息: {error_info['message']}, 上下文: {error_info['context']}"
        )
        
        # 记录堆栈跟踪（仅在DEBUG级别）
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"错误堆栈跟踪:\n{traceback.format_exc()}")
    
    def _handle_specific_error(
        self, 
        error: Exception, 
        source: str, 
        context: Optional[Dict[str, Any]]
    ) -> None:
        """根据错误类型执行特定处理"""
        if isinstance(error, NetworkError):
            self._handle_network_error(error, source, context)
        elif isinstance(error, ParserError):
            self._handle_parser_error(error, source, context)
        elif isinstance(error, DataValidationError):
            self._handle_validation_error(error, source, context)
        elif isinstance(error, ConfigError):
            self._handle_config_error(error, source, context)
        elif isinstance(error, TimeoutError):
            self._handle_timeout_error(error, source, context)
        elif isinstance(error, BrowserError):
            self._handle_browser_error(error, source, context)
        else:
            self._handle_unknown_error(error, source, context)
    
    def _handle_network_error(
        self, 
        error: NetworkError, 
        source: str, 
        context: Optional[Dict[str, Any]]
    ) -> None:
        """处理网络错误"""
        self.logger.warning(f"网络错误处理 - {source}: {error.message}")
        
        # 可以在这里添加网络错误的特定处理逻辑
        # 例如：重试机制、切换代理等
    
    def _handle_parser_error(
        self, 
        error: ParserError, 
        source: str, 
        context: Optional[Dict[str, Any]]
    ) -> None:
        """处理解析器错误"""
        self.logger.warning(f"解析器错误处理 - {source}: {error.message}")
        
        # 可以在这里添加解析器错误的特定处理逻辑
        # 例如：切换解析策略、跳过当前数据等
    
    def _handle_validation_error(
        self, 
        error: DataValidationError, 
        source: str, 
        context: Optional[Dict[str, Any]]
    ) -> None:
        """处理数据验证错误"""
        self.logger.warning(f"数据验证错误处理 - {source}: {error.message}")
        
        # 可以在这里添加数据验证错误的特定处理逻辑
        # 例如：记录异常数据、调整验证规则等
    
    def _handle_config_error(
        self, 
        error: ConfigError, 
        source: str, 
        context: Optional[Dict[str, Any]]
    ) -> None:
        """处理配置错误"""
        self.logger.error(f"配置错误处理 - {source}: {error.message}")
        
        # 配置错误通常比较严重，可能需要停止相关功能
    
    def _handle_timeout_error(
        self, 
        error: TimeoutError, 
        source: str, 
        context: Optional[Dict[str, Any]]
    ) -> None:
        """处理超时错误"""
        self.logger.warning(f"超时错误处理 - {source}: {error.message}")
        
        # 可以在这里添加超时错误的特定处理逻辑
        # 例如：增加超时时间、重试等
    
    def _handle_browser_error(
        self, 
        error: BrowserError, 
        source: str, 
        context: Optional[Dict[str, Any]]
    ) -> None:
        """处理浏览器错误"""
        self.logger.warning(f"浏览器错误处理 - {source}: {error.message}")
        
        # 可以在这里添加浏览器错误的特定处理逻辑
        # 例如：重启浏览器、切换浏览器类型等
    
    def _handle_unknown_error(
        self, 
        error: Exception, 
        source: str, 
        context: Optional[Dict[str, Any]]
    ) -> None:
        """处理未知错误"""
        self.logger.error(f"未知错误处理 - {source}: {str(error)}")
        
        # 对于未知错误，记录详细信息以便后续分析
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return self.error_stats.copy()
    
    def reset_error_stats(self) -> None:
        """重置错误统计信息"""
        self.error_stats = {
            "total_errors": 0,
            "error_by_type": {},
            "error_by_source": {},
            "last_error_time": None
        }
        self.logger.info("错误统计信息已重置")
    
    def is_error_rate_high(self, threshold: float = 0.5) -> bool:
        """
        检查错误率是否过高
        
        Args:
            threshold: 错误率阈值
            
        Returns:
            错误率是否超过阈值
        """
        # 这里可以实现更复杂的错误率计算逻辑
        # 目前简单返回False
        return False


# 全局错误处理器实例
_error_handler_instance = None


def get_gold_scraper_error_handler() -> GoldScraperErrorHandler:
    """
    获取黄金爬虫错误处理器实例（单例模式）
    
    Returns:
        错误处理器实例
    """
    global _error_handler_instance
    
    if _error_handler_instance is None:
        _error_handler_instance = GoldScraperErrorHandler()
    
    return _error_handler_instance


def handle_gold_scraper_error(
    error: Exception, 
    source: str = "unknown",
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    处理黄金爬虫错误的便捷函数
    
    Args:
        error: 异常对象
        source: 错误来源
        context: 错误上下文
    """
    error_handler = get_gold_scraper_error_handler()
    error_handler.handle_error(error, source, context)


# 导出主要类和函数
__all__ = [
    'GoldScraperError',
    'NetworkError',
    'ParserError', 
    'DataValidationError',
    'ConfigError',
    'TimeoutError',
    'BrowserError',
    'GoldScraperErrorHandler',
    'get_gold_scraper_error_handler',
    'handle_gold_scraper_error'
]