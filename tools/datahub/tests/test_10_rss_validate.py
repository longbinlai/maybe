#!/usr/bin/env python3
"""
测试 1.2.4: RSSSource.validate() 方法
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.sources.rss_source import RSSSource
from datahub.core.base_source import DataItem, ValidationResult

print("="*80)
print("测试 1.2.4: RSSSource.validate() 方法")
print("="*80)
sys.stdout.flush()

# 创建 RSSSource 实例
config = {
    'name': 'test_rss',
    'type': 'rss',
    'category': 'test',
    'url': 'https://example.com/rss',
    'priority': 'high',
    'enabled': True,
    'max_items': 20,
    'validation': {
        'min_items': 5,
        'max_age_days': 7,
        'keywords': ['python', 'coding', 'test']
    }
}
source = RSSSource('test_rss', config)
print("✅ RSSSource 实例创建成功")
sys.stdout.flush()

# 测试 1: 完美数据（高分）
print("\n测试 1: 完美数据（高分）")
items = []
for i in range(10):
    items.append(DataItem(
        id=f'item_{i}',
        source='test_rss',
        category='test',
        title=f'Python 编程技巧 {i}',
        content=f'这是一篇关于 Python 和 coding 的文章 {i}',
        url=f'https://example.com/article{i}',
        published=datetime.now() - timedelta(days=i),
        metadata={}
    ))

result = source.validate(items)
assert result.is_valid, f"应该验证通过，但结果: {result}"
assert result.score >= 90, f"分数应该 >= 90，实际: {result.score}"
assert len(result.issues) == 0, f"应该没有问题，但发现: {result.issues}"
print("✅ 完美数据验证通过")
print(f"   分数: {result.score}")
print(f"   问题数: {len(result.issues)}")
sys.stdout.flush()

# 测试 2: 数据量不足
print("\n测试 2: 数据量不足")
items = []
for i in range(3):  # 少于 min_items=5
    items.append(DataItem(
        id=f'item_{i}',
        source='test_rss',
        category='test',
        title=f'Python 编程技巧 {i}',
        content=f'这是一篇关于 Python 和 coding 的文章 {i}',
        url=f'https://example.com/article{i}',
        published=datetime.now() - timedelta(days=i),
        metadata={}
    ))

result = source.validate(items)
assert not result.is_valid, f"应该验证失败，但结果: {result}"
assert result.score < 90, f"分数应该 < 90，实际: {result.score}"
assert any('数据量不足' in issue for issue in result.issues), f"应该包含'数据量不足'问题，实际: {result.issues}"
print("✅ 正确检测数据量不足")
print(f"   分数: {result.score}")
print(f"   问题: {result.issues}")
sys.stdout.flush()

# 测试 3: 数据过旧
print("\n测试 3: 数据过旧")
items = []
for i in range(10):
    items.append(DataItem(
        id=f'item_{i}',
        source='test_rss',
        category='test',
        title=f'Python 编程技巧 {i}',
        content=f'这是一篇关于 Python 和 coding 的文章 {i}',
        url=f'https://example.com/article{i}',
        published=datetime.now() - timedelta(days=10 + i),  # 超过 max_age_days=7
        metadata={}
    ))

result = source.validate(items)
assert not result.is_valid, f"应该验证失败，但结果: {result}"
assert result.score < 90, f"分数应该 < 90，实际: {result.score}"
assert any('数据过旧' in issue for issue in result.issues), f"应该包含'数据过旧'问题，实际: {result.issues}"
print("✅ 正确检测数据过旧")
print(f"   分数: {result.score}")
print(f"   问题: {result.issues}")
sys.stdout.flush()

# 测试 4: 关键词覆盖率低
print("\n测试 4: 关键词覆盖率低")
items = []
for i in range(10):
    items.append(DataItem(
        id=f'item_{i}',
        source='test_rss',
        category='test',
        title=f'无关标题 {i}',
        content=f'这是一篇无关内容的文章 {i}',
        url=f'https://example.com/article{i}',
        published=datetime.now() - timedelta(days=i),
        metadata={}
    ))

result = source.validate(items)
assert not result.is_valid, f"应该验证失败，但结果: {result}"
assert result.score < 90, f"分数应该 < 90，实际: {result.score}"
assert any('关键词覆盖率低' in issue for issue in result.issues), f"应该包含'关键词覆盖率低'问题，实际: {result.issues}"
print("✅ 正确检测关键词覆盖率低")
print(f"   分数: {result.score}")
print(f"   问题: {result.issues}")
sys.stdout.flush()

# 测试 5: 多个问题叠加
print("\n测试 5: 多个问题叠加")
items = []
for i in range(2):  # 数据量不足
    items.append(DataItem(
        id=f'item_{i}',
        source='test_rss',
        category='test',
        title=f'无关标题 {i}',  # 关键词覆盖率低
        content=f'无关内容 {i}',
        url=f'https://example.com/article{i}',
        published=datetime.now() - timedelta(days=10),  # 数据过旧
        metadata={}
    ))

result = source.validate(items)
assert not result.is_valid, f"应该验证失败，但结果: {result}"
assert result.score < 70, f"分数应该 < 70，实际: {result.score}"
assert len(result.issues) >= 2, f"应该有多个问题，实际: {result.issues}"
print("✅ 正确检测多个问题叠加")
print(f"   分数: {result.score}")
print(f"   问题数: {len(result.issues)}")
print(f"   问题: {result.issues}")
sys.stdout.flush()

# 测试 6: 空数据
print("\n测试 6: 空数据")
items = []

result = source.validate(items)
assert not result.is_valid, f"应该验证失败，但结果: {result}"
assert result.score < 50, f"分数应该 < 50，实际: {result.score}"
assert any('数据为空' in issue for issue in result.issues), f"应该包含'数据为空'问题，实际: {result.issues}"
print("✅ 正确处理空数据")
print(f"   分数: {result.score}")
print(f"   问题: {result.issues}")
sys.stdout.flush()

# 测试 7: 边界情况（刚好满足要求）
print("\n测试 7: 边界情况（刚好满足要求）")
items = []
for i in range(5):  # 刚好等于 min_items
    items.append(DataItem(
        id=f'item_{i}',
        source='test_rss',
        category='test',
        title=f'Python 编程技巧 {i}',
        content=f'这是一篇关于 Python 和 coding 的文章 {i}',
        url=f'https://example.com/article{i}',
        published=datetime.now() - timedelta(days=6),  # 刚好在 max_age_days 内
        metadata={}
    ))

result = source.validate(items)
assert result.is_valid, f"应该验证通过，但结果: {result}"
assert result.score >= 90, f"分数应该 >= 90，实际: {result.score}"
assert len(result.issues) == 0, f"应该没有问题，但发现: {result.issues}"
print("✅ 正确处理边界情况")
print(f"   分数: {result.score}")
print(f"   问题数: {len(result.issues)}")
sys.stdout.flush()

print("\n" + "="*80)
print("✅ 测试 1.2.4 通过！")
print("="*80)
sys.stdout.flush()
