#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金爬虫性能监控模块
集成到TrendRadar现有监控系统
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import threading


@dataclass
class PerformanceMetric:
    """性能指标数据结构"""
    name: str
    value: float
    unit: str
    category: str
    timestamp: str
    source: str = "gold_scraper"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class GoldScraperPerformanceMonitor:
    """黄金爬虫性能监控器"""
    
    def __init__(self, max_history_size: int = 1000):
        """
        初始化性能监控器
        
        Args:
            max_history_size: 历史数据最大保存数量
        """
        self.logger = logging.getLogger("GoldScraperPerformanceMonitor")
        self.max_history_size = max_history_size
        
        # 性能指标存储
        self.metrics_history = deque(maxlen=max_history_size)
        self.current_metrics = {}
        
        # 计时器存储
        self.timers = {}
        
        # 统计数据
        self.stats = {
            "scraping_sessions": 0,
            "successful_scrapes": 0,
            "failed_scrapes": 0,
            "total_data_points": 0,
            "average_response_time": 0.0,
            "last_scrape_time": None
        }
        
        # 线程锁
        self._lock = threading.Lock()
        
        self.logger.info("黄金爬虫性能监控器初始化完成")
    
    def start_timer(self, timer_name: str) -> None:
        """
        开始计时
        
        Args:
            timer_name: 计时器名称
        """
        with self._lock:
            self.timers[timer_name] = time.time()
    
    def end_timer(self, timer_name: str, category: str = "timing") -> Optional[float]:
        """
        结束计时并记录指标
        
        Args:
            timer_name: 计时器名称
            category: 指标分类
            
        Returns:
            耗时（秒），如果计时器不存在则返回None
        """
        with self._lock:
            if timer_name not in self.timers:
                self.logger.warning(f"计时器 {timer_name} 不存在")
                return None
            
            start_time = self.timers.pop(timer_name)
            duration = time.time() - start_time
            
            # 记录性能指标
            self.record_metric(
                name=f"{timer_name}_duration",
                value=duration,
                unit="seconds",
                category=category
            )
            
            return duration
    
    def record_metric(
        self, 
        name: str, 
        value: float, 
        unit: str, 
        category: str,
        source: str = "gold_scraper"
    ) -> None:
        """
        记录性能指标
        
        Args:
            name: 指标名称
            value: 指标值
            unit: 单位
            category: 分类
            source: 数据源
        """
        with self._lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                unit=unit,
                category=category,
                timestamp=datetime.now().isoformat(),
                source=source
            )
            
            # 添加到历史记录
            self.metrics_history.append(metric)
            
            # 更新当前指标
            self.current_metrics[name] = metric
            
            self.logger.debug(f"记录性能指标: {name} = {value} {unit}")
    
    def record_scraping_session(
        self, 
        success: bool, 
        data_points: int = 0,
        response_time: float = 0.0,
        parser_name: str = "unknown"
    ) -> None:
        """
        记录爬取会话信息
        
        Args:
            success: 是否成功
            data_points: 获取的数据点数量
            response_time: 响应时间
            parser_name: 解析器名称
        """
        with self._lock:
            self.stats["scraping_sessions"] += 1
            self.stats["last_scrape_time"] = datetime.now().isoformat()
            
            if success:
                self.stats["successful_scrapes"] += 1
                self.stats["total_data_points"] += data_points
                
                # 更新平均响应时间
                if response_time > 0:
                    current_avg = self.stats["average_response_time"]
                    total_successful = self.stats["successful_scrapes"]
                    self.stats["average_response_time"] = (
                        (current_avg * (total_successful - 1) + response_time) / total_successful
                    )
            else:
                self.stats["failed_scrapes"] += 1
            
            # 记录相关指标
            self.record_metric(f"scrape_success_{parser_name}", 1 if success else 0, "boolean", "scraping")
            self.record_metric(f"data_points_{parser_name}", data_points, "count", "scraping")
            
            if response_time > 0:
                self.record_metric(f"response_time_{parser_name}", response_time, "seconds", "performance")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前性能指标"""
        with self._lock:
            return {name: metric.to_dict() for name, metric in self.current_metrics.items()}
    
    def get_metrics_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        按分类获取指标
        
        Args:
            category: 指标分类
            
        Returns:
            指标列表
        """
        with self._lock:
            return [
                metric.to_dict() 
                for metric in self.metrics_history 
                if metric.category == category
            ]
    
    def get_metrics_by_timerange(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        按时间范围获取指标
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            指标列表
        """
        with self._lock:
            results = []
            for metric in self.metrics_history:
                metric_time = datetime.fromisoformat(metric.timestamp)
                if start_time <= metric_time <= end_time:
                    results.append(metric.to_dict())
            return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = self.stats.copy()
            
            # 计算成功率
            total_scrapes = stats["scraping_sessions"]
            if total_scrapes > 0:
                stats["success_rate"] = stats["successful_scrapes"] / total_scrapes
                stats["failure_rate"] = stats["failed_scrapes"] / total_scrapes
            else:
                stats["success_rate"] = 0.0
                stats["failure_rate"] = 0.0
            
            # 计算平均数据点数
            if stats["successful_scrapes"] > 0:
                stats["average_data_points"] = stats["total_data_points"] / stats["successful_scrapes"]
            else:
                stats["average_data_points"] = 0.0
            
            return stats
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self._lock:
            # 计算最近的性能指标
            recent_metrics = self._get_recent_metrics(minutes=30)
            
            summary = {
                "total_metrics": len(self.metrics_history),
                "recent_metrics_count": len(recent_metrics),
                "statistics": self.get_statistics(),
                "recent_performance": self._analyze_recent_performance(recent_metrics)
            }
            
            return summary
    
    def _get_recent_metrics(self, minutes: int = 30) -> List[PerformanceMetric]:
        """获取最近的指标"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_metrics = []
        for metric in self.metrics_history:
            metric_time = datetime.fromisoformat(metric.timestamp)
            if metric_time >= cutoff_time:
                recent_metrics.append(metric)
        
        return recent_metrics
    
    def _analyze_recent_performance(self, recent_metrics: List[PerformanceMetric]) -> Dict[str, Any]:
        """分析最近的性能表现"""
        if not recent_metrics:
            return {"status": "no_recent_data"}
        
        # 按分类分组
        by_category = defaultdict(list)
        for metric in recent_metrics:
            by_category[metric.category].append(metric.value)
        
        analysis = {}
        
        # 分析各分类的性能
        for category, values in by_category.items():
            if values:
                analysis[category] = {
                    "count": len(values),
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        return analysis
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        with self._lock:
            self.stats = {
                "scraping_sessions": 0,
                "successful_scrapes": 0,
                "failed_scrapes": 0,
                "total_data_points": 0,
                "average_response_time": 0.0,
                "last_scrape_time": None
            }
            self.logger.info("性能统计信息已重置")
    
    def clear_history(self) -> None:
        """清空历史数据"""
        with self._lock:
            self.metrics_history.clear()
            self.current_metrics.clear()
            self.logger.info("性能监控历史数据已清空")
    
    def export_metrics(self, format_type: str = "dict") -> Any:
        """
        导出指标数据
        
        Args:
            format_type: 导出格式 ("dict", "json")
            
        Returns:
            导出的数据
        """
        with self._lock:
            data = {
                "statistics": self.get_statistics(),
                "current_metrics": self.get_current_metrics(),
                "metrics_history": [metric.to_dict() for metric in self.metrics_history],
                "export_time": datetime.now().isoformat()
            }
            
            if format_type == "json":
                import json
                return json.dumps(data, indent=2, ensure_ascii=False)
            else:
                return data


# 全局性能监控器实例
_performance_monitor_instance = None


def get_gold_scraper_performance_monitor() -> GoldScraperPerformanceMonitor:
    """
    获取黄金爬虫性能监控器实例（单例模式）
    
    Returns:
        性能监控器实例
    """
    global _performance_monitor_instance
    
    if _performance_monitor_instance is None:
        _performance_monitor_instance = GoldScraperPerformanceMonitor()
    
    return _performance_monitor_instance


def record_gold_scraper_metric(
    name: str, 
    value: float, 
    unit: str, 
    category: str = "general"
) -> None:
    """
    记录黄金爬虫性能指标的便捷函数
    
    Args:
        name: 指标名称
        value: 指标值
        unit: 单位
        category: 分类
    """
    monitor = get_gold_scraper_performance_monitor()
    monitor.record_metric(name, value, unit, category)


# 上下文管理器用于自动计时
class GoldScraperTimer:
    """黄金爬虫计时器上下文管理器"""
    
    def __init__(self, timer_name: str, category: str = "timing"):
        self.timer_name = timer_name
        self.category = category
        self.monitor = get_gold_scraper_performance_monitor()
    
    def __enter__(self):
        self.monitor.start_timer(self.timer_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monitor.end_timer(self.timer_name, self.category)


# 导出主要类和函数
__all__ = [
    'PerformanceMetric',
    'GoldScraperPerformanceMonitor',
    'get_gold_scraper_performance_monitor',
    'record_gold_scraper_metric',
    'GoldScraperTimer'
]