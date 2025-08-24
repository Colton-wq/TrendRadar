#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金价格网站解析器模块
为不同的黄金价格网站提供专用的数据解析器
"""

from .base_parser import BaseParser
from .sge_parser import SGEParser
from .cngold_parser import CngoldParser
from .sina_parser import SinaParser

__version__ = "1.0.0"
__author__ = "TrendRadar Team"

__all__ = [
    'BaseParser',
    'SGEParser', 
    'CngoldParser',
    'SinaParser'
]