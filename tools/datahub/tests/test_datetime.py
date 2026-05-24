#!/usr/bin/env python3
"""
测试 datetime 是否有问题
"""
import sys

print("步骤 1: 导入 datetime")
sys.stdout.flush()

from datetime import datetime
print("✅ 导入成功")
sys.stdout.flush()

print("步骤 2: 创建固定时间")
dt1 = datetime(2024, 1, 1, 12, 0, 0)
print(f"✅ 固定时间: {dt1}")
sys.stdout.flush()

print("步骤 3: 调用 now()")
dt2 = datetime.now()
print("✅ now() 调用成功（不打印值）")
sys.stdout.flush()

print("步骤 4: 打印 now() 的值")
print(f"✅ now() 值: {dt2}")
sys.stdout.flush()

print("\n所有 datetime 测试通过！")
sys.stdout.flush()
