#!/usr/bin/env python3
import sys

print("步骤 1: 开始", flush=True)

try:
    print("步骤 2: 导入 feedparser", flush=True)
    import feedparser
    print(f"步骤 3: 导入成功，版本: {getattr(feedparser, '__version__', 'unknown')}", flush=True)
except Exception as e:
    print(f"步骤 3: 导入失败: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("步骤 4: 完成", flush=True)
