#!/usr/bin/env python3
"""
测试 1.2: RSSSource 单元测试

使用 subprocess 运行每个测试，避免导入链问题
"""
import subprocess
import sys
from pathlib import Path

# 测试文件列表
test_files = [
    'test_07_rss_init.py',
]

print("="*80)
print("Phase 1.2: RSSSource 单元测试")
print("="*80)
print()

# 运行每个测试
results = []
for test_file in test_files:
    test_path = Path(__file__).parent / test_file
    if not test_path.exists():
        print(f"⚠️  测试文件不存在: {test_file}")
        results.append((test_file, 'skipped'))
        continue
    
    print(f"运行 {test_file}...")
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ {test_file} 通过")
            print(result.stdout)
            results.append((test_file, 'passed'))
        else:
            print(f"❌ {test_file} 失败")
            print(result.stdout)
            print(result.stderr)
            results.append((test_file, 'failed'))
    except subprocess.TimeoutExpired:
        print(f"⏱️  {test_file} 超时")
        results.append((test_file, 'timeout'))
    except Exception as e:
        print(f"❌ {test_file} 异常: {e}")
        results.append((test_file, 'error'))
    
    print()

# 汇总结果
print("="*80)
print("测试汇总")
print("="*80)
passed = sum(1 for _, status in results if status == 'passed')
failed = sum(1 for _, status in results if status == 'failed')
skipped = sum(1 for _, status in results if status == 'skipped')
timeout = sum(1 for _, status in results if status == 'timeout')
error = sum(1 for _, status in results if status == 'error')

for test_file, status in results:
    print(f"{test_file}: {status}")

print()
print(f"总计: {len(results)} 个测试")
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print(f"⚠️  跳过: {skipped}")
print(f"⏱️  超时: {timeout}")
print(f"❗ 异常: {error}")

# 退出码
if failed > 0 or error > 0:
    sys.exit(1)
else:
    sys.exit(0)
