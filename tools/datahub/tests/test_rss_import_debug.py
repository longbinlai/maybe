#!/usr/bin/env python3
"""
逐步测试 RSSSource 导入
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("步骤 1: 导入基础库", flush=True)
import feedparser
print("  ✅ feedparser", flush=True)

print("步骤 2: 导入 base_source", flush=True)
from datahub.core.base_source import BaseDataSource, DataSourceResult, DataItem
print("  ✅ base_source", flush=True)

print("步骤 3: 导入 rss_source", flush=True)
from datahub.sources.rss_source import RSSSource
print("  ✅ rss_source", flush=True)

print("步骤 4: 创建 RSSSource 实例", flush=True)
config = {
    'name': 'test_rss',
    'type': 'rss',
    'category': 'test',
    'url': 'https://example.com/rss',
    'priority': 'high',
    'enabled': True,
    'max_items': 20
}
source = RSSSource('test_rss', config)
print(f"  ✅ 创建成功: {source.name}", flush=True)

print("\n✅ 所有步骤完成！", flush=True)
