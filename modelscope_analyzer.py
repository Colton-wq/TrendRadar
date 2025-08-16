#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ModelScope AI分析模块
集成Qwen3-Coder-480B-A35B-Instruct进行GitHub项目智能分析
"""

import os
import json
import requests
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class ProjectAnalysis:
    """项目分析结果"""
    quality_score: float  # 0-1.0
    category: str
    tech_stack: List[str]
    highlights: List[str]
    concerns: List[str]
    recommendation: str
    confidence: float

class ModelScopeAnalyzer:
    """ModelScope AI分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.api_key = os.getenv('MODELSCOPE_API_KEY')
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.model = "qwen3-coder-plus"  # 使用Qwen3-Coder模型
        
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
        
        # 请求限制控制
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 最小请求间隔（秒）
    
    def _wait_for_rate_limit(self):
        """等待API限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_api_request(self, prompt: str) -> Optional[str]:
        """发起ModelScope API请求"""
        if not self.api_key:
            logger.warning("ModelScope API密钥未配置，使用本地分析")
            return None
        
        self._wait_for_rate_limit()
        
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的代码项目分析专家，擅长评估GitHub项目的质量、技术栈和发展潜力。请用中文回答。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "max_tokens": 1000,
                "temperature": 0.3
            }
        }
        
        try:
            response = self.session.post(self.base_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'output' in result and 'text' in result['output']:
                    return result['output']['text']
                else:
                    logger.error(f"API响应格式异常: {result}")
                    return None
            else:
                logger.error(f"API请求失败: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"API请求异常: {e}")
            return None
    
    def _build_analysis_prompt(self, project_data: Dict) -> str:
        """构建分析提示词"""
        prompt = f"""请分析以下GitHub项目，并提供详细评估：

项目信息：
- 名称：{project_data.get('name', '')}
- 作者：{project_data.get('owner_login', '')}
- 描述：{project_data.get('description', '')}
- 编程语言：{project_data.get('language', '')}
- Stars：{project_data.get('stars', 0)}
- Forks：{project_data.get('forks', 0)}
- 创建时间：{project_data.get('created_at', '')}
- 标签：{', '.join(project_data.get('topics', []))}
- 许可证：{project_data.get('license_name', '未知')}

请从以下维度进行分析：

1. **质量评分** (0-10分)：基于代码质量、文档完整性、社区活跃度等
2. **技术分类**：确定项目所属的技术领域
3. **技术栈识别**：列出项目使用的主要技术和框架
4. **项目亮点**：列出3个最突出的优势
5. **潜在问题**：指出可能的不足或风险点
6. **推荐理由**：一句话总结为什么值得关注

请以JSON格式返回结果：
{{
  "quality_score": 8.5,
  "category": "AI/机器学习",
  "tech_stack": ["Python", "PyTorch", "Transformers"],
  "highlights": ["创新的算法实现", "完整的文档", "活跃的社区"],
  "concerns": ["依赖较多", "文档需要改进"],
  "recommendation": "值得关注的AI工具项目",
  "confidence": 0.9
}}"""
        return prompt
    
    def analyze_project(self, project_data: Dict) -> ProjectAnalysis:
        """分析GitHub项目"""
        try:
            # 构建提示词
            prompt = self._build_analysis_prompt(project_data)
            
            # 调用AI API
            ai_response = self._make_api_request(prompt)
            
            if ai_response:
                # 解析AI响应
                return self._parse_ai_response(ai_response, project_data)
            else:
                # 使用本地分析作为后备
                return self._local_analysis(project_data)
                
        except Exception as e:
            logger.error(f"项目分析失败: {e}")
            return self._local_analysis(project_data)
    
    def _parse_ai_response(self, response: str, project_data: Dict) -> ProjectAnalysis:
        """解析AI响应"""
        try:
            # 尝试提取JSON部分
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                return ProjectAnalysis(
                    quality_score=min(result.get('quality_score', 5.0) / 10.0, 1.0),
                    category=result.get('category', '未分类'),
                    tech_stack=result.get('tech_stack', []),
                    highlights=result.get('highlights', []),
                    concerns=result.get('concerns', []),
                    recommendation=result.get('recommendation', ''),
                    confidence=result.get('confidence', 0.5)
                )
            else:
                # JSON解析失败，使用文本分析
                return self._parse_text_response(response, project_data)
                
        except json.JSONDecodeError:
            logger.warning("AI响应JSON解析失败，使用文本分析")
            return self._parse_text_response(response, project_data)
    
    def _parse_text_response(self, response: str, project_data: Dict) -> ProjectAnalysis:
        """解析文本响应"""
        # 简单的文本解析逻辑
        lines = response.split('\n')
        
        quality_score = 0.6  # 默认评分
        category = "未分类"
        tech_stack = [project_data.get('language', '')]
        highlights = []
        concerns = []
        recommendation = "AI分析项目"
        
        # 尝试从文本中提取信息
        for line in lines:
            line = line.strip()
            if '评分' in line or '分数' in line:
                # 尝试提取数字
                import re
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    score = float(numbers[0])
                    quality_score = min(score / 10.0, 1.0) if score > 1 else score
            
            elif '分类' in line or '领域' in line:
                category = line.split('：')[-1].strip() if '：' in line else category
            
            elif '亮点' in line or '优势' in line:
                highlights.append(line.split('：')[-1].strip() if '：' in line else line)
        
        return ProjectAnalysis(
            quality_score=quality_score,
            category=category,
            tech_stack=tech_stack,
            highlights=highlights[:3],
            concerns=concerns,
            recommendation=recommendation,
            confidence=0.7
        )
    
    def _local_analysis(self, project_data: Dict) -> ProjectAnalysis:
        """本地分析（AI API不可用时的后备方案）"""
        stars = project_data.get('stars', 0)
        forks = project_data.get('forks', 0)
        language = project_data.get('language', '')
        description = project_data.get('description', '')
        topics = project_data.get('topics', [])
        
        # 基础质量评分
        quality_score = 0.0
        
        # Star数评分 (0.4权重)
        if stars >= 1000:
            quality_score += 0.4
        elif stars >= 100:
            quality_score += 0.3
        elif stars >= 10:
            quality_score += 0.2
        else:
            quality_score += 0.1
        
        # Fork数评分 (0.2权重)
        if forks >= 100:
            quality_score += 0.2
        elif forks >= 10:
            quality_score += 0.15
        elif forks >= 1:
            quality_score += 0.1
        
        # 描述质量评分 (0.2权重)
        if description and len(description) > 100:
            quality_score += 0.2
        elif description and len(description) > 50:
            quality_score += 0.15
        elif description:
            quality_score += 0.1
        
        # 标签评分 (0.2权重)
        if len(topics) >= 5:
            quality_score += 0.2
        elif len(topics) >= 3:
            quality_score += 0.15
        elif len(topics) >= 1:
            quality_score += 0.1
        
        # 技术分类
        category = self._classify_by_language_and_topics(language, topics, description)
        
        # 技术栈识别
        tech_stack = self._identify_tech_stack(language, topics, description)
        
        # 生成亮点
        highlights = []
        if stars >= 100:
            highlights.append(f"高人气项目({stars} stars)")
        if forks >= 10:
            highlights.append(f"活跃的社区({forks} forks)")
        if len(topics) >= 3:
            highlights.append("丰富的项目标签")
        if len(description) > 100:
            highlights.append("详细的项目描述")
        
        # 潜在问题
        concerns = []
        if stars < 10:
            concerns.append("项目知名度较低")
        if not description:
            concerns.append("缺少项目描述")
        if not topics:
            concerns.append("缺少项目标签")
        
        recommendation = f"{'值得关注的' if quality_score > 0.6 else '有潜力的'}{category}项目"
        
        return ProjectAnalysis(
            quality_score=min(quality_score, 1.0),
            category=category,
            tech_stack=tech_stack,
            highlights=highlights[:3],
            concerns=concerns[:2],
            recommendation=recommendation,
            confidence=0.8
        )
    
    def _classify_by_language_and_topics(self, language: str, topics: List[str], description: str) -> str:
        """基于语言和标签分类项目"""
        text = f"{language} {' '.join(topics)} {description}".lower()
        
        # 分类规则
        if any(keyword in text for keyword in ['ai', 'ml', 'machine learning', 'deep learning', 'neural']):
            return "AI/机器学习"
        elif any(keyword in text for keyword in ['web', 'react', 'vue', 'angular', 'frontend']):
            return "Web开发"
        elif any(keyword in text for keyword in ['mobile', 'android', 'ios', 'flutter', 'react native']):
            return "移动开发"
        elif any(keyword in text for keyword in ['devops', 'docker', 'kubernetes', 'ci/cd']):
            return "DevOps/云原生"
        elif any(keyword in text for keyword in ['blockchain', 'crypto', 'web3', 'ethereum']):
            return "区块链/Web3"
        elif any(keyword in text for keyword in ['game', 'unity', 'unreal', 'godot']):
            return "游戏开发"
        elif any(keyword in text for keyword in ['data', 'analysis', 'visualization', 'pandas']):
            return "数据科学"
        elif any(keyword in text for keyword in ['security', 'cyber', 'penetration', 'vulnerability']):
            return "网络安全"
        elif language in ['C', 'C++', 'Rust', 'Assembly']:
            return "系统编程"
        else:
            return "通用工具"
    
    def _identify_tech_stack(self, language: str, topics: List[str], description: str) -> List[str]:
        """识别技术栈"""
        tech_stack = []
        
        # 主要编程语言
        if language:
            tech_stack.append(language)
        
        # 从标签中提取技术栈
        tech_keywords = {
            'react', 'vue', 'angular', 'nodejs', 'express', 'django', 'flask',
            'pytorch', 'tensorflow', 'keras', 'docker', 'kubernetes', 'aws',
            'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch'
        }
        
        text = f"{' '.join(topics)} {description}".lower()
        for keyword in tech_keywords:
            if keyword in text:
                tech_stack.append(keyword.title())
        
        return list(set(tech_stack))[:5]  # 最多返回5个

# 使用示例
if __name__ == "__main__":
    analyzer = ModelScopeAnalyzer()
    
    # 测试项目数据
    test_project = {
        'name': 'awesome-ai-tool',
        'owner_login': 'developer',
        'description': 'A powerful AI tool for code generation using machine learning',
        'language': 'Python',
        'stars': 150,
        'forks': 25,
        'created_at': '2025-01-01T00:00:00Z',
        'topics': ['ai', 'machine-learning', 'code-generation'],
        'license_name': 'MIT'
    }
    
    analysis = analyzer.analyze_project(test_project)
    print(f"质量评分: {analysis.quality_score:.2f}")
    print(f"分类: {analysis.category}")
    print(f"技术栈: {', '.join(analysis.tech_stack)}")
    print(f"亮点: {', '.join(analysis.highlights)}")
    print(f"推荐理由: {analysis.recommendation}")