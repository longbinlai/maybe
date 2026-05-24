#!/usr/bin/env python3
"""
测试 1.1.6: DataSourceResult 类
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.core.base_source import DataSourceResult, DataItem, ValidationResult

print("="*80)
print("测试 1.1.6: DataSourceResult 类")
print("="*80)
sys.stdout.flush()

# 创建测试数据项
item1 = DataItem(
    id="item_001",
    source="test",
    category="test",
    title="标题1",
    content="内容1",
    url="https://example.com/1",
    published=datetime(2024, 1, 1)
)

item2 = DataItem(
    id="item_002",
    source="test",
    category="test",
    title="标题2",
    content="内容2",
    url="https://example.com/2",
    published=datetime(2024, 1, 2)
)

# 创建验证结果
validation = ValidationResult(
    is_valid=True,
    score=90,
    issues=[],
    details={'items_count': 2}
)

# 测试 1: 成功结果
result1 = DataSourceResult(
    source_name="test_source",
    source_type="rss",
    category="test_category",
    status="success",
    items=[item1, item2],
    validation=validation,
    error=None,
    fetched_at=datetime.now()
)

assert result1.source_name == "test_source"
assert result1.source_type == "rss"
assert result1.category == "test_category"
assert result1.status == "success"
assert len(result1.items) == 2
assert result1.validation.is_valid == True
assert result1.error is None

print("✅ 成功结果创建成功")
print(f"   source_name: {result1.source_name}")
print(f"   status: {result1.status}")
print(f"   items_count: {len(result1.items)}")
sys.stdout.flush()

# 测试 2: 失败结果
result2 = DataSourceResult(
    source_name="failed_source",
    source_type="rss",
    category="test_category",
    status="failed",
    items=[],
    validation=None,
    error="Connection timeout",
    fetched_at=datetime.now()
)

assert result2.status == "failed"
assert len(result2.items) == 0
assert result2.validation is None
assert result2.error == "Connection timeout"

print("✅ 失败结果创建成功")
print(f"   status: {result2.status}")
print(f"   error: {result2.error}")
sys.stdout.flush()

# 测试 3: 降级结果
result3 = DataSourceResult(
    source_name="degraded_source",
    source_type="rss",
    category="test_category",
    status="degraded",
    items=[item1],
    validation=validation,
    error=None,
    fetched_at=datetime.now()
)

assert result3.status == "degraded"
assert len(result3.items) == 1

print("✅ 降级结果创建成功")
print(f"   status: {result3.status}")
print(f"   items_count: {len(result3.items)}")
sys.stdout.flush()

# 测试 4: to_dict 序列化
data = result1.to_dict()
assert data['source_name'] == "test_source"
assert data['status'] == "success"
assert data['items_count'] == 2
assert len(data['items']) == 2
assert data['validation']['is_valid'] == True
assert data['validation']['score'] == 90

print("✅ to_dict 序列化成功")
print(f"   字段数: {len(data)}")
print(f"   字段: {list(data.keys())}")
sys.stdout.flush()

print("\n✅ 测试 1.1.6 通过！")
sys.stdout.flush()
