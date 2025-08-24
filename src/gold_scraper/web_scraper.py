#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金价格网页爬虫核心模块
为TrendRadar系统提供备用黄金价格数据源
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    async_playwright = None
    Browser = None
    Page = None

# 导入专用解析器
try:
    from .parsers import SGEParser, CngoldParser, SinaParser, GoldPriceData
except ImportError:
    # 兼容性导入
    try:
        from parsers import SGEParser, CngoldParser, SinaParser, GoldPriceData
    except ImportError:
        SGEParser = None
        CngoldParser = None
        SinaParser = None
        GoldPriceData = None


class AntiDetectionManager:
    """反爬虫检测管理器"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    
    @classmethod
    def get_random_user_agent(cls) -> str:
        """获取随机User-Agent"""
        return random.choice(cls.USER_AGENTS)
    
    @classmethod
    def get_random_delay(cls, min_delay: int = 5, max_delay: int = 10) -> float:
        """获取随机延迟时间（秒）"""
        return random.uniform(min_delay, max_delay)
    
    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }


class WebScrapingManager:
    """网页爬虫管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger("WebScrapingManager")
        
        # 初始化解析器
        self.parsers = []
        if SGEParser:
            self.parsers.append(SGEParser())
        if CngoldParser:
            self.parsers.append(CngoldParser())
        if SinaParser:
            self.parsers.append(SinaParser())
        
        if not self.parsers:
            self.logger.error("未找到可用的解析器")
        
        # 配置信息
        self.config = {
            "max_concurrent_parsers": 2,  # 最大并发解析器数量
            "parser_timeout": 60,         # 单个解析器超时时间（秒）
            "retry_attempts": 2,          # 重试次数
            "delay_between_parsers": (5, 10)  # 解析器间延迟范围
        }
        
    async def scrape_all_sources(self) -> List[GoldPriceData]:
        """
        爬取所有数据源
        
        Returns:
            所有解析器获取的数据列表
        """
        if not async_playwright:
            self.logger.error("Playwright未安装，无法使用网页爬虫功能")
            return []
        
        if not self.parsers:
            self.logger.error("没有可用的解析器")
            return []
        
        all_results = []
        
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions'
                ]
            )
            
            try:
                # 并发处理解析器（限制并发数量）
                semaphore = asyncio.Semaphore(self.config["max_concurrent_parsers"])
                tasks = []
                
                for parser in self.parsers:
                    task = self._scrape_with_parser(browser, parser, semaphore)
                    tasks.append(task)
                
                # 等待所有任务完成
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"解析器 {self.parsers[i].name} 执行异常: {result}")
                    elif isinstance(result, list):
                        all_results.extend(result)
                        self.logger.info(f"解析器 {self.parsers[i].name} 获取 {len(result)} 条数据")
                    
            finally:
                await browser.close()
        
        # 数据去重和验证
        validated_results = self._validate_and_deduplicate(all_results)
        
        self.logger.info(f"所有数据源爬取完成，共获取 {len(validated_results)} 条有效数据")
        return validated_results
    
    async def _scrape_with_parser(
        self, 
        browser: Browser, 
        parser, 
        semaphore: asyncio.Semaphore
    ) -> List[GoldPriceData]:
        """
        使用指定解析器爬取数据
        
        Args:
            browser: 浏览器实例
            parser: 解析器实例
            semaphore: 并发控制信号量
            
        Returns:
            解析器获取的数据列表
        """
        async with semaphore:
            for attempt in range(self.config["retry_attempts"] + 1):
                try:
                    # 创建新页面
                    page = await browser.new_page()
                    
                    try:
                        # 设置反爬虫措施
                        await page.set_user_agent(AntiDetectionManager.get_random_user_agent())
                        await page.set_extra_http_headers(AntiDetectionManager.get_headers())
                        
                        # 设置超时
                        page.set_default_timeout(self.config["parser_timeout"] * 1000)
                        
                        # 爬取数据
                        self.logger.info(f"开始爬取 {parser.name} (尝试 {attempt + 1})")
                        
                        results = await asyncio.wait_for(
                            parser.parse_data(page),
                            timeout=self.config["parser_timeout"]
                        )
                        
                        if results:
                            self.logger.info(f"{parser.name} 爬取成功，获取 {len(results)} 条数据")
                            return results
                        else:
                            self.logger.warning(f"{parser.name} 未获取到数据")
                            
                    finally:
                        await page.close()
                        
                    # 随机延迟
                    if attempt < self.config["retry_attempts"]:
                        delay = AntiDetectionManager.get_random_delay(*self.config["delay_between_parsers"])
                        await asyncio.sleep(delay)
                        
                except asyncio.TimeoutError:
                    self.logger.warning(f"{parser.name} 超时 (尝试 {attempt + 1})")
                except Exception as e:
                    self.logger.error(f"{parser.name} 爬取失败 (尝试 {attempt + 1}): {e}")
                    
                if attempt < self.config["retry_attempts"]:
                    # 重试前等待
                    retry_delay = random.uniform(2, 5)
                    await asyncio.sleep(retry_delay)
            
            self.logger.error(f"{parser.name} 所有尝试均失败")
            return []
    
    def _validate_and_deduplicate(self, data_list: List[GoldPriceData]) -> List[GoldPriceData]:
        """
        验证和去重数据
        
        Args:
            data_list: 原始数据列表
            
        Returns:
            验证和去重后的数据列表
        """
        if not data_list:
            return []
        
        # 按 (source, symbol) 分组去重
        unique_data = {}
        for data in data_list:
            if not isinstance(data, GoldPriceData):
                continue
                
            # 基本验证
            if not data.symbol or data.price <= 0:
                self.logger.warning(f"跳过无效数据: {data}")
                continue
            
            key = (data.source, data.symbol)
            if key not in unique_data:
                unique_data[key] = data
            else:
                # 保留时间戳更新的数据
                if data.timestamp > unique_data[key].timestamp:
                    unique_data[key] = data
        
        results = list(unique_data.values())
        
        # 按数据源和优先级排序
        results.sort(key=lambda x: (x.source, x.symbol))
        
        self.logger.info(f"数据验证完成，去重后保留 {len(results)} 条数据")
        return results
    
    def format_for_trendradar(self, gold_data_list: List[GoldPriceData]) -> Dict[str, Any]:
        """
        格式化数据以兼容TrendRadar现有接口
        
        Args:
            gold_data_list: 黄金价格数据列表
            
        Returns:
            TrendRadar兼容格式的数据字典
        """
        if not gold_data_list:
            return {}
        
        # 按数据源分组
        grouped_data = {}
        for data in gold_data_list:
            source = data.source
            if source not in grouped_data:
                grouped_data[source] = []
            
            # 转换为TrendRadar兼容格式
            item = {
                "title": f"{data.symbol} {data.price} {data.change_percent}",
                "price": data.price,
                "change": data.change,
                "change_percent": data.change_percent,
                "symbol": data.symbol,
                "currency": data.currency,
                "timestamp": data.timestamp,
                "url": "",  # 爬虫数据没有URL
                "mobileUrl": ""
            }
            
            # 添加可选字段
            if hasattr(data, 'high') and data.high:
                item["high"] = data.high
            if hasattr(data, 'low') and data.low:
                item["low"] = data.low
            if hasattr(data, 'open_price') and data.open_price:
                item["open"] = data.open_price
            if hasattr(data, 'volume') and data.volume:
                item["volume"] = data.volume
            if hasattr(data, 'buy_price') and data.buy_price:
                item["buy_price"] = data.buy_price
            if hasattr(data, 'sell_price') and data.sell_price:
                item["sell_price"] = data.sell_price
                
            grouped_data[source].append(item)
        
        return grouped_data
    
    async def test_all_parsers(self) -> Dict[str, bool]:
        """
        测试所有解析器的连接状态
        
        Returns:
            解析器名称到连接状态的映射
        """
        if not async_playwright:
            self.logger.error("Playwright未安装，无法测试解析器")
            return {}
        
        results = {}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            try:
                for parser in self.parsers:
                    try:
                        page = await browser.new_page()
                        await page.set_user_agent(AntiDetectionManager.get_random_user_agent())
                        
                        # 测试连接
                        if hasattr(parser, 'test_connection'):
                            success = await parser.test_connection(page)
                        else:
                            # 简单测试：尝试访问基础URL
                            await page.goto(parser.base_url, timeout=10000)
                            success = True
                        
                        results[parser.name] = success
                        await page.close()
                        
                    except Exception as e:
                        self.logger.error(f"测试 {parser.name} 连接失败: {e}")
                        results[parser.name] = False
                        
            finally:
                await browser.close()
        
        return results
    
    def get_parser_info(self) -> List[Dict[str, Any]]:
        """
        获取所有解析器的信息
        
        Returns:
            解析器信息列表
        """
        info_list = []
        for parser in self.parsers:
            if hasattr(parser, 'get_parser_config'):
                info = parser.get_parser_config()
            else:
                info = {
                    "name": parser.name,
                    "base_url": parser.base_url
                }
            info_list.append(info)
        
        return info_list


# 导出主要类和函数
__all__ = [
    'WebScrapingManager',
    'AntiDetectionManager'
]

# 兼容性导出
if GoldPriceData:
    __all__.append('GoldPriceData')