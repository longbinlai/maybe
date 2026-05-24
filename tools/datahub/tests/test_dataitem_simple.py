#!/usr/bin/env python3
"""
最简单的 DataItem 测试 - 直接导入 base_source
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接导入 base_source，不经过 datahub/__init__.py
from datahub.core.base_source import DataItem

print("="*80)
print("测试 1: 创建 DataItem")
print("="*80)

item = DataItem(
    id="test_001",
    source="test_source",
    category="test_category",
    title="测试标题",
    content="测试内容",
    url="https://example.com/test",
    published=datetime(2024, 1, 1, 12, 0, 0)
)

print(f"✅ DataItem 创建成功")
print(f"   ID: {item.id}")
print(f"   标题: {item.title}")
print(f"   发布时间: {item.published}")

print("\n" + "="*80)
print("测试 2: 序列化")
print("="*80)

data = item.to_dict()
print(f"✅ 序列化成功")
print(f"   字段数: {len(data)}")
print(f"   字段: {list(data.keys())}")
print(f"   发布时间格式: {data['published']}")

print("\n" + "="*80)
print("测试 3: ID 生成")
print("="*80)

id1 = DataItem.generate_id("source1", "url1", "title1")
id2 = DataItem.generate_id("source1", "url1", "title1")
id3 = DataItem.generate_id("source2", "url1", "title1")

print(f"✅ ID 生成成功")
print(f"   ID1: {id1}")
print(f"   ID2: {id2}")
print(f"   ID3: {id3}")
print(f"   ID1 == ID2: {id1 == id2}")
print(f"   ID1 != ID3: {id1 != id3}")

print("\n" + "="*80)
print("测试 4: 带元数据")
print("="*80)

item2 = DataItem(
    id="test_002",
    source="yfinance",
    category="forex",
    title="USD/CNY 汇率",
    content="美元兑人民币汇率",
    url="https://finance.yahoo.com",
    published=datetime.now(),
    metadata={
        'ticker': 'CNY=X',
        'price': 7.25,
        'change_pct': 0.15
    }
)

print(f"✅ 带元数据创建成功")
print(f"   Ticker: {item2.metadata['ticker']}")
print(f"   Price: {item2.metadata['price']}")
print(f"   Change: {item2.metadata['change_pct']}%")

print("\n" + "="*80)
print("测试 5: Unicode 字符")
print("="*80)

item3 = DataItem(
    id="test_003",
    source="test",
    category="test",
    title="测试中文、日文、한글、🎉🎊",
    content="多语言内容: 中文 日本語 한국어 🚀",
    url="https://example.com",
    published=datetime.now()
)

print(f"✅ Unicode 字符处理成功")
print(f"   标题: {item3.title}")
print(f"   内容: {item3.content}")

print("\n" + "="*80)
print("所有测试通过！✅")
print("="*80)
