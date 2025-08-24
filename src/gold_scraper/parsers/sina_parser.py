#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新浪财经数据解析器
专门处理新浪财经的黄金价格数据提取和解析
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Any, Dict
from urllib.parse import urljoin

try:
    from playwright.async_api import Page
except ImportError:
    Page = None

from .base_parser import BaseParser, GoldPriceData


class SinaParser(BaseParser):
    """新浪财经解析器"""
    
    def __init__(self):
        super().__init__("Sina", "https://finance.sina.com.cn/")
        
        # 新浪财经特定配置
        self.data_url = "https://finance.sina.com.cn/nmetal/"
        self.target_products = [
            "XAUUSD", "沪金主力", "黄金T+D",
            "XAGUSD", "沪银主力", "白银T+D"
        ]
        
        # CSS选择器配置
        self.selectors = {
            "price_table": ".data_table, .price_table, table",
            "data_rows": "tr:not(:first-child)",
            "cells": {
                "name": "td:nth-child(1)",
                "price": "td:nth-child(2)",
                "change": "td:nth-child(3)",
                "change_percent": "td:nth-child(4)",
                "high": "td:nth-child(5)",
                "low": "td:nth-child(6)",
                "open": "td:nth-child(7)",
                "volume": "td:nth-child(8)"
            },
            "quote_elements": ".quote, .price_info",
            "realtime_data": ".realtime_data, .live_data"
        }
        
        # 产品映射配置
        self.product_mapping = {
            "XAUUSD": {"currency": "USD", "priority": 1, "symbol_alt": ["现货黄金", "国际金价"]},
            "沪金主力": {"currency": "CNY", "priority": 2, "symbol_alt": ["沪金", "AU主力"]},
            "黄金T+D": {"currency": "CNY", "priority": 3, "symbol_alt": ["Au(T+D)", "黄金延期"]},
            "XAGUSD": {"currency": "USD", "priority": 4, "symbol_alt": ["现货白银", "国际银价"]},
            "沪银主力": {"currency": "CNY", "priority": 5, "symbol_alt": ["沪银", "AG主力"]},
            "白银T+D": {"currency": "CNY", "priority": 6, "symbol_alt": ["Ag(T+D)", "白银延期"]}
        }
    
    async def parse_data(self, page: Page) -> List[GoldPriceData]:
        """
        解析新浪财经页面数据
        
        Args:
            page: Playwright页面对象
            
        Returns:
            解析后的黄金价格数据列表
        """
        if not page:
            self.logger.error("页面对象为空")
            return []
        
        try:
            self.logger.info(f"访问新浪财经页面: {self.data_url}")
            await page.goto(self.data_url, wait_until="networkidle", timeout=30000)
            
            # 等待页面加载
            await page.wait_for_selector("table, .data_table", timeout=15000)
            
            results = []
            
            # 解析表格数据
            table_results = await self._parse_tables(page)
            results.extend(table_results)
            
            # 解析实时报价数据
            quote_results = await self._parse_quote_data(page)
            results.extend(quote_results)
            
            # 去重和排序
            results = self._deduplicate_and_sort(results)
            
            self.logger.info(f"新浪财经解析完成，获取 {len(results)} 条有效数据")
            return results
            
        except Exception as e:
            self.logger.error(f"新浪财经页面解析失败: {e}")
            return []
    
    async def _parse_tables(self, page: Page) -> List[GoldPriceData]:
        """
        解析表格数据
        
        Args:
            page: Playwright页面对象
            
        Returns:
            解析后的数据列表
        """
        results = []
        
        try:
            # 获取所有表格
            tables = await page.query_selector_all(self.selectors["price_table"])
            
            if not tables:
                self.logger.debug("未找到价格表格")
                return results
            
            for table_index, table in enumerate(tables[:5]):  # 只处理前5个表格
                try:
                    self.logger.debug(f"解析表格 {table_index}")
                    
                    # 获取表格行
                    rows = await table.query_selector_all(self.selectors["data_rows"])
                    
                    for row_index, row in enumerate(rows):
                        try:
                            row_data = await self._extract_table_row_data(row, table_index)
                            if row_data:
                                results.append(row_data)
                                
                        except Exception as e:
                            self.logger.debug(f"表格 {table_index} 第 {row_index} 行解析失败: {e}")
                            continue
                            
                except Exception as e:
                    self.logger.error(f"解析表格 {table_index} 失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析表格数据失败: {e}")
        
        return results
    
    async def _extract_table_row_data(self, row, table_index: int) -> Optional[GoldPriceData]:
        """
        提取表格行数据
        
        Args:
            row: 表格行元素
            table_index: 表格索引
            
        Returns:
            解析后的数据对象，失败时返回None
        """
        try:
            # 获取所有单元格
            cells = await row.query_selector_all("td")
            
            if len(cells) < 4:
                return None
            
            # 提取基础数据
            name = await cells[0].inner_text() if len(cells) > 0 else ""
            price_text = await cells[1].inner_text() if len(cells) > 1 else "0"
            change_text = await cells[2].inner_text() if len(cells) > 2 else "0"
            change_percent_text = await cells[3].inner_text() if len(cells) > 3 else "0.00%"
            
            # 可选数据
            high_text = await cells[4].inner_text() if len(cells) > 4 else "0"
            low_text = await cells[5].inner_text() if len(cells) > 5 else "0"
            open_text = await cells[6].inner_text() if len(cells) > 6 else "0"
            volume_text = await cells[7].inner_text() if len(cells) > 7 else ""
            
            # 清理产品名称
            name = name.strip()
            
            # 匹配目标产品（包括别名）
            matched_product = self._match_product_name(name)
            if not matched_product:
                return None
            
            # 获取产品配置
            product_config = self.product_mapping[matched_product]
            
            # 处理涨跌数据
            combined_change = f"{change_text} {change_percent_text}"
            
            # 创建数据对象
            gold_data = self.create_gold_data(
                symbol=matched_product,
                price=price_text,
                change=combined_change,
                change_percent=change_percent_text,
                currency=product_config["currency"],
                high=high_text,
                low=low_text,
                open_price=open_text,
                volume=volume_text
            )
            
            if gold_data:
                gold_data.source = f"sina_table_{table_index}"
                self.logger.debug(f"成功解析新浪财经数据: {matched_product} = {gold_data.price}")
                
            return gold_data
            
        except Exception as e:
            self.logger.error(f"提取表格行数据失败: {e}")
            return None
    
    async def _parse_quote_data(self, page: Page) -> List[GoldPriceData]:
        """
        解析实时报价数据
        
        Args:
            page: Playwright页面对象
            
        Returns:
            解析后的数据列表
        """
        results = []
        
        try:
            # 查找报价元素
            quote_elements = await page.query_selector_all(self.selectors["quote_elements"])
            
            if not quote_elements:
                self.logger.debug("未找到报价元素")
                return results
            
            for element in quote_elements[:10]:  # 只处理前10个元素
                try:
                    # 尝试提取报价信息
                    quote_data = await self._extract_quote_element(element)
                    if quote_data:
                        results.append(quote_data)
                        
                except Exception as e:
                    self.logger.debug(f"解析报价元素失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析报价数据失败: {e}")
        
        return results
    
    async def _extract_quote_element(self, element) -> Optional[GoldPriceData]:
        """
        提取报价元素数据
        
        Args:
            element: 报价元素
            
        Returns:
            解析后的数据对象，失败时返回None
        """
        try:
            # 尝试提取名称
            name_element = await element.query_selector(".name, .title, h3, h4")
            name = await name_element.inner_text() if name_element else ""
            
            # 尝试提取价格
            price_element = await element.query_selector(".price, .value, .current")
            price_text = await price_element.inner_text() if price_element else "0"
            
            # 尝试提取涨跌
            change_element = await element.query_selector(".change, .up, .down, .percent")
            change_text = await change_element.inner_text() if change_element else "0"
            
            # 清理名称
            name = name.strip()
            
            # 匹配目标产品
            matched_product = self._match_product_name(name)
            if not matched_product:
                return None
            
            # 获取产品配置
            product_config = self.product_mapping[matched_product]
            
            # 创建数据对象
            gold_data = self.create_gold_data(
                symbol=matched_product,
                price=price_text,
                change=change_text,
                currency=product_config["currency"]
            )
            
            if gold_data:
                gold_data.source = "sina_quote"
                
            return gold_data
            
        except Exception as e:
            self.logger.error(f"提取报价元素数据失败: {e}")
            return None
    
    def _match_product_name(self, name: str) -> Optional[str]:
        """
        匹配产品名称（包括别名）
        
        Args:
            name: 原始产品名称
            
        Returns:
            匹配的标准产品名称，未匹配时返回None
        """
        if not name:
            return None
        
        name = name.strip()
        
        # 直接匹配
        if name in self.target_products:
            return name
        
        # 别名匹配
        for product, config in self.product_mapping.items():
            if name in config.get("symbol_alt", []):
                return product
            
            # 模糊匹配
            if any(alt in name for alt in config.get("symbol_alt", [])):
                return product
        
        return None
    
    def _deduplicate_and_sort(self, data_list: List[GoldPriceData]) -> List[GoldPriceData]:
        """
        去重和排序数据
        
        Args:
            data_list: 原始数据列表
            
        Returns:
            去重排序后的数据列表
        """
        if not data_list:
            return []
        
        # 按产品名称分组
        grouped_data = {}
        for data in data_list:
            symbol = data.symbol
            if symbol not in grouped_data:
                grouped_data[symbol] = []
            grouped_data[symbol].append(data)
        
        # 每个产品只保留一条最优数据
        results = []
        for symbol, items in grouped_data.items():
            if len(items) == 1:
                results.append(items[0])
            else:
                # 选择优先级最高的数据源
                best_item = min(items, key=lambda x: self._get_source_priority(x.source))
                results.append(best_item)
        
        # 按产品优先级排序
        results.sort(key=lambda x: self.product_mapping.get(x.symbol, {"priority": 99})["priority"])
        
        return results
    
    def _get_source_priority(self, source: str) -> int:
        """
        获取数据源优先级
        
        Args:
            source: 数据源标识
            
        Returns:
            优先级数值（越小优先级越高）
        """
        if "quote" in source:
            return 1  # 实时报价优先级最高
        elif "table_0" in source:
            return 2  # 第一个表格优先级次之
        elif "table" in source:
            return 3  # 其他表格
        else:
            return 99  # 未知来源优先级最低
    
    async def test_connection(self, page: Page) -> bool:
        """
        测试连接是否正常
        
        Args:
            page: Playwright页面对象
            
        Returns:
            连接是否成功
        """
        try:
            await page.goto(self.base_url, timeout=10000)
            await page.wait_for_selector("title", timeout=5000)
            title = await page.title()
            
            if "新浪财经" in title or "新浪网" in title:
                self.logger.info("新浪财经连接测试成功")
                return True
            else:
                self.logger.warning(f"新浪财经页面标题异常: {title}")
                return False
                
        except Exception as e:
            self.logger.error(f"新浪财经连接测试失败: {e}")
            return False
    
    def get_supported_products(self) -> List[str]:
        """
        获取支持的产品列表
        
        Returns:
            支持的产品名称列表
        """
        return self.target_products.copy()
    
    def get_parser_config(self) -> dict:
        """
        获取解析器配置信息
        
        Returns:
            配置信息字典
        """
        config = self.get_parser_info()
        config.update({
            "data_url": self.data_url,
            "target_products": self.target_products,
            "product_mapping": self.product_mapping,
            "selectors": self.selectors,
            "update_frequency": "realtime",
            "data_format": "table_structured"
        })
        return config


# 导出解析器类
__all__ = ['SinaParser']