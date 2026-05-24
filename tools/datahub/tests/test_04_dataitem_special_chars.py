#!/usr/bin/env python3
"""
测试 1.1.4: DataItem 特殊字符和 Unicode
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.core.base_source import DataItem

print("="*80)
print("测试 1.1.4: DataItem 特殊字符和 Unicode")
print("="*80)
sys.stdout.flush()

# 测试特殊字符
item1 = DataItem(
    id="test_005",
    source="test",
    category="test",
    title="测试 '引号' \"双引号\" & 符号 <标签>",
    content="内容包含\n换行\t制表符\r回车",
    url="https://example.com/path?param=value&foo=bar#anchor",
    published=datetime.now(),
    metadata={
        'key_with_underscore': 'value',
        'key-with-dash': 'value',
        'key.with.dots': 'value'
    }
)

assert "'" in item1.title
assert '"' in item1.title
assert '&' in item1.title
assert '<' in item1.title
assert '\n' in item1.content
assert '\t' in item1.content
assert '?' in item1.url
assert '&' in item1.url
assert '#' in item1.url

data1 = item1.to_dict()
assert data1['title'] == item1.title
assert data1['content'] == item1.content
assert data1['url'] == item1.url

print("✅ 特殊字符处理成功")
print(f"   标题: {item1.title}")
print(f"   内容长度: {len(item1.content)}")
print(f"   URL: {item1.url}")
sys.stdout.flush()

# 测试 Unicode 字符
item2 = DataItem(
    id="test_006",
    source="test",
    category="test",
    title="测试中文、日文、한글、العربية、עברית、🎉🎊",
    content="多语言内容: 中文 日本語 한국어 العربية עברית 🚀",
    url="https://example.com",
    published=datetime.now(),
    metadata={'emoji': '🎉🎊🚀'}
)

assert '中文' in item2.title
assert '日本語' in item2.content
assert '한국어' in item2.content
assert 'العربية' in item2.content
assert '🎉' in item2.title
assert '🚀' in item2.content

data2 = item2.to_dict()
assert data2['title'] == item2.title
assert data2['metadata']['emoji'] == '🎉🎊🚀'

print("✅ Unicode 字符处理成功")
print(f"   标题: {item2.title}")
print(f"   表情: {item2.metadata['emoji']}")
sys.stdout.flush()

print("\n✅ 测试 1.1.4 通过！")
sys.stdout.flush()
