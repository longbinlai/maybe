#!/usr/bin/env python3
"""
测试 1.1.3: DataItem ID 生成
"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.core.base_source import DataItem

print("="*80)
print("测试 1.1.3: DataItem ID 生成")
print("="*80)
sys.stdout.flush()

# 测试相同输入生成相同 ID
id1 = DataItem.generate_id("source1", "url1", "title1")
id2 = DataItem.generate_id("source1", "url1", "title1")
assert id1 == id2, "相同输入应该生成相同 ID"

# 测试不同输入生成不同 ID
id3 = DataItem.generate_id("source2", "url1", "title1")
assert id1 != id3, "不同 source 应该生成不同 ID"

id4 = DataItem.generate_id("source1", "url2", "title1")
assert id1 != id4, "不同 url 应该生成不同 ID"

id5 = DataItem.generate_id("source1", "url1", "title2")
assert id1 != id5, "不同 title 应该生成不同 ID"

# 测试 ID 格式（MD5 前 12 位）
assert len(id1) == 12, f"ID 长度应该是 12，实际是 {len(id1)}"
assert all(c in '0123456789abcdef' for c in id1), "ID 应该只包含十六进制字符"

print("✅ ID 生成成功")
print(f"   ID1: {id1}")
print(f"   ID2: {id2}")
print(f"   ID3: {id3}")
print(f"   ID1 == ID2: {id1 == id2}")
print(f"   ID1 != ID3: {id1 != id3}")
sys.stdout.flush()

# 测试 Unicode 字符
id_unicode = DataItem.generate_id("中文", "https://例子.com", "标题")
assert len(id_unicode) == 12
print(f"   Unicode ID: {id_unicode}")
sys.stdout.flush()

print("\n✅ 测试 1.1.3 通过！")
sys.stdout.flush()
