#!/usr/bin/env python3
"""
测试 1.2.3: RSSSource._parse_date() 方法
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.sources.rss_source import RSSSource

print("="*80)
print("测试 1.2.3: RSSSource._parse_date() 方法")
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
    'max_items': 20
}
source = RSSSource('test_rss', config)
print("✅ RSSSource 实例创建成功")
sys.stdout.flush()

# 测试 1: published_parsed 格式（feedparser 解析后的时间元组）
print("\n测试 1: published_parsed 格式")
entry = {
    'title': '测试标题',
    'link': 'https://example.com/article1',
    'summary': '测试摘要',
    'published_parsed': (2024, 1, 15, 10, 30, 0, 0, 0, 0)  # 2024-01-15 10:30:00
}
item = source._parse_entry(entry)
assert item is not None, "条目解析失败"
assert item.published.year == 2024, f"年份不匹配: {item.published.year}"
assert item.published.month == 1, f"月份不匹配: {item.published.month}"
assert item.published.day == 15, f"日期不匹配: {item.published.day}"
assert item.published.hour == 10, f"小时不匹配: {item.published.hour}"
assert item.published.minute == 30, f"分钟不匹配: {item.published.minute}"
print("✅ 正确解析 published_parsed 格式")
print(f"   解析结果: {item.published}")
sys.stdout.flush()

# 测试 2: updated_parsed 格式（当 published_parsed 不存在时使用）
print("\n测试 2: updated_parsed 格式")
entry = {
    'title': '测试标题',
    'link': 'https://example.com/article2',
    'summary': '测试摘要',
    'updated_parsed': (2024, 2, 20, 14, 45, 0, 0, 0, 0)  # 2024-02-20 14:45:00
}
item = source._parse_entry(entry)
assert item is not None, "条目解析失败"
assert item.published.year == 2024, f"年份不匹配: {item.published.year}"
assert item.published.month == 2, f"月份不匹配: {item.published.month}"
assert item.published.day == 20, f"日期不匹配: {item.published.day}"
assert item.published.hour == 14, f"小时不匹配: {item.published.hour}"
assert item.published.minute == 45, f"分钟不匹配: {item.published.minute}"
print("✅ 正确解析 updated_parsed 格式")
print(f"   解析结果: {item.published}")
sys.stdout.flush()

# 测试 3: published 字符串格式（RFC 822）
print("\n测试 3: published 字符串格式（RFC 822）")
entry = {
    'title': '测试标题',
    'link': 'https://example.com/article3',
    'summary': '测试摘要',
    'published': 'Mon, 15 Jan 2024 10:30:00 +0000'
}
item = source._parse_entry(entry)
assert item is not None, "条目解析失败"
assert item.published.year == 2024, f"年份不匹配: {item.published.year}"
assert item.published.month == 1, f"月份不匹配: {item.published.month}"
assert item.published.day == 15, f"日期不匹配: {item.published.day}"
print("✅ 正确解析 RFC 822 格式")
print(f"   解析结果: {item.published}")
sys.stdout.flush()

# 测试 4: published 字符串格式（ISO 8601）
print("\n测试 4: published 字符串格式（ISO 8601）")
entry = {
    'title': '测试标题',
    'link': 'https://example.com/article4',
    'summary': '测试摘要',
    'published': '2024-03-10T08:15:00+08:00'
}
item = source._parse_entry(entry)
assert item is not None, "条目解析失败"
assert item.published.year == 2024, f"年份不匹配: {item.published.year}"
assert item.published.month == 3, f"月份不匹配: {item.published.month}"
assert item.published.day == 10, f"日期不匹配: {item.published.day}"
print("✅ 正确解析 ISO 8601 格式")
print(f"   解析结果: {item.published}")
sys.stdout.flush()

# 测试 5: 缺少日期（使用当前时间）
print("\n测试 5: 缺少日期（使用当前时间）")
entry = {
    'title': '测试标题',
    'link': 'https://example.com/article5',
    'summary': '测试摘要'
}
item = source._parse_entry(entry)
assert item is not None, "条目解析失败"
assert item.published is not None, "日期应该使用当前时间"
# 检查日期是否在最近 1 分钟内
now = datetime.now()
time_diff = abs((now - item.published).total_seconds())
assert time_diff < 60, f"日期差异过大: {time_diff} 秒"
print("✅ 正确使用当前时间作为默认日期")
print(f"   当前时间: {item.published}")
sys.stdout.flush()

# 测试 6: published_parsed 优先级高于 updated_parsed
print("\n测试 6: published_parsed 优先级高于 updated_parsed")
entry = {
    'title': '测试标题',
    'link': 'https://example.com/article6',
    'summary': '测试摘要',
    'published_parsed': (2024, 1, 15, 10, 30, 0, 0, 0, 0),
    'updated_parsed': (2024, 2, 20, 14, 45, 0, 0, 0, 0)
}
item = source._parse_entry(entry)
assert item is not None, "条目解析失败"
# 应该使用 published_parsed
assert item.published.month == 1, f"应该使用 published_parsed，但月份是: {item.published.month}"
print("✅ 正确使用 published_parsed（优先级高于 updated_parsed）")
print(f"   解析结果: {item.published}")
sys.stdout.flush()

# 测试 7: 无效的日期字符串（使用当前时间）
print("\n测试 7: 无效的日期字符串（使用当前时间）")
entry = {
    'title': '测试标题',
    'link': 'https://example.com/article7',
    'summary': '测试摘要',
    'published': 'invalid date format'
}
item = source._parse_entry(entry)
assert item is not None, "条目解析失败"
assert item.published is not None, "日期应该使用当前时间"
# 检查日期是否在最近 1 分钟内
now = datetime.now()
time_diff = abs((now - item.published).total_seconds())
assert time_diff < 60, f"日期差异过大: {time_diff} 秒"
print("✅ 正确处理无效日期字符串（使用当前时间）")
print(f"   当前时间: {item.published}")
sys.stdout.flush()

print("\n" + "="*80)
print("✅ 测试 1.2.3 通过！")
print("="*80)
sys.stdout.flush()
