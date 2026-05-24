#!/usr/bin/env python3
"""
测试 1.1.2: DataItem 序列化 (to_dict)
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.core.base_source import DataItem

print("="*80)
print("测试 1.1.2: DataItem 序列化")
print("="*80)
sys.stdout.flush()

item = DataItem(
    id="test_003",
    source="rss",
    category="central_bank",
    title="美联储利率决议",
    content="美联储宣布维持利率不变",
    url="https://federalreserve.gov",
    published=datetime(2024, 1, 15, 14, 30, 0),
    metadata={'author': 'Federal Reserve'}
)

data = item.to_dict()

# 验证所有字段
assert data['id'] == "test_003"
assert data['source'] == "rss"
assert data['category'] == "central_bank"
assert data['title'] == "美联储利率决议"
assert data['content'] == "美联储宣布维持利率不变"
assert data['url'] == "https://federalreserve.gov"
assert data['published'] == "2024-01-15T14:30:00"  # ISO 格式
assert data['metadata'] == {'author': 'Federal Reserve'}

print("✅ 序列化成功")
print(f"   字段数: {len(data)}")
print(f"   字段: {list(data.keys())}")
print(f"   发布时间格式: {data['published']}")
sys.stdout.flush()

# 测试空元数据
item2 = DataItem(
    id="test_004",
    source="test",
    category="test",
    title="标题",
    content="内容",
    url="https://example.com",
    published=datetime(2024, 1, 1)
)

data2 = item2.to_dict()
assert data2['metadata'] == {}
print("✅ 空元数据序列化成功")
sys.stdout.flush()

print("\n✅ 测试 1.1.2 通过！")
sys.stdout.flush()
