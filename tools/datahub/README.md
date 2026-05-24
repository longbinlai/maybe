# DataHub - 宏观经济数据源管理系统

## 📋 系统概述

DataHub 是一个灵活的、插件式的数据源管理系统，专门为家庭理财的宏观经济分析设计。它支持 RSS 订阅和 Yahoo Finance 数据，并提供统一的数据访问接口。

## 🎯 核心特性

### 1. 插件式架构
- **RSS 数据源**: 支持标准 RSS/Atom 格式
- **Yahoo Finance 数据源**: 支持股票、汇率、商品价格
- **易于扩展**: 新增数据源只需继承 `BaseDataSource` 类

### 2. 配置驱动
- 所有数据源通过 YAML 配置
- 支持启用/禁用单个数据源
- 可配置验证规则和优先级

### 3. 智能验证
- 自动检测数据质量
- 验证数据量、时效性、关键词覆盖率
- 生成详细的验证报告

### 4. 缓存机制
- 自动缓存获取的数据
- 可配置缓存 TTL（默认 1 小时）
- 避免重复请求，提高效率

## 🏗️ 系统架构

```
macro-trends/
├── datahub/                    # DataHub 核心模块
│   ├── core/
│   │   ├── base_source.py     # 数据源基类
│   │   └── source_registry.py # 数据源注册中心
│   └── sources/
│       ├── rss_source.py      # RSS 数据源实现
│       └── yfinance_source.py # Yahoo Finance 数据源实现
├── config/
│   └── sources.yaml           # 数据源配置文件
├── cache/                     # 数据缓存目录
├── reports/                   # 生成的报告
└── cli.py                     # 命令行工具
```

## 📊 已配置的数据源（13个）

### 央行数据源（3个）
- ✅ **Federal Reserve** - 美联储新闻稿
- ✅ **European Central Bank** - 欧洲央行新闻
- ✅ **Bank of Japan** - 日本央行新闻

### 经济数据源（2个）
- ✅ **Bureau of Labor Statistics** - 美国劳工统计局
- ✅ **Bureau of Economic Analysis** - 美国经济分析局

### 外汇数据源（1个）
- ✅ **ForexLive** - 外汇市场新闻

### 大宗商品数据源（1个）
- ✅ **OilPrice.com** - 原油和能源新闻

### 中国经济数据源（1个）
- ✅ **South China Morning Post** - 中国经济新闻

### Yahoo Finance 数据源（5个）
- ✅ **yfinance_gold** - 黄金价格 (GC=F)
- ✅ **yfinance_oil** - 原油价格 (CL=F)
- ✅ **yfinance_fx** - 主要汇率 (CNY, JPY, EUR, GBP)
- ✅ **yfinance_indices** - 主要指数 (S&P500, DJI, NASDAQ, 恒生, 上证)
- ✅ **yfinance_news** - 市场新闻

## 🚀 快速开始

### 1. 列出所有数据源
```bash
cd ~/.openclaw/workspace/skills/macro-trends
python3 cli.py list
```

### 2. 测试数据源连接
```bash
python3 cli.py test
```

### 3. 获取所有数据
```bash
python3 cli.py fetch-all
```

### 4. 获取单个数据源
```bash
python3 cli.py fetch federal_reserve
python3 cli.py fetch yfinance_fx
```

### 5. 查看缓存状态
```bash
python3 cli.py status
```

## 📝 配置文件详解

### 基本结构
```yaml
sources:
  source_name:
    type: rss | yfinance
    category: central_bank | economic_data | forex | commodity | china | market
    priority: high | medium | low
    enabled: true | false
    # 其他配置...
```

### RSS 数据源配置
```yaml
federal_reserve:
  type: rss
  category: central_bank
  priority: high
  enabled: true
  url: https://www.federalreserve.gov/feeds/press_all.xml
  max_items: 20
  validation:
    min_items: 10
    max_age_days: 7
    keywords:
      - federal reserve
      - monetary policy
      - interest rate
```

### Yahoo Finance 数据源配置
```yaml
yfinance_fx:
  type: yfinance
  category: forex
  priority: high
  enabled: true
  tickers:
    - CNY=X  # USD/CNY
    - JPY=X  # USD/JPY
    - EUR=X  # EUR/USD
  data_type: price | news | info
  period: 5d
  interval: 1d
  validation:
    min_items: 2
    max_age_days: 1
```

## 🔧 添加新数据源

### 方法 1: 添加 RSS 数据源

1. 在 `config/sources.yaml` 中添加配置：
```yaml
my_new_source:
  type: rss
  category: your_category
  priority: medium
  enabled: true
  url: https://example.com/rss
  max_items: 20
  validation:
    min_items: 5
    max_age_days: 7
    keywords:
      - keyword1
      - keyword2
```

2. 重新运行 `python3 cli.py list` 验证

### 方法 2: 添加 Yahoo Finance 数据源

1. 在 `config/sources.yaml` 中添加配置：
```yaml
yfinance_new:
  type: yfinance
  category: your_category
  priority: medium
  enabled: true
  tickers:
    - SYMBOL1
    - SYMBOL2
  data_type: price
  period: 5d
  interval: 1d
```

2. 重新运行 `python3 cli.py list` 验证

### 方法 3: 开发自定义数据源

1. 创建新文件 `datahub/sources/my_source.py`:
```python
from ..core.base_source import BaseDataSource, DataSourceResult, DataItem

class MySource(BaseDataSource):
    def fetch(self) -> DataSourceResult:
        # 实现你的数据获取逻辑
        items = []
        
        # 获取数据...
        
        return DataSourceResult(
            source_name=self.name,
            source_type='my_source',
            category=self.category,
            status='success',
            items=items
        )
```

2. 在 `datahub/sources/__init__.py` 中导出:
```python
from .my_source import MySource
```

3. 在 `datahub/__init__.py` 中注册:
```python
from .sources.my_source import MySource
```

4. 在 `datahub/core/source_registry.py` 中添加映射:
```python
source_types = {
    'rss': RSSSource,
    'yfinance': YFinanceSource,
    'my_source': MySource,  # 添加这一行
}
```

5. 在配置文件中添加数据源配置

## 📈 数据格式

### DataItem 结构
```python
{
    'id': 'unique_id',           # 唯一标识符
    'source': 'source_name',     # 数据源名称
    'category': 'central_bank',  # 类别
    'title': 'Article Title',    # 标题
    'content': 'Content...',     # 内容
    'url': 'https://...',        # 链接
    'published': '2024-01-01T00:00:00',  # 发布时间
    'metadata': {                # 元数据
        'author': 'Author Name',
        'tags': ['tag1', 'tag2']
    }
}
```

### DataSourceResult 结构
```python
{
    'source_name': 'federal_reserve',
    'source_type': 'rss',
    'category': 'central_bank',
    'status': 'success' | 'degraded' | 'failed',
    'items_count': 20,
    'items': [...],
    'validation': {
        'is_valid': true,
        'score': 85,
        'issues': ['issue1', 'issue2'],
        'details': {...}
    },
    'error': null,
    'fetched_at': '2024-01-01T00:00:00'
}
```

## 🐛 故障排查

### 问题 1: 数据源返回 0 篇文章
**可能原因**:
- RSS URL 已失效
- 网站阻止了爬虫
- 网络连接问题

**解决方案**:
```bash
# 测试连接
python3 cli.py test

# 查看具体错误
python3 cli.py fetch source_name
```

### 问题 2: 导入模块超时
**可能原因**:
- yfinance 首次导入需要下载数据
- 网络连接慢

**解决方案**:
- 增加超时时间
- 使用缓存（默认已启用）

### 问题 3: 验证失败
**可能原因**:
- 数据量不足
- 数据过旧
- 关键词覆盖率低

**解决方案**:
- 调整 `validation` 配置中的阈值
- 检查数据源 URL 是否正确

## 📊 报告示例

运行 `python3 cli.py fetch-all` 后生成的报告：

```json
{
  "timestamp": "2024-01-01T00:00:00",
  "summary": {
    "total_sources": 13,
    "success": 10,
    "degraded": 2,
    "failed": 1,
    "success_rate": 76.9
  },
  "by_category": {
    "central_bank": {
      "total": 3,
      "success": 3,
      "items_count": 60
    },
    "forex": {
      "total": 2,
      "success": 2,
      "items_count": 24
    }
  },
  "total_items": 150,
  "sources": {...}
}
```

## 🔄 集成到 OpenClaw

### 作为 Skill 使用

在 OpenClaw 对话中：
```
用户: "获取最新的宏观经济数据"
OpenClaw: python3 ~/.openclaw/workspace/skills/macro-trends/cli.py fetch-all
```

### 定时任务

创建 Cron 任务每天自动获取数据：
```bash
openclaw cron add \
  --name "daily-macro-data" \
  --cron "0 9 * * *" \
  --command "python3 ~/.openclaw/workspace/skills/macro-trends/cli.py fetch-all" \
  --description "每天上午9点获取宏观经济数据"
```

## 📝 下一步

### Phase 2: 宏观分析模块
- 经济周期判断算法
- 利率差分析
- 资产相对吸引力评分
- 持仓匹配度分析

### Phase 3: 报告生成
- 生成中文报告
- 集成到 MEMORY.md
- 飞书推送

## 📚 参考资料

- [yfinance 文档](https://ranaroussi.github.io/yfinance/)
- [feedparser 文档](https://feedparser.readthedocs.io/)
- [RSS 2.0 规范](https://www.rssboard.org/rss-specification)

---

**创建时间**: 2024-01-01  
**最后更新**: 2024-01-01  
**维护者**: OpenClaw System
