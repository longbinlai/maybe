#!/usr/bin/env python3
"""
调试脚本：查看 DataHub 返回的原始数据结构
"""

import sys
import os
import json
from pathlib import Path

# Add datahub to path
DATAHUB_PATH = Path(__file__).parent.parent.parent.parent / "datahub"
sys.path.insert(0, str(DATAHUB_PATH))

from datahub import SourceRegistry

def main():
    config_path = DATAHUB_PATH / "config" / "sources.yaml"
    registry = SourceRegistry(config_path)
    
    print("🔄 收集数据...")
    results = registry.fetch_all(use_cache=True)
    
    print("\n" + "="*80)
    print("数据源概览")
    print("="*80)
    
    for source_name, result in results.items():
        print(f"\n📦 {source_name}")
        print(f"   状态: {result.status}")
        print(f"   数据项数: {len(result.items)}")
        
        if result.items:
            print(f"   第一个数据项:")
            item = result.items[0]
            print(f"     - title: {item.title[:80] if len(item.title) > 80 else item.title}")
            print(f"     - metadata keys: {list(item.metadata.keys())}")
            
            # 显示 metadata 内容
            for key, value in item.metadata.items():
                value_str = str(value)
                if len(value_str) > 60:
                    value_str = value_str[:60] + "..."
                print(f"       {key}: {value_str}")

if __name__ == "__main__":
    main()
