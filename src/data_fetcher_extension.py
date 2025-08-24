#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataFetcher类扩展模块
为TrendRadar的DataFetcher类添加黄金价格爬虫功能
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Union

# 导入黄金爬虫模块
try:
    from src.gold_scraper import WebScrapingManager, GoldPriceData
except ImportError:
    WebScrapingManager = None
    GoldPriceData = None


class DataFetcherExtension:
    """DataFetcher类的扩展功能"""
    
    def __init__(self, data_fetcher_instance):
        """
        初始化扩展
        
        Args:
            data_fetcher_instance: 原始DataFetcher实例
        """
        self.data_fetcher = data_fetcher_instance
        self.logger = logging.getLogger("DataFetcherExtension")
        self.web_scraping_manager = None
        
        # 初始化网页爬虫管理器
        if WebScrapingManager:
            self.web_scraping_manager = WebScrapingManager()
        else:
            self.logger.warning("黄金爬虫模块未安装，网页爬虫功能不可用")
    
    async def fetch_gold_price_web(
        self,
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5
    ) -> Tuple[Optional[str], str, str]:
        """
        从网页爬取黄金价格数据
        
        Args:
            max_retries: 最大重试次数
            min_retry_wait: 最小重试等待时间
            max_retry_wait: 最大重试等待时间
            
        Returns:
            Tuple[数据JSON字符串, 数据源ID, 数据源别名]
        """
        if not self.web_scraping_manager:
            self.logger.error("网页爬虫管理器未初始化")
            return None, "gold_web_scraper", "黄金网页爬虫"
        
        retries = 0
        while retries <= max_retries:
            try:
                self.logger.info(f"开始爬取黄金价格数据（第 {retries + 1} 次尝试）")
                
                # 爬取所有数据源
                gold_data_list = await self.web_scraping_manager.scrape_all_sources()
                
                if not gold_data_list:
                    raise ValueError("未获取到任何黄金价格数据")
                
                # 格式化数据以兼容TrendRadar
                formatted_data = self.web_scraping_manager.format_for_trendradar(gold_data_list)
                
                # 构建响应数据结构，模拟API响应格式
                response_data = {
                    "status": "success",
                    "source": "web_scraper",
                    "timestamp": gold_data_list[0].timestamp if gold_data_list else "",
                    "items": []
                }
                
                # 将格式化的数据转换为items格式
                for source, items in formatted_data.items():
                    for item in items:
                        response_data["items"].append({
                            "title": item["title"],
                            "url": "",  # 爬虫数据没有URL
                            "mobileUrl": "",
                            "source": source,
                            "price": item["price"],
                            "change": item["change"],
                            "change_percent": item["change_percent"],
                            "symbol": item["symbol"],
                            "currency": item["currency"],
                            "timestamp": item["timestamp"]
                        })
                
                data_text = json.dumps(response_data, ensure_ascii=False, indent=2)
                
                self.logger.info(f"黄金价格爬取成功，获取 {len(response_data['items'])} 条数据")
                return data_text, "gold_web_scraper", "黄金网页爬虫"
                
            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    import random
                    base_wait = random.uniform(min_retry_wait, max_retry_wait)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    
                    self.logger.warning(f"黄金价格爬取失败: {e}. {wait_time:.2f}秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"黄金价格爬取最终失败: {e}")
                    return None, "gold_web_scraper", "黄金网页爬虫"
        
        return None, "gold_web_scraper", "黄金网页爬虫"
    
    def fetch_gold_price_web_sync(
        self,
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5
    ) -> Tuple[Optional[str], str, str]:
        """
        同步版本的黄金价格爬取方法
        
        Args:
            max_retries: 最大重试次数
            min_retry_wait: 最小重试等待时间
            max_retry_wait: 最大重试等待时间
            
        Returns:
            Tuple[数据JSON字符串, 数据源ID, 数据源别名]
        """
        try:
            # 在新的事件循环中运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.fetch_gold_price_web(max_retries, min_retry_wait, max_retry_wait)
                )
            finally:
                loop.close()
        except Exception as e:
            self.logger.error(f"同步黄金价格爬取失败: {e}")
            return None, "gold_web_scraper", "黄金网页爬虫"
    
    def crawl_gold_websites(
        self,
        request_interval: int = 5000
    ) -> Tuple[Dict, Dict, List]:
        """
        爬取黄金价格网站数据，兼容现有crawl_websites接口
        
        Args:
            request_interval: 请求间隔（毫秒）
            
        Returns:
            Tuple[结果字典, ID到名称映射, 失败ID列表]
        """
        results = {}
        id_to_name = {}
        failed_ids = []
        
        # 设置ID和名称映射
        gold_id = "gold_web_scraper"
        gold_name = "黄金网页爬虫"
        id_to_name[gold_id] = gold_name
        
        try:
            # 爬取黄金价格数据
            response, _, _ = self.fetch_gold_price_web_sync()
            
            if response:
                try:
                    data = json.loads(response)
                    results[gold_id] = {}
                    
                    # 处理爬取的数据项
                    for index, item in enumerate(data.get("items", []), 1):
                        title = item["title"]
                        
                        if title in results[gold_id]:
                            results[gold_id][title]["ranks"].append(index)
                        else:
                            results[gold_id][title] = {
                                "ranks": [index],
                                "url": item.get("url", ""),
                                "mobileUrl": item.get("mobileUrl", ""),
                                "price": item.get("price", 0),
                                "change": item.get("change", 0),
                                "change_percent": item.get("change_percent", "0.00%"),
                                "symbol": item.get("symbol", ""),
                                "currency": item.get("currency", "CNY"),
                                "source": item.get("source", "unknown")
                            }
                            
                except json.JSONDecodeError:
                    self.logger.error("解析黄金价格响应失败")
                    failed_ids.append(gold_id)
                except Exception as e:
                    self.logger.error(f"处理黄金价格数据出错: {e}")
                    failed_ids.append(gold_id)
            else:
                failed_ids.append(gold_id)
                
        except Exception as e:
            self.logger.error(f"黄金价格爬取异常: {e}")
            failed_ids.append(gold_id)
        
        # 添加请求间隔延迟
        if request_interval > 0:
            time.sleep(request_interval / 1000.0)
        
        return results, id_to_name, failed_ids
    
    def is_web_scraping_available(self) -> bool:
        """检查网页爬虫功能是否可用"""
        return self.web_scraping_manager is not None
    
    def get_supported_gold_sources(self) -> List[str]:
        """获取支持的黄金数据源列表"""
        if not self.web_scraping_manager:
            return []
        
        return [scraper.name for scraper in self.web_scraping_manager.scrapers]


def extend_data_fetcher(data_fetcher_instance):
    """
    为DataFetcher实例添加黄金爬虫功能
    
    Args:
        data_fetcher_instance: DataFetcher实例
        
    Returns:
        扩展后的DataFetcher实例
    """
    # 创建扩展实例
    extension = DataFetcherExtension(data_fetcher_instance)
    
    # 将扩展方法绑定到原实例
    data_fetcher_instance.fetch_gold_price_web = extension.fetch_gold_price_web_sync
    data_fetcher_instance.crawl_gold_websites = extension.crawl_gold_websites
    data_fetcher_instance.is_web_scraping_available = extension.is_web_scraping_available
    data_fetcher_instance.get_supported_gold_sources = extension.get_supported_gold_sources
    
    # 添加扩展实例的引用
    data_fetcher_instance._gold_extension = extension
    
    return data_fetcher_instance


# 导出主要函数
__all__ = [
    'DataFetcherExtension',
    'extend_data_fetcher'
]