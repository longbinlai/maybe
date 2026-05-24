#!/usr/bin/env python3
"""
测试 1.2.1: RSSSource 初始化和基本配置
"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.sources.rss_source import RSSSource

print("="*80)
print("测试 1.2.1: RSSSource 初始化和基本配置")
print("="*80)
sys.stdout.flush()

# 测试 1: 基本初始化
config1 = {
    'name': 'test_rss',
    'type': 'rss',
    'category': 'test',
    'url': 'https://example.com/rss',
    'priority': 'high',
    'enabled': True,
    'max_items': 20,
    'keywords': ['test', 'example'],
    'min_items': 5,
    'max_age_days': 7
}

source1 = RSSSource('test_rss', config1)

assert source1.name == 'test_rss'
assert source1.category == 'test'
assert source1.priority == 'high'
assert source1.enabled == True
assert source1.max_items == 20
assert source1.url == 'https://example.com/rss'
assert source1.feed_type == 'rss'  # 默认值

print("✅ 基本初始化成功")
print(f"   name: {source1.name}")
print(f"   category: {source1.category}")
print(f"   priority: {source1.priority}")
print(f"   enabled: {source1.enabled}")
print(f"   max_items: {source1.max_items}")
print(f"   url: {source1.url}")
print(f"   feed_type: {source1.feed_type}")
sys.stdout.flush()

# 测试 2: 自定义 feed_type
config2 = {
    'name': 'atom_feed',
    'type': 'rss',
    'category': 'test',
    'url': 'https://example.com/atom',
    'feed_type': 'atom',
    'max_items': 10
}

source2 = RSSSource('atom_feed', config2)

assert source2.feed_type == 'atom'
assert source2.max_items == 10

print("✅ 自定义 feed_type 成功")
print(f"   feed_type: {source2.feed_type}")
print(f"   max_items: {source2.max_items}")
sys.stdout.flush()

# 测试 3: 默认值
config3 = {
    'name': 'minimal_rss',
    'type': 'rss',
    'category': 'test',
    'url': 'https://example.com/rss'
}

source3 = RSSSource('minimal_rss', config3)

assert source3.feed_type == 'rss'  # 默认值
assert source3.max_items == 20  # 默认值
assert source3.priority == 'medium'  # 继承自 BaseDataSource
assert source3.enabled == True  # 继承自 BaseDataSource

print("✅ 默认值测试成功")
print(f"   feed_type: {source3.feed_type}")
print(f"   max_items: {source3.max_items}")
print(f"   priority: {source3.priority}")
print(f"   enabled: {source3.enabled}")
sys.stdout.flush()

# 测试 4: 验证配置
assert hasattr(source1, 'validate')
assert hasattr(source1, 'fetch')
assert hasattr(source1, '_parse_entry')
assert hasattr(source1, '_parse_date')

print("✅ 方法存在性验证成功")
print(f"   validate: {hasattr(source1, 'validate')}")
print(f"   fetch: {hasattr(source1, 'fetch')}")
print(f"   _parse_entry: {hasattr(source1, '_parse_entry')}")
print(f"   _parse_date: {hasattr(source1, '_parse_date')}")
sys.stdout.flush()

print("\n✅ 测试 1.2.1 通过！")
sys.stdout.flush()
