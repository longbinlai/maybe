#!/usr/bin/env python3
"""
最最简单的测试 - 不使用任何导入，带 flush
"""
import sys

print("="*80)
print("测试 0: Python 基本功能")
print("="*80)
sys.stdout.flush()

print("✅ Python 启动成功")
print(f"   Python 版本: {sys.version}")
sys.stdout.flush()

print("\n" + "="*80)
print("测试 1: dataclasses 导入")
print("="*80)
sys.stdout.flush()

from dataclasses import dataclass
print("✅ dataclasses 导入成功")
sys.stdout.flush()

print("\n" + "="*80)
print("测试 2: 创建简单 dataclass")
print("="*80)
sys.stdout.flush()

@dataclass
class SimpleItem:
    id: str
    name: str
    
item = SimpleItem(id="001", name="测试")
print(f"✅ 创建成功: {item}")
sys.stdout.flush()

print("\n" + "="*80)
print("测试 3: datetime 导入")
print("="*80)
sys.stdout.flush()

from datetime import datetime
now = datetime.now()
print(f"✅ datetime 导入成功: {now}")
sys.stdout.flush()

print("\n" + "="*80)
print("测试 4: 读取 base_source.py")
print("="*80)
sys.stdout.flush()

with open('../datahub/core/base_source.py', 'r', encoding='utf-8') as f:
    code = f.read()
print(f"✅ 文件读取成功，{len(code)} 字节")
sys.stdout.flush()

print("\n" + "="*80)
print("测试 5: 编译 base_source.py")
print("="*80)
sys.stdout.flush()

compiled = compile(code, 'base_source.py', 'exec')
print(f"✅ 代码编译成功")
sys.stdout.flush()

print("\n" + "="*80)
print("测试 6: 执行 base_source.py")
print("="*80)
sys.stdout.flush()

exec(compiled)
print(f"✅ 代码执行成功")
sys.stdout.flush()

print("\n" + "="*80)
print("测试 7: 访问 DataItem")
print("="*80)
sys.stdout.flush()

print(f"✅ DataItem 类: {DataItem}")
print(f"✅ ValidationResult 类: {ValidationResult}")
sys.stdout.flush()

print("\n" + "="*80)
print("测试 8: 创建 DataItem 实例")
print("="*80)
sys.stdout.flush()

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
sys.stdout.flush()

print("\n" + "="*80)
print("所有基础测试通过！✅")
print("="*80)
sys.stdout.flush()
