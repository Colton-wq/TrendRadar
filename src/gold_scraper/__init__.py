#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金价格爬虫模块
为TrendRadar系统提供备用黄金价格数据源
"""

from .web_scraper import (
    GoldPriceData,
    WebScrapingManager,
    AntiDetectionManager,
    SGEScraper,
    CngoldScraper
)

__version__ = "1.0.0"
__author__ = "TrendRadar Team"

__all__ = [
    'GoldPriceData',
    'WebScrapingManager', 
    'AntiDetectionManager',
    'SGEScraper',
    'CngoldScraper'
]