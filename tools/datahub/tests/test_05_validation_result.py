#!/usr/bin/env python3
"""
测试 1.1.5: ValidationResult 类
"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.core.base_source import ValidationResult

print("="*80)
print("测试 1.1.5: ValidationResult 类")
print("="*80)
sys.stdout.flush()

# 测试 1: 有效结果
vr1 = ValidationResult(
    is_valid=True,
    score=85,
    issues=[],
    details={'items_count': 20}
)

assert vr1.is_valid == True
assert vr1.score == 85
assert vr1.issues == []
assert vr1.details == {'items_count': 20}

print("✅ 有效结果创建成功")
print(f"   is_valid: {vr1.is_valid}")
print(f"   score: {vr1.score}")
print(f"   issues: {vr1.issues}")
sys.stdout.flush()

# 测试 2: 带问题的结果
vr2 = ValidationResult(
    is_valid=False,
    score=45,
    issues=['数据量不足', '数据过旧'],
    details={'items_count': 2, 'max_age_days': 10}
)

assert vr2.is_valid == False
assert vr2.score == 45
assert len(vr2.issues) == 2
assert '数据量不足' in vr2.issues
assert '数据过旧' in vr2.issues

print("✅ 带问题的结果创建成功")
print(f"   is_valid: {vr2.is_valid}")
print(f"   score: {vr2.score}")
print(f"   issues: {vr2.issues}")
sys.stdout.flush()

# 测试 3: 边界值
vr3 = ValidationResult(
    is_valid=True,
    score=0,  # 最低分
    issues=[],
    details={}
)
assert vr3.score == 0

vr4 = ValidationResult(
    is_valid=True,
    score=100,  # 最高分
    issues=[],
    details={}
)
assert vr4.score == 100

print("✅ 边界值测试成功")
print(f"   最低分: {vr3.score}")
print(f"   最高分: {vr4.score}")
sys.stdout.flush()

print("\n✅ 测试 1.1.5 通过！")
sys.stdout.flush()
