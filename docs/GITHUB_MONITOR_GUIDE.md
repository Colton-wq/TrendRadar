# GitHub项目监控系统部署指南

## 📋 系统概述

GitHub项目监控系统是基于TrendRadar架构的智能项目发现工具，能够：

- 🔍 **智能搜索**: 基于关键词自动发现GitHub新项目
- 🤖 **AI分析**: 集成ModelScope Qwen3-Coder进行项目质量评估
- 📱 **多渠道推送**: 支持企业微信、飞书、钉钉、Telegram推送
- ⚡ **自动化运行**: GitHub Actions每小时自动监控
- 🎯 **精准过滤**: 支持必须词和排除词的复杂筛选逻辑

## 🏗️ 系统架构

```
GitHub API → 关键词匹配 → AI质量分析 → 去重存储 → 多渠道推送
     ↓           ↓            ↓          ↓          ↓
  项目搜索    智能筛选     ModelScope   历史管理   企微/飞书/钉钉
```

## 🚀 快速部署

### 1. 环境准备

**必需的GitHub Secrets配置**:
```bash
# GitHub API访问（必需）- 注意：不能使用GITHUB_开头的名称
GH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# ModelScope AI分析（可选，提升分析质量）
MODELSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# 推送渠道配置（至少配置一个）
WEWORK_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
TELEGRAM_BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ
TELEGRAM_CHAT_ID=-1001234567890
```

⚠️ **重要提示**: GitHub Secrets名称不能以 `GITHUB_` 开头，这是GitHub的保留前缀。因此我们使用 `GH_TOKEN` 而不是 `GITHUB_TOKEN`。

### 2. 配置GitHub Token

1. 访问 [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. 点击 "Generate new token (classic)"
3. 选择权限：
   - ✅ `public_repo` (访问公共仓库)
   - ✅ `read:user` (读取用户信息)
4. 复制生成的token到 `GH_TOKEN` Secret

### 3. 配置推送渠道

#### 企业微信机器人
1. 在企业微信群中添加机器人
2. 获取Webhook URL
3. 设置 `WEWORK_WEBHOOK_URL` Secret

#### 飞书机器人
1. 在飞书群中添加自定义机器人
2. 获取Webhook URL
3. 设置 `FEISHU_WEBHOOK_URL` Secret

#### 钉钉机器人
1. 在钉钉群中添加自定义机器人
2. 获取Webhook URL
3. 设置 `DINGTALK_WEBHOOK_URL` Secret

### 4. 启用GitHub Actions

1. 进入仓库 **Actions** 选项卡
2. 找到 "GitHub Project Monitor" 工作流
3. 点击 **Enable workflow**
4. 手动触发一次测试运行

## ⚙️ 配置详解

### 关键词配置文件

编辑 `config/github_keywords.yaml` 自定义监控类别：

```yaml
github_monitoring:
  # 自定义监控类别
  my_category:
    keywords: 
      - "关键词1"
      - "关键词2"
    must_have:
      - "+必须包含的词"
    exclude:
      - "!要排除的词"
    min_stars: 10
    languages: ["Python", "JavaScript"]
```

### 配置语法说明

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `keywords` | 基础关键词列表 | `["react", "vue"]` |
| `must_have` | 必须包含的词（+前缀） | `["+framework"]` |
| `exclude` | 要排除的词（!前缀） | `["!tutorial"]` |
| `min_stars` | 最小Star数要求 | `10` |
| `languages` | 编程语言限制 | `["Python", "Go"]` |

### 高级搜索语法

GitHub API支持的搜索修饰符：

```bash
# 时间范围
created:>2025-01-01
updated:>2025-01-01

# Star数范围
stars:10..100
stars:>50

# 编程语言
language:python
language:javascript OR language:typescript

# 仓库大小
size:>1000

# 许可证
license:mit
license:apache-2.0

# 组合查询示例
machine learning language:python stars:>10 created:>2025-01-01
```

## 🤖 AI分析功能

### ModelScope集成

系统集成了阿里云ModelScope的Qwen3-Coder-480B-A35B-Instruct模型，提供：

1. **项目质量评分** (0-10分)
2. **技术分类识别** (AI/ML, Web开发等)
3. **技术栈分析** (框架、库识别)
4. **项目亮点提取** (优势分析)
5. **潜在问题识别** (风险评估)

### 配置ModelScope API

1. 注册 [阿里云账号](https://www.aliyun.com/)
2. 开通 [模型服务灵积](https://dashscope.aliyun.com/)
3. 获取API Key
4. 设置 `MODELSCOPE_API_KEY` Secret

### 成本控制

ModelScope API按token计费：

| 输入Token数 | 价格(百万token) | 缓存价格 |
|-------------|----------------|----------|
| 0-32K | $1 | $0.1 |
| 32K-128K | $1.8 | $0.18 |
| 128K-256K | $3 | $0.3 |
| 256K-1M | $6 | $0.6 |

**成本估算**: 每个项目分析约消耗500-1000 tokens，成本约$0.0005-0.001

## 📊 监控效果

### 推送消息格式

```
🚀 新发现GitHub项目 (AI/机器学习)

📦 项目名称: awesome-ai-tool
👤 作者: developer
⭐ Stars: 150 | 🍴 Forks: 25
💻 语言: Python
📅 创建时间: 2025-01-15

📝 描述: 一个强大的AI代码生成工具...

🔗 链接: https://github.com/developer/awesome-ai-tool

🤖 AI评分: 8.5/10 (高质量AI工具项目)

📊 标签: ai, machine-learning, code-generation
⚖️ 许可证: MIT
```

### 监控统计

- **监控频率**: 每小时自动运行
- **API限制**: 每小时最多80次GitHub API调用
- **覆盖范围**: 10个技术领域，100+关键词
- **去重机制**: 基于项目全名和创建时间

## 🔧 故障排除

### 常见问题

#### 1. GitHub API限制
**问题**: API调用超限
**解决**: 
- 检查 `GH_TOKEN` 是否正确配置
- 降低监控频率或减少关键词数量
- 使用GitHub App Token提高限制

#### 2. 推送失败
**问题**: 消息推送不成功
**解决**:
- 验证Webhook URL是否正确
- 检查机器人权限设置
- 查看GitHub Actions日志

#### 3. AI分析失败
**问题**: ModelScope API调用失败
**解决**:
- 检查 `MODELSCOPE_API_KEY` 配置
- 确认账户余额充足
- 系统会自动降级到本地分析

#### 4. Secret配置错误
**问题**: Secret名称以GITHUB_开头
**解决**:
- 使用 `GH_TOKEN` 而不是 `GITHUB_TOKEN`
- GitHub保留所有 `GITHUB_` 前缀的环境变量

### 调试方法

#### 查看运行日志
1. 进入 **Actions** 选项卡
2. 点击最新的工作流运行
3. 查看 "Run GitHub Project Monitor" 步骤日志

#### 手动测试
```bash
# 本地测试
export GITHUB_TOKEN=your_token_here
python github_monitor.py

# 测试特定类别
CATEGORIES=ai_ml python github_monitor.py

# 强制运行（忽略去重）
FORCE_RUN=true python github_monitor.py
```

## 📈 性能优化

### API调用优化
- 使用智能缓存减少重复请求
- 批量处理项目分析
- 合理设置请求间隔

### 存储优化
- 定期清理历史数据
- 压缩存储格式
- 使用增量更新

### 推送优化
- 合并相似项目推送
- 设置推送频率限制
- 支持推送内容自定义

## 🔒 安全考虑

### Token安全
- 使用GitHub Secrets存储敏感信息
- 定期轮换API密钥
- 限制Token权限范围

### 数据隐私
- 不存储敏感项目信息
- 遵循GitHub API使用条款
- 支持数据删除和清理

## 📚 扩展开发

### 添加新的监控类别
1. 编辑 `config/github_keywords.yaml`
2. 添加新的类别配置
3. 测试关键词匹配效果

### 集成新的推送渠道
1. 在 `github_monitor.py` 中添加推送逻辑
2. 配置相应的环境变量
3. 更新GitHub Actions工作流

### 自定义AI分析
1. 修改 `modelscope_analyzer.py`
2. 调整分析提示词
3. 添加新的评估维度

## 📞 技术支持

如遇到问题，请：

1. 查看 [GitHub Issues](https://github.com/Colton-wq/TrendRadar/issues)
2. 提交详细的错误日志
3. 描述复现步骤和环境信息

---

**最后更新**: 2025-08-16
**版本**: v1.0.1 (修正Secret配置)