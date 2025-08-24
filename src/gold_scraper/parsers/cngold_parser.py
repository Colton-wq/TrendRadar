#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金投网数据解析器
专门处理金投网的黄金价格数据提取和解析
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


class CngoldParser(BaseParser):
    """金投网解析器"""
    
    def __init__(self):
        super().__init__("Cngold", "https://gold.cngold.org/")
        
        # 金投网特定配置
        self.target_products = [
            "黄金T+D", "现货黄金", "黄金9999", 
            "纸黄金(人民币)", "纸黄金(美元)",
            "白银T+D", "现货白银"
        ]
        
        # CSS选择器配置
        self.selectors = {
            "gold_tables": "table",
            "table_by_index": {
                "gold_td": 0,      # 黄金T+D表格
                "spot_gold": 2,    # 现货黄金表格
                "paper_gold": 1,   # 纸黄金表格
                "physical_gold": 4, # 实物黄金表格
                "bank_gold": 5     # 银行黄金表格
            },
            "cells": {
                "name": "td:nth-child(1)",
                "price": "td:nth-child(2)",
                "change": "td:nth-child(3)",
                "buy_price": "td:nth-child(4)",
                "sell_price": "td:nth-child(5)"
            },
            "market_ticker": ".hq-list li",
            "price_elements": ".price, .value, td:nth-child(2)",
            "change_elements": ".change, .up, .down, td:nth-child(3)"
        }
        
        # 产品映射配置
        self.product_mapping = {
            "黄金T+D": {"currency": "CNY", "priority": 1},
            "现货黄金": {"currency": "USD", "priority": 2},
            "黄金9999": {"currency": "CNY", "priority": 3},
            "纸黄金(人民币)": {"currency": "CNY", "priority": 4},
            "纸黄金(美元)": {"currency": "USD", "priority": 5},
            "白银T+D": {"currency": "CNY", "priority": 6},
            "现货白银": {"currency": "USD", "priority": 7}
        }
    
    async def parse_data(self, page: Page) -> List[GoldPriceData]:
        """
        解析金投网页面数据
        
        Args:
            page: Playwright页面对象
            
        Returns:
            解析后的黄金价格数据列表
        """
        if not page:
            self.logger.error("页面对象为空")
            return []
        
        try:
            self.logger.info(f"访问金投网页面: {self.base_url}")
            await page.goto(self.base_url, wait_until="networkidle", timeout=30000)
            
            # 等待表格加载
            await page.wait_for_selector("table", timeout=15000)
            
            # 获取所有表格
            tables = await page.query_selector_all(self.selectors["gold_tables"])
            
            if not tables:
                self.logger.warning("未找到数据表格")
                return []
            
            results = []
            
            # 解析表格数据
            table_results = await self._parse_tables(tables)
            results.extend(table_results)
            
            # 解析行情播报数据（如果存在）
            ticker_results = await self._parse_market_ticker(page)
            results.extend(ticker_results)
            
            # 去重和排序
            results = self._deduplicate_and_sort(results)
            
            self.logger.info(f"金投网解析完成，获取 {len(results)} 条有效数据")
            return results
            
        except Exception as e:
            self.logger.error(f"金投网页面解析失败: {e}")
            return []
    
    async def _parse_tables(self, tables: List) -> List[GoldPriceData]:
        """
        解析表格数据
        
        Args:
            tables: 表格元素列表
            
        Returns:
            解析后的数据列表
        """
        results = []
        
        # 只处理前8个表格，避免处理无关表格
        for table_index, table in enumerate(tables[:8]):
            try:
                self.logger.debug(f"解析表格 {table_index}")
                
                # 获取表格行
                rows = await table.query_selector_all("tbody tr, tr")
                
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
            
            if len(cells) < 3:
                return None
            
            # 提取基础数据
            name = await cells[0].inner_text() if len(cells) > 0 else ""
            price_text = await cells[1].inner_text() if len(cells) > 1 else "0"
            change_text = await cells[2].inner_text() if len(cells) > 2 else "0"
            buy_price_text = await cells[3].inner_text() if len(cells) > 3 else "0"
            sell_price_text = await cells[4].inner_text() if len(cells) > 4 else "0"
            
            # 清理产品名称
            name = name.strip()
            
            # 过滤目标产品
            if name not in self.target_products:
                return None
            
            # 获取产品配置
            product_config = self.product_mapping.get(name, {"currency": "CNY", "priority": 99})
            
            # 创建数据对象
            gold_data = self.create_gold_data(
                symbol=name,
                price=price_text,
                change=change_text,
                currency=product_config["currency"],
                buy_price=buy_price_text,
                sell_price=sell_price_text
            )
            
            if gold_data:
                # 添加额外信息
                gold_data.source = f"cngold_table_{table_index}"
                self.logger.debug(f"成功解析金投网数据: {name} = {gold_data.price}")
                
            return gold_data
            
        except Exception as e:
            self.logger.error(f"提取表格行数据失败: {e}")
            return None
    
    async def _parse_market_ticker(self, page: Page) -> List[GoldPriceData]:
        """
        解析行情播报数据
        
        Args:
            page: Playwright页面对象
            
        Returns:
            解析后的数据列表
        """
        results = []
        
        try:
            # 查找行情播报元素
            ticker_elements = await page.query_selector_all(self.selectors["market_ticker"])
            
            if not ticker_elements:
                self.logger.debug("未找到行情播报元素")
                return results
            
            for element in ticker_elements[:10]:  # 只处理前10个元素
                try:
                    # 提取名称
                    name_element = await element.query_selector("a, .name")
                    name = await name_element.inner_text() if name_element else ""
                    
                    # 提取价格
                    price_element = await element.query_selector(".price, .value")
                    price_text = await price_element.inner_text() if price_element else "0"
                    
                    # 提取涨跌
                    change_element = await element.query_selector(".change, .up, .down")
                    change_text = await change_element.inner_text() if change_element else "0"
                    
                    # 清理名称
                    name = name.strip()
                    
                    # 过滤目标产品
                    if name not in self.target_products:
                        continue
                    
                    # 获取产品配置
                    product_config = self.product_mapping.get(name, {"currency": "CNY", "priority": 99})
                    
                    # 创建数据对象
                    gold_data = self.create_gold_data(
                        symbol=name,
                        price=price_text,
                        change=change_text,
                        currency=product_config["currency"]
                    )
                    
                    if gold_data:
                        gold_data.source = "cngold_ticker"
                        results.append(gold_data)
                        
                except Exception as e:
                    self.logger.debug(f"解析行情播报元素失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析行情播报失败: {e}")
        
        return results
    
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
        if "ticker" in source:
            return 1  # 行情播报优先级最高
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
            
            if "金投网" in title or "黄金" in title:
                self.logger.info("金投网连接测试成功")
                return True
            else:
                self.logger.warning(f"金投网页面标题异常: {title}")
                return False
                
        except Exception as e:
            self.logger.error(f"金投网连接测试失败: {e}")
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
            "target_products": self.target_products,
            "product_mapping": self.product_mapping,
            "selectors": self.selectors,
            "update_frequency": "realtime",
            "data_format": "multi_table"
        })
        return config


# 导出解析器类
__all__ = ['CngoldParser']