#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证和一致性检查模块
确保API和爬虫数据的质量和一致性
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    score: float  # 0-100分
    issues: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class DataValidator:
    """数据验证器 - MVP版本"""
    
    def __init__(self):
        self.logger = logging.getLogger("DataValidator")
        
        # 验证规则配置
        self.validation_rules = {
            "required_fields": ["price", "symbol", "timestamp"],
            "price_range": [50.0, 2000.0],  # 黄金价格合理范围（美元/盎司）
            "max_price_change": 50.0,       # 最大价格变化（美元）
            "max_age_minutes": 60,          # 数据最大年龄（分钟）
            "min_data_points": 1,           # 最少数据点数量
            "max_data_points": 100          # 最多数据点数量
        }
        
        self.logger.info("数据验证器初始化完成")
    
    def validate_gold_data(self, data: Any, source: str = "unknown") -> ValidationResult:
        """
        验证黄金价格数据
        
        Args:
            data: 待验证的数据
            source: 数据源标识
            
        Returns:
            验证结果
        """
        issues = []
        warnings = []
        score = 100.0
        metadata = {"source": source, "validation_time": datetime.now().isoformat()}
        
        try:
            # 解析JSON数据
            if isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError as e:
                    issues.append(f"JSON解析失败: {e}")
                    return ValidationResult(False, 0.0, issues, warnings, metadata)
            else:
                parsed_data = data
            
            # 基本结构验证
            structure_score = self._validate_structure(parsed_data, issues, warnings)
            score = min(score, structure_score)
            
            # 数据内容验证
            if "items" in parsed_data:
                content_score = self._validate_content(parsed_data["items"], issues, warnings)
                score = min(score, content_score)
                metadata["item_count"] = len(parsed_data["items"])
            else:
                issues.append("缺少items字段")
                score -= 30
            
            # 时效性验证
            timeliness_score = self._validate_timeliness(parsed_data, issues, warnings)
            score = min(score, timeliness_score)
            
            # 一致性验证
            consistency_score = self._validate_consistency(parsed_data, issues, warnings)
            score = min(score, consistency_score)
            
        except Exception as e:
            issues.append(f"验证过程异常: {e}")
            score = 0.0
        
        # 确定验证结果
        is_valid = len(issues) == 0 and score >= 60.0
        
        metadata.update({
            "final_score": score,
            "issue_count": len(issues),
            "warning_count": len(warnings)
        })
        
        self.logger.info(f"数据验证完成 - 来源: {source}, 分数: {score:.1f}, 有效: {is_valid}")
        
        return ValidationResult(is_valid, score, issues, warnings, metadata)
    
    def _validate_structure(self, data: Dict[str, Any], issues: List[str], warnings: List[str]) -> float:
        """验证数据结构"""
        score = 100.0
        
        # 检查必需字段
        if "status" not in data:
            issues.append("缺少status字段")
            score -= 20
        elif data["status"] != "success":
            warnings.append(f"状态不是success: {data['status']}")
            score -= 10
        
        if "timestamp" not in data:
            warnings.append("缺少timestamp字段")
            score -= 5
        
        if "source" not in data:
            warnings.append("缺少source字段")
            score -= 5
        
        return score
    
    def _validate_content(self, items: List[Dict[str, Any]], issues: List[str], warnings: List[str]) -> float:
        """验证数据内容"""
        score = 100.0
        
        # 检查数据点数量
        item_count = len(items)
        if item_count < self.validation_rules["min_data_points"]:
            issues.append(f"数据点数量不足: {item_count}")
            score -= 30
        elif item_count > self.validation_rules["max_data_points"]:
            warnings.append(f"数据点数量过多: {item_count}")
            score -= 10
        
        # 验证每个数据项
        valid_items = 0
        for i, item in enumerate(items):
            item_score = self._validate_item(item, issues, warnings, i)
            if item_score >= 60:
                valid_items += 1
        
        # 计算有效数据比例
        if item_count > 0:
            valid_ratio = valid_items / item_count
            if valid_ratio < 0.5:
                issues.append(f"有效数据比例过低: {valid_ratio:.2f}")
                score -= 40
            elif valid_ratio < 0.8:
                warnings.append(f"有效数据比例较低: {valid_ratio:.2f}")
                score -= 15
        
        return score
    
    def _validate_item(self, item: Dict[str, Any], issues: List[str], warnings: List[str], index: int) -> float:
        """验证单个数据项"""
        score = 100.0
        
        # 检查必需字段
        for field in self.validation_rules["required_fields"]:
            if field not in item:
                issues.append(f"数据项{index}缺少{field}字段")
                score -= 30
        
        # 验证价格
        if "price" in item:
            try:
                price = float(item["price"])
                price_range = self.validation_rules["price_range"]
                
                if not (price_range[0] <= price <= price_range[1]):
                    warnings.append(f"数据项{index}价格超出合理范围: {price}")
                    score -= 20
                    
            except (ValueError, TypeError):
                issues.append(f"数据项{index}价格格式无效: {item['price']}")
                score -= 25
        
        # 验证符号
        if "symbol" in item:
            symbol = str(item["symbol"]).strip()
            if not symbol:
                warnings.append(f"数据项{index}符号为空")
                score -= 10
        
        return score
    
    def _validate_timeliness(self, data: Dict[str, Any], issues: List[str], warnings: List[str]) -> float:
        """验证数据时效性"""
        score = 100.0
        
        try:
            # 检查数据时间戳
            if "timestamp" in data:
                timestamp_str = data["timestamp"]
                data_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                current_time = datetime.now()
                
                # 计算数据年龄
                age_minutes = (current_time - data_time).total_seconds() / 60
                max_age = self.validation_rules["max_age_minutes"]
                
                if age_minutes > max_age:
                    warnings.append(f"数据过期: {age_minutes:.1f}分钟前")
                    score -= min(30, age_minutes - max_age)
                    
        except Exception as e:
            warnings.append(f"时间戳验证失败: {e}")
            score -= 10
        
        return score
    
    def _validate_consistency(self, data: Dict[str, Any], issues: List[str], warnings: List[str]) -> float:
        """验证数据一致性"""
        score = 100.0
        
        if "items" not in data:
            return score
        
        items = data["items"]
        if len(items) < 2:
            return score
        
        # 检查价格一致性
        prices = []
        for item in items:
            if "price" in item:
                try:
                    price = float(item["price"])
                    prices.append(price)
                except (ValueError, TypeError):
                    continue
        
        if len(prices) >= 2:
            price_range = max(prices) - min(prices)
            max_change = self.validation_rules["max_price_change"]
            
            if price_range > max_change:
                warnings.append(f"价格变化范围过大: {price_range:.2f}")
                score -= 15
        
        return score
    
    def compare_sources(self, api_data: Any, scraper_data: Any) -> Dict[str, Any]:
        """
        比较API和爬虫数据的一致性
        
        Args:
            api_data: API数据
            scraper_data: 爬虫数据
            
        Returns:
            比较结果
        """
        comparison = {
            "api_validation": self.validate_gold_data(api_data, "api"),
            "scraper_validation": self.validate_gold_data(scraper_data, "scraper"),
            "consistency_score": 0.0,
            "differences": []
        }
        
        try:
            # 解析数据
            api_parsed = json.loads(api_data) if isinstance(api_data, str) else api_data
            scraper_parsed = json.loads(scraper_data) if isinstance(scraper_data, str) else scraper_data
            
            # 比较数据点数量
            api_count = len(api_parsed.get("items", []))
            scraper_count = len(scraper_parsed.get("items", []))
            
            if abs(api_count - scraper_count) > 5:
                comparison["differences"].append(f"数据点数量差异: API={api_count}, 爬虫={scraper_count}")
            
            # 比较价格（如果有相同符号）
            api_prices = self._extract_prices(api_parsed)
            scraper_prices = self._extract_prices(scraper_parsed)
            
            common_symbols = set(api_prices.keys()) & set(scraper_prices.keys())
            
            if common_symbols:
                price_diffs = []
                for symbol in common_symbols:
                    api_price = api_prices[symbol]
                    scraper_price = scraper_prices[symbol]
                    diff = abs(api_price - scraper_price)
                    price_diffs.append(diff)
                    
                    if diff > 5.0:  # 价格差异超过5美元
                        comparison["differences"].append(
                            f"{symbol}价格差异: API={api_price:.2f}, 爬虫={scraper_price:.2f}"
                        )
                
                # 计算一致性分数
                if price_diffs:
                    avg_diff = sum(price_diffs) / len(price_diffs)
                    comparison["consistency_score"] = max(0, 100 - avg_diff * 10)
                else:
                    comparison["consistency_score"] = 100
            
        except Exception as e:
            comparison["differences"].append(f"比较过程异常: {e}")
        
        return comparison
    
    def _extract_prices(self, data: Dict[str, Any]) -> Dict[str, float]:
        """提取价格数据"""
        prices = {}
        
        for item in data.get("items", []):
            if "symbol" in item and "price" in item:
                try:
                    symbol = str(item["symbol"])
                    price = float(item["price"])
                    prices[symbol] = price
                except (ValueError, TypeError):
                    continue
        
        return prices


# 全局实例
_data_validator_instance = None


def get_data_validator() -> DataValidator:
    """
    获取数据验证器实例（单例模式）
    
    Returns:
        数据验证器实例
    """
    global _data_validator_instance
    
    if _data_validator_instance is None:
        _data_validator_instance = DataValidator()
    
    return _data_validator_instance


# 导出主要类和函数
__all__ = [
    'DataValidator',
    'ValidationResult',
    'get_data_validator'
]