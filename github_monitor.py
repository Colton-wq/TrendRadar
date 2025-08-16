#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub项目监控系统
基于TrendRadar架构的GitHub新项目监控和推送系统
"""

import os
import json
import time
import requests
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
import hashlib

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class GitHubProject:
    """GitHub项目数据结构"""
    name: str
    full_name: str
    description: str
    html_url: str
    stars: int
    forks: int
    language: str
    created_at: str
    updated_at: str
    owner_login: str
    topics: List[str]
    license_name: Optional[str] = None
    ai_score: Optional[float] = None
    ai_analysis: Optional[str] = None

class GitHubMonitor:
    """GitHub项目监控核心类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化监控器"""
        self.config = self._load_config(config_path)
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.session = requests.Session()
        
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            })
        
        # API限制控制
        self.api_calls_count = 0
        self.api_calls_reset_time = time.time() + 3600  # 1小时重置
        self.max_calls_per_hour = 80  # 安全余量
        
        # 数据存储
        self.seen_projects = self._load_seen_projects()
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 加载GitHub关键词配置
            github_config_path = "config/github_keywords.yaml"
            if os.path.exists(github_config_path):
                with open(github_config_path, 'r', encoding='utf-8') as f:
                    github_config = yaml.safe_load(f)
                config.update(github_config)
            
            return config
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            return {}
    
    def _load_seen_projects(self) -> set:
        """加载已处理项目列表"""
        seen_file = "data/seen_github_projects.json"
        if os.path.exists(seen_file):
            try:
                with open(seen_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except Exception as e:
                logger.error(f"加载已处理项目失败: {e}")
        return set()
    
    def _save_seen_projects(self):
        """保存已处理项目列表"""
        os.makedirs("data", exist_ok=True)
        seen_file = "data/seen_github_projects.json"
        try:
            with open(seen_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.seen_projects), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存已处理项目失败: {e}")
    
    def _check_api_limit(self) -> bool:
        """检查API调用限制"""
        current_time = time.time()
        
        # 重置计数器
        if current_time > self.api_calls_reset_time:
            self.api_calls_count = 0
            self.api_calls_reset_time = current_time + 3600
        
        # 检查是否超限
        if self.api_calls_count >= self.max_calls_per_hour:
            logger.warning("API调用次数已达上限，等待重置")
            return False
        
        return True
    
    def _make_github_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """发起GitHub API请求"""
        if not self._check_api_limit():
            return None
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            self.api_calls_count += 1
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                logger.warning("API限制触发，等待重置")
                return None
            else:
                logger.error(f"API请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"API请求异常: {e}")
            return None
    
    def _build_search_query(self, category: str, config: Dict) -> str:
        """构建GitHub搜索查询"""
        keywords = config.get('keywords', [])
        must_have = config.get('must_have', [])
        exclude = config.get('exclude', [])
        min_stars = config.get('min_stars', 0)
        languages = config.get('languages', [])
        
        # 基础关键词
        query_parts = []
        if keywords:
            query_parts.extend(keywords)
        
        # 必须包含的词
        for term in must_have:
            if term.startswith('+'):
                query_parts.append(term[1:])
        
        # 排除的词
        for term in exclude:
            if term.startswith('!'):
                query_parts.append(f"-{term[1:]}")
        
        # 最小Star数
        if min_stars > 0:
            query_parts.append(f"stars:>={min_stars}")
        
        # 编程语言
        if languages:
            lang_query = " OR ".join([f"language:{lang}" for lang in languages])
            query_parts.append(f"({lang_query})")
        
        # 时间范围（最近7天）
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        query_parts.append(f"created:>={week_ago}")
        
        return " ".join(query_parts)
    
    def search_repositories(self, category: str, config: Dict) -> List[GitHubProject]:
        """搜索GitHub仓库"""
        query = self._build_search_query(category, config)
        logger.info(f"搜索 {category} 类别项目: {query}")
        
        url = "https://api.github.com/search/repositories"
        params = {
            'q': query,
            'sort': 'created',
            'order': 'desc',
            'per_page': 30
        }
        
        response_data = self._make_github_request(url, params)
        if not response_data:
            return []
        
        projects = []
        for item in response_data.get('items', []):
            # 检查是否已处理过
            project_id = f"{item['full_name']}_{item['created_at']}"
            if project_id in self.seen_projects:
                continue
            
            # 创建项目对象
            project = GitHubProject(
                name=item['name'],
                full_name=item['full_name'],
                description=item.get('description', ''),
                html_url=item['html_url'],
                stars=item['stargazers_count'],
                forks=item['forks_count'],
                language=item.get('language', ''),
                created_at=item['created_at'],
                updated_at=item['updated_at'],
                owner_login=item['owner']['login'],
                topics=item.get('topics', []),
                license_name=item.get('license', {}).get('name') if item.get('license') else None
            )
            
            projects.append(project)
            self.seen_projects.add(project_id)
        
        logger.info(f"发现 {len(projects)} 个新项目")
        return projects
    
    def analyze_with_ai(self, project: GitHubProject) -> Tuple[float, str]:
        """使用AI分析项目（ModelScope集成）"""
        # 这里可以集成ModelScope的Qwen3-Coder API
        # 目前返回模拟数据
        
        # 基于项目信息计算简单评分
        score = 0.0
        analysis_parts = []
        
        # Star数评分
        if project.stars >= 100:
            score += 0.3
            analysis_parts.append("高Star数项目")
        elif project.stars >= 10:
            score += 0.2
            analysis_parts.append("中等Star数项目")
        
        # 描述质量评分
        if project.description and len(project.description) > 50:
            score += 0.2
            analysis_parts.append("详细描述")
        
        # 编程语言评分
        popular_languages = ['Python', 'JavaScript', 'TypeScript', 'Go', 'Rust']
        if project.language in popular_languages:
            score += 0.2
            analysis_parts.append(f"热门语言({project.language})")
        
        # Topics评分
        if len(project.topics) >= 3:
            score += 0.2
            analysis_parts.append("丰富的标签")
        
        # 许可证评分
        if project.license_name:
            score += 0.1
            analysis_parts.append("开源许可证")
        
        analysis = "、".join(analysis_parts) if analysis_parts else "基础项目"
        return min(score, 1.0), analysis
    
    def format_project_message(self, project: GitHubProject, category: str) -> str:
        """格式化项目推送消息"""
        # AI分析
        ai_score, ai_analysis = self.analyze_with_ai(project)
        project.ai_score = ai_score
        project.ai_analysis = ai_analysis
        
        # 格式化消息
        message = f"""🚀 **新发现GitHub项目** ({category})

📦 **项目名称**: {project.name}
👤 **作者**: {project.owner_login}
⭐ **Stars**: {project.stars} | 🍴 **Forks**: {project.forks}
💻 **语言**: {project.language or '未知'}
📅 **创建时间**: {project.created_at[:10]}

📝 **描述**: {project.description[:200]}{'...' if len(project.description) > 200 else ''}

🔗 **链接**: {project.html_url}

🤖 **AI评分**: {ai_score:.1f}/1.0 ({ai_analysis})

📊 **标签**: {', '.join(project.topics[:5]) if project.topics else '无'}
⚖️ **许可证**: {project.license_name or '未知'}
"""
        return message
    
    def send_notifications(self, projects: List[GitHubProject], category: str):
        """发送通知"""
        if not projects:
            return
        
        # 复用TrendRadar的推送逻辑
        from main import send_notifications as trend_send
        
        messages = []
        for project in projects:
            message = self.format_project_message(project, category)
            messages.append(message)
        
        # 合并消息
        if messages:
            combined_message = f"📈 **GitHub项目监控报告** - {category}\n\n" + "\n\n---\n\n".join(messages)
            
            # 发送到各个渠道
            try:
                trend_send(combined_message, "GitHub项目监控")
                logger.info(f"成功推送 {len(projects)} 个项目到通知渠道")
            except Exception as e:
                logger.error(f"推送失败: {e}")
    
    def run_monitoring(self):
        """执行监控任务"""
        logger.info("开始GitHub项目监控")
        
        # 获取监控配置
        github_config = self.config.get('github_monitoring', {})
        if not github_config:
            logger.warning("未找到GitHub监控配置")
            return
        
        total_projects = 0
        
        # 遍历各个类别
        for category, config in github_config.items():
            if not isinstance(config, dict):
                continue
                
            logger.info(f"监控类别: {category}")
            
            try:
                # 搜索项目
                projects = self.search_repositories(category, config)
                
                if projects:
                    # 发送通知
                    self.send_notifications(projects, category)
                    total_projects += len(projects)
                
                # API调用间隔
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"监控类别 {category} 失败: {e}")
                continue
        
        # 保存状态
        self._save_seen_projects()
        
        logger.info(f"监控完成，共发现 {total_projects} 个新项目")
        logger.info(f"API调用次数: {self.api_calls_count}/{self.max_calls_per_hour}")

def main():
    """主函数"""
    monitor = GitHubMonitor()
    monitor.run_monitoring()

if __name__ == "__main__":
    main()