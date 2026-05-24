#!/usr/bin/env python3
"""
测试 1.1.1: DataItem 基本创建
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接导入 base_source
from datahub.core.base_source import DataItem

print("="*80)
print("测试 1.1.1: DataItem 基本创建")
print("="*80)
sys.stdout.flush()

# 测试 1: 基本创建
item = DataItem(
    id="test_001",
    source="test_source",
    category="test_category",
    title="测试标题",
    content="测试内容",
    url="https://example.com/test",
    published=datetime(2024, 1, 1, 12, 0, 0)
)

assert item.id == "test_001"
assert item.source == "test_source"
assert item.category == "test_category"
assert item.title == "测试标题"
assert item.content == "测试内容"
assert item.url == "https://example.com/test"
assert item.published == datetime(2024, 1, 1, 12, 0, 0)
assert item.metadata == {}  # 默认空字典

print("✅ 基本创建成功")
print(f"   ID: {item.id}")
print(f"   标题: {item.title}")
print(f"   元数据: {item.metadata}")
sys.stdout.flush()

# 测试 2: 带元数据创建
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
        'change_pct': 0.15,
        'volume': 1000000
    }
)

assert item2.metadata['ticker'] == 'CNY=X'
assert item2.metadata['price'] == 7.25
assert item2.metadata['change_pct'] == 0.15
assert item2.metadata['volume'] == 1000000

print("✅ 带元数据创建成功")
print(f"   Ticker: {item2.metadata['ticker']}")
print(f"   Price: {item2.metadata['price']}")
print(f"   Change: {item2.metadata['change_pct']}%")
sys.stdout.flush()

print("\n✅ 测试 1.1.1 通过！")
sys.stdout.flush()
