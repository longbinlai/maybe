#!/usr/bin/env python3
"""
批量运行所有 Phase 1.1 测试
"""
import sys
import subprocess
from pathlib import Path

tests_dir = Path(__file__).parent
test_files = sorted(tests_dir.glob('test_0*.py'))

print("="*80)
print("Phase 1.1: DataItem 类单元测试")
print("="*80)
print(f"\n找到 {len(test_files)} 个测试文件\n")
sys.stdout.flush()

results = []

for test_file in test_files:
    print("="*80)
    print(f"运行: {test_file.name}")
    print("="*80)
    sys.stdout.flush()
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        results.append((test_file.name, success, None))
        
        if success:
            print(f"✅ {test_file.name} 通过\n")
        else:
            print(f"❌ {test_file.name} 失败\n")
        
    except subprocess.TimeoutExpired:
        print(f"❌ {test_file.name} 超时\n")
        results.append((test_file.name, False, "超时"))
    except Exception as e:
        print(f"❌ {test_file.name} 异常: {e}\n")
        results.append((test_file.name, False, str(e)))
    
    sys.stdout.flush()

# 汇总结果
print("\n" + "="*80)
print("测试汇总")
print("="*80)

passed = sum(1 for _, success, _ in results if success)
failed = sum(1 for _, success, _ in results if not success)

for name, success, error in results:
    status = "✅ 通过" if success else "❌ 失败"
    print(f"{status} - {name}")
    if error:
        print(f"   错误: {error}")

print(f"\n总计: {passed}/{len(results)} 通过, {failed}/{len(results)} 失败")
sys.stdout.flush()

sys.exit(0 if failed == 0 else 1)
