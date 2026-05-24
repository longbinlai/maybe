#!/usr/bin/env python3
"""
测试 1.2.1: RSSSource 初始化（简化版）
"""
print("开始测试")

# 步骤 1: 导入基础模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 步骤 2: 导入 RSSSource（使用延迟导入，避免 yfinance）
try:
    from datahub.sources.rss_source import RSSSource
    print("✅ RSSSource 导入成功")
except Exception as e:
    print(f"❌ RSSSource 导入失败: {e}")
    sys.exit(1)

# 步骤 3: 创建实例
config = {
    'name': 'test_rss',
    'type': 'rss',
    'category': 'test',
    'url': 'https://example.com/rss',
    'priority': 'high',
    'enabled': True,
    'max_items': 20
}

try:
    source = RSSSource('test_rss', config)
    print(f"✅ RSSSource 创建成功: {source.name}")
    print(f"   category: {source.category}")
    print(f"   url: {source.url}")
    print(f"   max_items: {source.max_items}")
except Exception as e:
    print(f"❌ RSSSource 创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ 测试通过！")
