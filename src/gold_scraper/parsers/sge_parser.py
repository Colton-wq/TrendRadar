#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海黄金交易所数据解析器
专门处理SGE网站的黄金价格数据提取和解析
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Any
from urllib.parse import urljoin

try:
    from playwright.async_api import Page
except ImportError:
    Page = None

from .base_parser import BaseParser, GoldPriceData


class SGEParser(BaseParser):
    """上海黄金交易所解析器"""
    
    def __init__(self):
        super().__init__("SGE", "https://www.sge.com.cn/")
        
        # SGE特定配置
        self.data_url = "https://www.sge.com.cn/sjzx/quotation_daily_new"
        self.target_contracts = [
            "Au99.99", "Au(T+D)", "mAu(T+D)", 
            "Au99.95", "Au100g", "Ag99.9", "Ag(T+D)"
        ]
        
        # CSS选择器配置
        self.selectors = {
            "table": "table",
            "data_rows": "table tbody tr:not(:first-child)",
            "cells": {
                "date": "td:nth-child(1)",
                "contract": "td:nth-child(2)",
                "open_price": "td:nth-child(3)",
                "high_price": "td:nth-child(4)",
                "low_price": "td:nth-child(5)",
                "close_price": "td:nth-child(6)",
                "change": "td:nth-child(7)",
                "change_percent": "td:nth-child(8)",
                "avg_price": "td:nth-child(9)",
                "volume": "td:nth-child(10)",
                "amount": "td:nth-child(11)"
            }
        }
    
    async def parse_data(self, page: Page) -> List[GoldPriceData]:
        """
        解析SGE页面数据
        
        Args:
            page: Playwright页面对象
            
        Returns:
            解析后的黄金价格数据列表
        """
        if not page:
            self.logger.error("页面对象为空")
            return []
        
        try:
            # 构建当日数据URL
            today = datetime.now().strftime("%Y-%m-%d")
            url = f"{self.data_url}?start_date={today}&end_date={today}"
            
            self.logger.info(f"访问SGE数据页面: {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 等待表格加载
            await page.wait_for_selector(self.selectors["table"], timeout=15000)
            
            # 获取所有数据行
            rows = await page.query_selector_all(self.selectors["data_rows"])
            
            if not rows:
                self.logger.warning("未找到数据行")
                return []
            
            results = []
            for row_index, row in enumerate(rows):
                try:
                    # 提取单行数据
                    row_data = await self._extract_row_data(row)
                    if row_data:
                        results.append(row_data)
                        
                except Exception as e:
                    self.logger.error(f"解析第 {row_index + 1} 行数据失败: {e}")
                    continue
            
            self.logger.info(f"SGE解析完成，获取 {len(results)} 条有效数据")
            return results
            
        except Exception as e:
            self.logger.error(f"SGE页面解析失败: {e}")
            return []
    
    async def _extract_row_data(self, row) -> Optional[GoldPriceData]:
        """
        提取单行数据
        
        Args:
            row: 表格行元素
            
        Returns:
            解析后的数据对象，失败时返回None
        """
        try:
            # 获取所有单元格
            cells = await row.query_selector_all("td")
            
            if len(cells) < 8:
                self.logger.warning(f"数据行单元格数量不足: {len(cells)}")
                return None
            
            # 提取基础数据
            date_text = await cells[0].inner_text() if len(cells) > 0 else ""
            contract = await cells[1].inner_text() if len(cells) > 1 else ""
            open_price_text = await cells[2].inner_text() if len(cells) > 2 else "0"
            high_price_text = await cells[3].inner_text() if len(cells) > 3 else "0"
            low_price_text = await cells[4].inner_text() if len(cells) > 4 else "0"
            close_price_text = await cells[5].inner_text() if len(cells) > 5 else "0"
            change_text = await cells[6].inner_text() if len(cells) > 6 else "0"
            change_percent_text = await cells[7].inner_text() if len(cells) > 7 else "0.00%"
            
            # 可选数据
            avg_price_text = await cells[8].inner_text() if len(cells) > 8 else "0"
            volume_text = await cells[9].inner_text() if len(cells) > 9 else ""
            amount_text = await cells[10].inner_text() if len(cells) > 10 else ""
            
            # 过滤目标合约
            contract = contract.strip()
            if contract not in self.target_contracts:
                return None
            
            # 处理涨跌数据
            combined_change = f"{change_text} {change_percent_text}"
            
            # 创建数据对象
            gold_data = self.create_gold_data(
                symbol=contract,
                price=close_price_text,
                change=combined_change,
                change_percent=change_percent_text,
                currency="CNY",
                high=high_price_text,
                low=low_price_text,
                open_price=open_price_text,
                volume=volume_text,
                timestamp=self._parse_sge_date(date_text)
            )
            
            if gold_data:
                self.logger.debug(f"成功解析SGE数据: {contract} = {gold_data.price}")
                
            return gold_data
            
        except Exception as e:
            self.logger.error(f"提取行数据失败: {e}")
            return None
    
    def _parse_sge_date(self, date_text: str) -> str:
        """
        解析SGE日期格式
        
        Args:
            date_text: 原始日期文本
            
        Returns:
            ISO格式时间戳
        """
        if not date_text or date_text.strip() in self.invalid_values:
            return self.format_timestamp()
        
        try:
            # SGE日期格式通常为 YYYY-MM-DD
            date_text = date_text.strip()
            if len(date_text) == 10 and date_text.count('-') == 2:
                # 添加当前时间
                current_time = datetime.now().strftime("%H:%M:%S")
                full_datetime = f"{date_text} {current_time}"
                dt = datetime.strptime(full_datetime, "%Y-%m-%d %H:%M:%S")
                return dt.isoformat()
            else:
                self.logger.warning(f"SGE日期格式异常: {date_text}")
                return self.format_timestamp()
                
        except Exception as e:
            self.logger.error(f"SGE日期解析失败: {date_text} -> {e}")
            return self.format_timestamp()
    
    def get_data_url(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """
        构建数据获取URL
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            完整的数据URL
        """
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if not end_date:
            end_date = start_date
            
        return f"{self.data_url}?start_date={start_date}&end_date={end_date}"
    
    def get_supported_contracts(self) -> List[str]:
        """
        获取支持的合约列表
        
        Returns:
            支持的合约名称列表
        """
        return self.target_contracts.copy()
    
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
            
            if "上海黄金交易所" in title or "SGE" in title:
                self.logger.info("SGE连接测试成功")
                return True
            else:
                self.logger.warning(f"SGE页面标题异常: {title}")
                return False
                
        except Exception as e:
            self.logger.error(f"SGE连接测试失败: {e}")
            return False
    
    def get_parser_config(self) -> dict:
        """
        获取解析器配置信息
        
        Returns:
            配置信息字典
        """
        config = self.get_parser_info()
        config.update({
            "data_url": self.data_url,
            "target_contracts": self.target_contracts,
            "selectors": self.selectors,
            "update_frequency": "workdays_realtime",
            "data_format": "table_structured"
        })
        return config


# 导出解析器类
__all__ = ['SGEParser']