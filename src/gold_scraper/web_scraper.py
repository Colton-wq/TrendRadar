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
from dataclasses import dataclass
import logging

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    async_playwright = None
    Browser = None
    Page = None


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


class GoldPriceScraper:
    """黄金价格爬虫基类"""
    
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.logger = logging.getLogger(f"GoldScraper.{name}")
        
    async def scrape(self, page: Page) -> List[GoldPriceData]:
        """抽象方法：爬取数据"""
        raise NotImplementedError("Subclasses must implement scrape method")
    
    def clean_price_text(self, text: str) -> float:
        """清理价格文本，转换为浮点数"""
        if not text or text in ["--", "N/A", ""]:
            return 0.0
        
        # 移除千分位分隔符和其他字符
        cleaned = text.replace(",", "").replace("￥", "").replace("$", "").strip()
        
        try:
            return float(cleaned)
        except ValueError:
            self.logger.warning(f"无法解析价格: {text}")
            return 0.0
    
    def clean_change_text(self, text: str) -> Tuple[float, str]:
        """清理涨跌数据，返回涨跌额和涨跌幅"""
        if not text or text in ["--", "N/A", ""]:
            return 0.0, "0.00%"
        
        # 提取数值部分
        import re
        
        # 匹配涨跌额（可能包含正负号和箭头）
        change_match = re.search(r'([+-]?\d+\.?\d*)', text)
        change = float(change_match.group(1)) if change_match else 0.0
        
        # 匹配涨跌幅
        percent_match = re.search(r'([+-]?\d+\.?\d*)%', text)
        if percent_match:
            percent = f"{percent_match.group(1)}%"
        else:
            percent = "0.00%"
        
        return change, percent


class SGEScraper(GoldPriceScraper):
    """上海黄金交易所爬虫"""
    
    def __init__(self):
        super().__init__("SGE", "https://www.sge.com.cn/")
        self.data_url = "https://www.sge.com.cn/sjzx/quotation_daily_new"
        
    async def scrape(self, page: Page) -> List[GoldPriceData]:
        """爬取上海黄金交易所数据"""
        try:
            # 构建当日数据URL
            today = datetime.now().strftime("%Y-%m-%d")
            url = f"{self.data_url}?start_date={today}&end_date={today}"
            
            await page.goto(url, wait_until="networkidle")
            
            # 等待表格加载
            await page.wait_for_selector("table", timeout=10000)
            
            # 提取表格数据
            rows = await page.query_selector_all("table tbody tr:not(:first-child)")
            
            results = []
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) >= 8:
                    try:
                        date_text = await cells[0].inner_text()
                        contract = await cells[1].inner_text()
                        open_price = self.clean_price_text(await cells[2].inner_text())
                        high_price = self.clean_price_text(await cells[3].inner_text())
                        low_price = self.clean_price_text(await cells[4].inner_text())
                        close_price = self.clean_price_text(await cells[5].inner_text())
                        change_text = await cells[6].inner_text()
                        change_percent_text = await cells[7].inner_text()
                        
                        change, change_percent = self.clean_change_text(f"{change_text} {change_percent_text}")
                        
                        # 只处理主要黄金合约
                        if contract in ["Au99.99", "Au(T+D)", "mAu(T+D)", "Au99.95", "Au100g"]:
                            gold_data = GoldPriceData(
                                source="sge",
                                symbol=contract,
                                price=close_price,
                                change=change,
                                change_percent=change_percent,
                                timestamp=datetime.now().isoformat(),
                                currency="CNY",
                                high=high_price,
                                low=low_price,
                                open_price=open_price
                            )
                            results.append(gold_data)
                            
                    except Exception as e:
                        self.logger.error(f"解析SGE数据行失败: {e}")
                        continue
            
            self.logger.info(f"SGE爬取成功，获取 {len(results)} 条数据")
            return results
            
        except Exception as e:
            self.logger.error(f"SGE爬取失败: {e}")
            return []


class CngoldScraper(GoldPriceScraper):
    """金投网爬虫"""
    
    def __init__(self):
        super().__init__("Cngold", "https://gold.cngold.org/")
        
    async def scrape(self, page: Page) -> List[GoldPriceData]:
        """爬取金投网数据"""
        try:
            await page.goto(self.base_url, wait_until="networkidle")
            
            # 等待表格加载
            await page.wait_for_selector("table", timeout=10000)
            
            # 获取所有表格
            tables = await page.query_selector_all("table")
            
            results = []
            target_products = ["黄金T+D", "现货黄金", "黄金9999", "纸黄金(人民币)", "纸黄金(美元)"]
            
            for table_index, table in enumerate(tables[:8]):  # 只处理前8个表格
                try:
                    rows = await table.query_selector_all("tbody tr")
                    
                    for row in rows:
                        cells = await row.query_selector_all("td")
                        if len(cells) >= 3:
                            name = await cells[0].inner_text()
                            price_text = await cells[1].inner_text()
                            change_text = await cells[2].inner_text()
                            
                            if name.strip() in target_products:
                                price = self.clean_price_text(price_text)
                                change, change_percent = self.clean_change_text(change_text)
                                
                                # 判断货币类型
                                currency = "USD" if "美元" in name else "CNY"
                                
                                gold_data = GoldPriceData(
                                    source="cngold",
                                    symbol=name.strip(),
                                    price=price,
                                    change=change,
                                    change_percent=change_percent,
                                    timestamp=datetime.now().isoformat(),
                                    currency=currency
                                )
                                results.append(gold_data)
                                
                except Exception as e:
                    self.logger.error(f"解析Cngold表格 {table_index} 失败: {e}")
                    continue
            
            self.logger.info(f"Cngold爬取成功，获取 {len(results)} 条数据")
            return results
            
        except Exception as e:
            self.logger.error(f"Cngold爬取失败: {e}")
            return []


class WebScrapingManager:
    """网页爬虫管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger("WebScrapingManager")
        self.scrapers = [
            SGEScraper(),
            CngoldScraper()
        ]
        
    async def scrape_all_sources(self) -> List[GoldPriceData]:
        """爬取所有数据源"""
        if not async_playwright:
            self.logger.error("Playwright未安装，无法使用网页爬虫功能")
            return []
        
        all_results = []
        
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                for scraper in self.scrapers:
                    try:
                        # 创建新页面
                        page = await browser.new_page()
                        
                        # 设置反爬虫措施
                        await page.set_user_agent(AntiDetectionManager.get_random_user_agent())
                        await page.set_extra_http_headers(AntiDetectionManager.get_headers())
                        
                        # 爬取数据
                        self.logger.info(f"开始爬取 {scraper.name}")
                        results = await scraper.scrape(page)
                        all_results.extend(results)
                        
                        # 关闭页面
                        await page.close()
                        
                        # 随机延迟
                        delay = AntiDetectionManager.get_random_delay()
                        self.logger.info(f"{scraper.name} 爬取完成，等待 {delay:.2f} 秒")
                        await asyncio.sleep(delay)
                        
                    except Exception as e:
                        self.logger.error(f"爬取 {scraper.name} 失败: {e}")
                        continue
                        
            finally:
                await browser.close()
        
        self.logger.info(f"所有数据源爬取完成，共获取 {len(all_results)} 条数据")
        return all_results
    
    def format_for_trendradar(self, gold_data_list: List[GoldPriceData]) -> Dict[str, Any]:
        """格式化数据以兼容TrendRadar现有接口"""
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
            
            if data.high:
                item["high"] = data.high
            if data.low:
                item["low"] = data.low
            if data.open_price:
                item["open"] = data.open_price
                
            grouped_data[source].append(item)
        
        return grouped_data


# 导出主要类和函数
__all__ = [
    'GoldPriceData',
    'WebScrapingManager',
    'AntiDetectionManager',
    'SGEScraper',
    'CngoldScraper'
]