#!/usr/bin/env python3
"""
测试 1.2.2: RSSSource._parse_entry() 方法
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.sources.rss_source import RSSSource
from datetime import datetime

print("="*80)
print("测试 1.2.2: RSSSource._parse_entry() 方法")
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

# 测试 1: 正常条目解析
print("\n测试 1: 正常条目解析")
entry = {
    'title': '测试标题',
    'link': 'https://example.com/article1',
    'summary': '测试摘要内容',
    'description': '测试描述内容',
    'published_parsed': (2024, 1, 15, 10, 30, 0, 0, 0, 0),
    'author': '张三',
    'tags': [{'term': 'tag1'}, {'term': 'tag2'}]
}

item = source._parse_entry(entry)
assert item is not None, "条目解析失败"
assert item.title == '测试标题', f"标题不匹配: {item.title}"
assert item.url == 'https://example.com/article1', f"URL 不匹配: {item.url}"
assert item.content == '测试摘要内容', f"内容不匹配: {item.content}"
assert item.metadata.get('author') == '张三', f"作者不匹配: {item.metadata.get('author')}"
assert 'tag1' in item.metadata.get('tags', []), f"标签不匹配: {item.metadata.get('tags')}"
print("✅ 正常条目解析成功")
print(f"   标题: {item.title}")
print(f"   URL: {item.url}")
print(f"   作者: {item.metadata.get('author')}")
print(f"   标签: {item.metadata.get('tags')}")
sys.stdout.flush()

# 测试 2: 缺少标题
print("\n测试 2: 缺少标题")
entry_no_title = {
    'link': 'https://example.com/article2',
    'summary': '测试摘要'
}
item = source._parse_entry(entry_no_title)
assert item is None, "应该返回 None"
print("✅ 正确处理缺少标题的条目")
sys.stdout.flush()

# 测试 3: 缺少链接
print("\n测试 3: 缺少链接")
entry_no_link = {
    'title': '测试标题',
    'summary': '测试摘要'
}
item = source._parse_entry(entry_no_link)
assert item is None, "应该返回 None"
print("✅ 正确处理缺少链接的条目")
sys.stdout.flush()

# 测试 4: 使用 description 而不是 summary
print("\n测试 4: 使用 description 而不是 summary")
entry_desc = {
    'title': '测试标题',
    'link': 'https://example.com/article3',
    'description': '这是描述内容'
}
item = source._parse_entry(entry_desc)
assert item is not None, "条目解析失败"
assert item.content == '这是描述内容', f"内容不匹配: {item.content}"
print("✅ 正确使用 description 字段")
sys.stdout.flush()

# 测试 5: 缺少日期（使用当前时间）
print("\n测试 5: 缺少日期（使用当前时间）")
entry_no_date = {
    'title': '测试标题',
    'link': 'https://example.com/article4',
    'summary': '测试摘要'
}
item = source._parse_entry(entry_no_date)
assert item is not None, "条目解析失败"
assert item.published is not None, "日期应该使用当前时间"
# 检查日期是否在最近 1 分钟内
now = datetime.now()
time_diff = abs((now - item.published).total_seconds())
assert time_diff < 60, f"日期差异过大: {time_diff} 秒"
print("✅ 正确处理缺少日期的条目")
print(f"   使用当前时间: {item.published}")
sys.stdout.flush()

# 测试 6: 元数据提取
print("\n测试 6: 元数据提取")
entry_meta = {
    'title': '测试标题',
    'link': 'https://example.com/article5',
    'summary': '测试摘要',
    'author': '李四',
    'tags': [{'term': 'news'}, {'term': 'tech'}, {'term': 'ai'}]
}
item = source._parse_entry(entry_meta)
assert item is not None, "条目解析失败"
assert item.metadata.get('author') == '李四', f"作者不匹配: {item.metadata.get('author')}"
assert len(item.metadata.get('tags', [])) == 3, f"标签数量不匹配: {len(item.metadata.get('tags', []))}"
assert 'news' in item.metadata.get('tags', []), f"标签不匹配: {item.metadata.get('tags')}"
assert 'tech' in item.metadata.get('tags', []), f"标签不匹配: {item.metadata.get('tags')}"
assert 'ai' in item.metadata.get('tags', []), f"标签不匹配: {item.metadata.get('tags')}"
print("✅ 正确提取元数据")
print(f"   作者: {item.metadata.get('author')}")
print(f"   标签: {item.metadata.get('tags')}")
sys.stdout.flush()

# 测试 7: 空内容
print("\n测试 7: 空内容")
entry_empty = {
    'title': '测试标题',
    'link': 'https://example.com/article6',
    'summary': '',
    'description': ''
}
item = source._parse_entry(entry_empty)
assert item is not None, "条目解析失败"
assert item.content == '', f"内容应该为空字符串: {item.content}"
print("✅ 正确处理空内容")
sys.stdout.flush()

print("\n" + "="*80)
print("✅ 测试 1.2.2 通过！")
print("="*80)
sys.stdout.flush()
