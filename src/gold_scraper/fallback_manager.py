#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源降级管理器
实现API优先、爬虫备用的智能切换策略
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from datetime import datetime, timedelta


class DataSourceType(Enum):
    """数据源类型"""
    API = "api"
    SCRAPER = "scraper"


class DataSourceStatus(Enum):
    """数据源状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class FallbackManager:
    """降级管理器 - MVP版本"""
    
    def __init__(self):
        self.logger = logging.getLogger("FallbackManager")
        
        # 数据源状态跟踪
        self.source_status = {
            DataSourceType.API: DataSourceStatus.UNKNOWN,
            DataSourceType.SCRAPER: DataSourceStatus.UNKNOWN
        }
        
        # 失败计数器
        self.failure_counts = {
            DataSourceType.API: 0,
            DataSourceType.SCRAPER: 0
        }
        
        # 最后成功时间
        self.last_success_time = {
            DataSourceType.API: None,
            DataSourceType.SCRAPER: None
        }
        
        # 配置参数
        self.config = {
            "api_failure_threshold": 3,      # API连续失败阈值
            "scraper_failure_threshold": 5,  # 爬虫连续失败阈值
            "health_check_interval": 300,    # 健康检查间隔（秒）
            "recovery_check_interval": 600,  # 恢复检查间隔（秒）
            "api_timeout": 10,               # API超时时间（秒）
            "scraper_timeout": 60            # 爬虫超时时间（秒）
        }
        
        self.logger.info("降级管理器初始化完成")
    
    def get_preferred_source(self) -> DataSourceType:
        """
        获取首选数据源
        
        Returns:
            首选的数据源类型
        """
        # API优先策略
        if self.source_status[DataSourceType.API] in [DataSourceStatus.HEALTHY, DataSourceStatus.UNKNOWN]:
            return DataSourceType.API
        
        # API不可用时使用爬虫
        if self.source_status[DataSourceType.SCRAPER] in [DataSourceStatus.HEALTHY, DataSourceStatus.UNKNOWN]:
            return DataSourceType.SCRAPER
        
        # 都不可用时仍然尝试API（可能已恢复）
        return DataSourceType.API
    
    def record_success(self, source_type: DataSourceType, response_time: float = 0.0) -> None:
        """
        记录数据源成功
        
        Args:
            source_type: 数据源类型
            response_time: 响应时间
        """
        self.source_status[source_type] = DataSourceStatus.HEALTHY
        self.failure_counts[source_type] = 0
        self.last_success_time[source_type] = datetime.now()
        
        self.logger.info(f"{source_type.value} 数据源成功，响应时间: {response_time:.2f}s")
    
    def record_failure(self, source_type: DataSourceType, error: str = "") -> None:
        """
        记录数据源失败
        
        Args:
            source_type: 数据源类型
            error: 错误信息
        """
        self.failure_counts[source_type] += 1
        
        # 根据失败次数更新状态
        threshold = self.config.get(f"{source_type.value}_failure_threshold", 3)
        
        if self.failure_counts[source_type] >= threshold:
            self.source_status[source_type] = DataSourceStatus.FAILED
        else:
            self.source_status[source_type] = DataSourceStatus.DEGRADED
        
        self.logger.warning(
            f"{source_type.value} 数据源失败 (第{self.failure_counts[source_type]}次): {error}"
        )
    
    def should_fallback(self, current_source: DataSourceType) -> bool:
        """
        判断是否应该降级
        
        Args:
            current_source: 当前数据源
            
        Returns:
            是否应该降级
        """
        if current_source == DataSourceType.API:
            # API失败时降级到爬虫
            return self.source_status[DataSourceType.API] == DataSourceStatus.FAILED
        
        # 爬虫失败时没有进一步降级选项
        return False
    
    def get_fallback_source(self, current_source: DataSourceType) -> Optional[DataSourceType]:
        """
        获取降级数据源
        
        Args:
            current_source: 当前数据源
            
        Returns:
            降级数据源，如果没有则返回None
        """
        if current_source == DataSourceType.API:
            if self.source_status[DataSourceType.SCRAPER] != DataSourceStatus.FAILED:
                return DataSourceType.SCRAPER
        
        return None
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        获取状态摘要
        
        Returns:
            状态摘要字典
        """
        return {
            "preferred_source": self.get_preferred_source().value,
            "source_status": {
                source.value: status.value 
                for source, status in self.source_status.items()
            },
            "failure_counts": {
                source.value: count 
                for source, count in self.failure_counts.items()
            },
            "last_success_time": {
                source.value: time.isoformat() if time else None
                for source, time in self.last_success_time.items()
            },
            "config": self.config
        }
    
    def reset_source_status(self, source_type: DataSourceType) -> None:
        """
        重置数据源状态（用于手动恢复）
        
        Args:
            source_type: 数据源类型
        """
        self.source_status[source_type] = DataSourceStatus.UNKNOWN
        self.failure_counts[source_type] = 0
        
        self.logger.info(f"{source_type.value} 数据源状态已重置")
    
    def is_source_healthy(self, source_type: DataSourceType) -> bool:
        """
        检查数据源是否健康
        
        Args:
            source_type: 数据源类型
            
        Returns:
            数据源是否健康
        """
        return self.source_status[source_type] in [
            DataSourceStatus.HEALTHY, 
            DataSourceStatus.UNKNOWN
        ]


class DataSourceWrapper:
    """数据源包装器 - 简化版本"""
    
    def __init__(self, fallback_manager: FallbackManager):
        self.fallback_manager = fallback_manager
        self.logger = logging.getLogger("DataSourceWrapper")
    
    async def fetch_data_with_fallback(self, api_fetcher=None, scraper_fetcher=None) -> Tuple[Optional[str], str, bool]:
        """
        使用降级策略获取数据
        
        Args:
            api_fetcher: API数据获取函数
            scraper_fetcher: 爬虫数据获取函数
            
        Returns:
            Tuple[数据, 数据源, 是否使用了降级]
        """
        preferred_source = self.fallback_manager.get_preferred_source()
        used_fallback = False
        
        # 尝试首选数据源
        if preferred_source == DataSourceType.API and api_fetcher:
            try:
                self.logger.info("尝试使用API数据源")
                start_time = time.time()
                
                data = await api_fetcher()
                
                response_time = time.time() - start_time
                self.fallback_manager.record_success(DataSourceType.API, response_time)
                
                return data, "api", False
                
            except Exception as e:
                self.logger.error(f"API数据源失败: {e}")
                self.fallback_manager.record_failure(DataSourceType.API, str(e))
                
                # 检查是否需要降级
                if self.fallback_manager.should_fallback(DataSourceType.API):
                    fallback_source = self.fallback_manager.get_fallback_source(DataSourceType.API)
                    if fallback_source == DataSourceType.SCRAPER and scraper_fetcher:
                        used_fallback = True
                        self.logger.info("降级到爬虫数据源")
                        
                        try:
                            start_time = time.time()
                            data = await scraper_fetcher()
                            response_time = time.time() - start_time
                            
                            self.fallback_manager.record_success(DataSourceType.SCRAPER, response_time)
                            return data, "scraper", True
                            
                        except Exception as scraper_error:
                            self.logger.error(f"爬虫数据源也失败: {scraper_error}")
                            self.fallback_manager.record_failure(DataSourceType.SCRAPER, str(scraper_error))
        
        elif preferred_source == DataSourceType.SCRAPER and scraper_fetcher:
            try:
                self.logger.info("使用爬虫数据源")
                start_time = time.time()
                
                data = await scraper_fetcher()
                
                response_time = time.time() - start_time
                self.fallback_manager.record_success(DataSourceType.SCRAPER, response_time)
                
                return data, "scraper", False
                
            except Exception as e:
                self.logger.error(f"爬虫数据源失败: {e}")
                self.fallback_manager.record_failure(DataSourceType.SCRAPER, str(e))
        
        # 所有数据源都失败
        self.logger.error("所有数据源都不可用")
        return None, "none", used_fallback


# 全局实例
_fallback_manager_instance = None


def get_fallback_manager() -> FallbackManager:
    """
    获取降级管理器实例（单例模式）
    
    Returns:
        降级管理器实例
    """
    global _fallback_manager_instance
    
    if _fallback_manager_instance is None:
        _fallback_manager_instance = FallbackManager()
    
    return _fallback_manager_instance


# 导出主要类和函数
__all__ = [
    'FallbackManager',
    'DataSourceWrapper',
    'DataSourceType',
    'DataSourceStatus',
    'get_fallback_manager'
]