#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金价格解析器基类
定义所有解析器的通用接口和数据处理方法
"""

import re
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass


@dataclass
class GoldPriceData:
    """黄金价格数据结构"""
    source: str
    symbol: str
    price: float
    change: float
    change_percent: str
    timestamp: str
    currency: str = "CNY"
    volume: Optional[str] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open_price: Optional[float] = None
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None


class DataValidationError(Exception):
    """数据验证异常"""
    pass


class BaseParser(ABC):
    """黄金价格解析器基类"""
    
    def __init__(self, name: str, base_url: str):
        """
        初始化解析器
        
        Args:
            name: 解析器名称
            base_url: 网站基础URL
        """
        self.name = name
        self.base_url = base_url
        self.logger = logging.getLogger(f"Parser.{name}")
        
        # 数据验证配置
        self.price_range = (100.0, 10000.0)  # 价格合理范围
        self.change_range = (-1000.0, 1000.0)  # 涨跌额合理范围
        self.invalid_values = ["--", "N/A", "", None, "null", "undefined"]
    
    @abstractmethod
    async def parse_data(self, page_content: Any) -> List[GoldPriceData]:
        """
        抽象方法：解析页面数据
        
        Args:
            page_content: 页面内容（Playwright Page对象或HTML字符串）
            
        Returns:
            解析后的黄金价格数据列表
        """
        pass
    
    def clean_price_text(self, text: str) -> float:
        """
        清理价格文本，转换为浮点数
        
        Args:
            text: 原始价格文本
            
        Returns:
            清理后的价格数值
            
        Raises:
            DataValidationError: 价格数据无效时抛出
        """
        if not text or str(text).strip() in self.invalid_values:
            return 0.0
        
        # 移除货币符号、千分位分隔符和其他字符
        cleaned = str(text).strip()
        cleaned = re.sub(r'[￥$¥,，\s]', '', cleaned)
        
        # 提取数字部分
        number_match = re.search(r'(\d+\.?\d*)', cleaned)
        if not number_match:
            self.logger.warning(f"无法从文本中提取价格数字: {text}")
            return 0.0
        
        try:
            price = float(number_match.group(1))
            
            # 验证价格范围
            if not (self.price_range[0] <= price <= self.price_range[1]):
                self.logger.warning(f"价格超出合理范围: {price}")
                return 0.0
                
            return price
            
        except ValueError as e:
            self.logger.error(f"价格转换失败: {text} -> {e}")
            return 0.0
    
    def clean_change_text(self, text: str) -> Tuple[float, str]:
        """
        清理涨跌数据，返回涨跌额和涨跌幅
        
        Args:
            text: 原始涨跌文本
            
        Returns:
            (涨跌额, 涨跌幅)
        """
        if not text or str(text).strip() in self.invalid_values:
            return 0.0, "0.00%"
        
        text = str(text).strip()
        
        # 提取涨跌额（可能包含正负号和箭头）
        change_match = re.search(r'([+-]?\d+\.?\d*)', text)
        change = 0.0
        if change_match:
            try:
                change = float(change_match.group(1))
                # 验证涨跌额范围
                if not (self.change_range[0] <= change <= self.change_range[1]):
                    self.logger.warning(f"涨跌额超出合理范围: {change}")
                    change = 0.0
            except ValueError:
                change = 0.0
        
        # 提取涨跌幅
        percent_match = re.search(r'([+-]?\d+\.?\d*)%', text)
        if percent_match:
            percent = f"{percent_match.group(1)}%"
        else:
            # 如果没有百分号，尝试计算
            if change != 0.0:
                percent = f"{change:+.2f}%"
            else:
                percent = "0.00%"
        
        return change, percent
    
    def clean_volume_text(self, text: str) -> Optional[str]:
        """
        清理成交量文本
        
        Args:
            text: 原始成交量文本
            
        Returns:
            清理后的成交量字符串
        """
        if not text or str(text).strip() in self.invalid_values:
            return None
        
        # 保留原始格式，只做基本清理
        cleaned = str(text).strip()
        return cleaned if cleaned else None
    
    def validate_data(self, data: GoldPriceData) -> bool:
        """
        验证数据完整性和合理性
        
        Args:
            data: 待验证的数据
            
        Returns:
            验证是否通过
        """
        try:
            # 必填字段检查
            if not data.source or not data.symbol:
                self.logger.warning(f"缺少必填字段: source={data.source}, symbol={data.symbol}")
                return False
            
            # 价格合理性检查
            if data.price <= 0 or not (self.price_range[0] <= data.price <= self.price_range[1]):
                self.logger.warning(f"价格不合理: {data.price}")
                return False
            
            # 时间戳格式检查
            if not data.timestamp:
                self.logger.warning("缺少时间戳")
                return False
            
            # 货币类型检查
            if data.currency not in ["CNY", "USD", "EUR", "JPY"]:
                self.logger.warning(f"不支持的货币类型: {data.currency}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"数据验证异常: {e}")
            return False
    
    def standardize_symbol(self, symbol: str) -> str:
        """
        标准化合约/产品名称
        
        Args:
            symbol: 原始合约名称
            
        Returns:
            标准化后的合约名称
        """
        if not symbol:
            return ""
        
        symbol = str(symbol).strip()
        
        # 标准化映射
        symbol_mapping = {
            "Au99.99": "AU9999",
            "Au(T+D)": "AUTD",
            "mAu(T+D)": "MAUTD",
            "Au99.95": "AU9995",
            "Au100g": "AU100G",
            "黄金T+D": "GOLD_TD",
            "现货黄金": "SPOT_GOLD",
            "黄金9999": "GOLD_9999",
            "纸黄金(人民币)": "PAPER_GOLD_CNY",
            "纸黄金(美元)": "PAPER_GOLD_USD",
            "XAUUSD": "XAUUSD",
            "沪金主力": "SHFE_GOLD_MAIN"
        }
        
        return symbol_mapping.get(symbol, symbol)
    
    def format_timestamp(self, timestamp: Optional[str] = None) -> str:
        """
        格式化时间戳为ISO 8601格式
        
        Args:
            timestamp: 原始时间戳，为None时使用当前时间
            
        Returns:
            ISO 8601格式的时间戳
        """
        if timestamp:
            try:
                # 尝试解析各种时间格式
                from dateutil import parser
                dt = parser.parse(timestamp)
                return dt.isoformat()
            except Exception:
                self.logger.warning(f"时间戳解析失败，使用当前时间: {timestamp}")
        
        return datetime.now().isoformat()
    
    def create_gold_data(
        self,
        symbol: str,
        price: Union[str, float],
        change: Union[str, float] = 0.0,
        change_percent: str = "0.00%",
        currency: str = "CNY",
        **kwargs
    ) -> Optional[GoldPriceData]:
        """
        创建标准化的黄金价格数据对象
        
        Args:
            symbol: 合约/产品名称
            price: 价格
            change: 涨跌额
            change_percent: 涨跌幅
            currency: 货币类型
            **kwargs: 其他可选字段
            
        Returns:
            标准化的黄金价格数据对象，验证失败时返回None
        """
        try:
            # 清理和转换数据
            clean_price = self.clean_price_text(str(price))
            clean_change, clean_percent = self.clean_change_text(str(change)) if isinstance(change, str) else (float(change), change_percent)
            
            # 创建数据对象
            data = GoldPriceData(
                source=self.name.lower(),
                symbol=self.standardize_symbol(symbol),
                price=clean_price,
                change=clean_change,
                change_percent=clean_percent,
                timestamp=self.format_timestamp(kwargs.get('timestamp')),
                currency=currency,
                volume=self.clean_volume_text(kwargs.get('volume', '')),
                high=self.clean_price_text(str(kwargs.get('high', 0))) if kwargs.get('high') else None,
                low=self.clean_price_text(str(kwargs.get('low', 0))) if kwargs.get('low') else None,
                open_price=self.clean_price_text(str(kwargs.get('open_price', 0))) if kwargs.get('open_price') else None,
                buy_price=self.clean_price_text(str(kwargs.get('buy_price', 0))) if kwargs.get('buy_price') else None,
                sell_price=self.clean_price_text(str(kwargs.get('sell_price', 0))) if kwargs.get('sell_price') else None
            )
            
            # 验证数据
            if self.validate_data(data):
                return data
            else:
                self.logger.warning(f"数据验证失败: {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"创建数据对象失败: {symbol} -> {e}")
            return None
    
    def get_parser_info(self) -> Dict[str, Any]:
        """
        获取解析器信息
        
        Returns:
            解析器信息字典
        """
        return {
            "name": self.name,
            "base_url": self.base_url,
            "price_range": self.price_range,
            "change_range": self.change_range,
            "supported_currencies": ["CNY", "USD", "EUR", "JPY"]
        }


# 导出主要类
__all__ = [
    'BaseParser',
    'GoldPriceData',
    'DataValidationError'
]