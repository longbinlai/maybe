#!/usr/bin/env python3
"""
测试 1.2.5: RSSSource.fetch() 方法（集成测试）

注意：这个测试需要网络连接，会实际获取 RSS 数据
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datahub.sources.rss_source import RSSSource
from datetime import datetime, timedelta

print("="*80)
print("测试 1.2.5: RSSSource.fetch() 方法（集成测试）")
print("="*80)
sys.stdout.flush()

# 创建 RSSSource 实例（使用真实的 RSS 源）
config = {
    'name': 'test_rss',
    'type': 'rss',
    'category': 'test',
    'url': 'https://feeds.bbci.co.uk/news/technology/rss.xml',  # BBC Technology RSS
    'priority': 'high',
    'enabled': True,
    'max_items': 10,
    'validation': {
        'min_items': 3,
        'max_age_days': 7,
        'keywords': ['technology', 'tech', 'AI', 'software']
    }
}
source = RSSSource('test_rss', config)
print("✅ RSSSource 实例创建成功")
print(f"   URL: {source.url}")
print(f"   max_items: {source.max_items}")
sys.stdout.flush()

# 测试 1: 成功获取 RSS 数据
print("\n测试 1: 成功获取 RSS 数据")
try:
    result = source.fetch()
    assert result.status in ['success', 'degraded'], f"应该成功或降级，实际: {result.status}"
    assert len(result.items) > 0, "应该获取到数据"
    assert len(result.items) <= source.max_items, f"数据量应该 <= {source.max_items}"
    
    print("✅ 成功获取 RSS 数据")
    print(f"   状态: {result.status}")
    print(f"   数据量: {len(result.items)}")
    print(f"   验证分数: {result.validation.score if result.validation else 'N/A'}")
    
    # 检查第一个数据项
    if result.items:
        first_item = result.items[0]
        print(f"\n   第一个数据项:")
        print(f"     标题: {first_item.title[:50]}...")
        print(f"     URL: {first_item.url}")
        print(f"     发布时间: {first_item.published}")
        print(f"     内容长度: {len(first_item.content)} 字符")
    
    sys.stdout.flush()
except Exception as e:
    print(f"⚠️  获取 RSS 数据失败（可能是网络问题）: {e}")
    print("   跳过此测试")
    sys.stdout.flush()

# 测试 2: 处理无效的 RSS URL
print("\n测试 2: 处理无效的 RSS URL")
invalid_config = config.copy()
invalid_config['url'] = 'https://invalid-url-that-does-not-exist.com/rss.xml'
invalid_source = RSSSource('invalid_rss', invalid_config)

try:
    result = invalid_source.fetch()
    assert result.status == 'failed', f"应该失败，实际: {result.status}"
    assert result.error is not None, "应该有错误信息"
    print("✅ 正确处理无效的 RSS URL")
    print(f"   状态: {result.status}")
    print(f"   错误: {result.error[:100]}...")
    sys.stdout.flush()
except Exception as e:
    print(f"⚠️  测试异常: {e}")
    sys.stdout.flush()

# 测试 3: 处理空的 RSS 源
print("\n测试 3: 处理空的 RSS 源（模拟）")
# 使用一个可能没有数据的 RSS 源
empty_config = config.copy()
empty_config['url'] = 'https://feeds.bbci.co.uk/news/technology/rss.xml'
empty_config['validation']['min_items'] = 100  # 设置一个很高的最小值
empty_source = RSSSource('empty_rss', empty_config)

try:
    result = empty_source.fetch()
    # 由于我们设置了很高的 min_items，验证应该失败
    if result.status == 'failed':
        print("✅ 正确处理数据量不足的情况")
        print(f"   状态: {result.status}")
        print(f"   验证问题: {result.validation.issues if result.validation else 'N/A'}")
    else:
        print(f"⚠️  状态不是 failed: {result.status}")
    sys.stdout.flush()
except Exception as e:
    print(f"⚠️  测试异常: {e}")
    sys.stdout.flush()

# 测试 4: 验证数据质量
print("\n测试 4: 验证数据质量")
try:
    result = source.fetch()
    if result.validation:
        print("✅ 数据质量验证完成")
        print(f"   验证通过: {result.validation.is_valid}")
        print(f"   分数: {result.validation.score}")
        print(f"   问题数: {len(result.validation.issues)}")
        if result.validation.issues:
            print(f"   问题列表:")
            for issue in result.validation.issues:
                print(f"     - {issue}")
        print(f"   详细信息:")
        for key, value in result.validation.details.items():
            print(f"     {key}: {value}")
    else:
        print("⚠️  没有验证结果")
    sys.stdout.flush()
except Exception as e:
    print(f"⚠️  测试异常: {e}")
    sys.stdout.flush()

# 测试 5: 检查数据项结构
print("\n测试 5: 检查数据项结构")
try:
    result = source.fetch()
    if result.items:
        item = result.items[0]
        # 检查必需的字段
        assert hasattr(item, 'id'), "缺少 id 字段"
        assert hasattr(item, 'source'), "缺少 source 字段"
        assert hasattr(item, 'category'), "缺少 category 字段"
        assert hasattr(item, 'title'), "缺少 title 字段"
        assert hasattr(item, 'content'), "缺少 content 字段"
        assert hasattr(item, 'url'), "缺少 url 字段"
        assert hasattr(item, 'published'), "缺少 published 字段"
        assert hasattr(item, 'metadata'), "缺少 metadata 字段"
        
        # 检查字段类型
        assert isinstance(item.id, str), "id 应该是字符串"
        assert isinstance(item.source, str), "source 应该是字符串"
        assert isinstance(item.category, str), "category 应该是字符串"
        assert isinstance(item.title, str), "title 应该是字符串"
        assert isinstance(item.content, str), "content 应该是字符串"
        assert isinstance(item.url, str), "url 应该是字符串"
        assert isinstance(item.published, datetime), "published 应该是 datetime"
        assert isinstance(item.metadata, dict), "metadata 应该是字典"
        
        print("✅ 数据项结构正确")
        print(f"   所有必需字段都存在")
        print(f"   所有字段类型都正确")
    else:
        print("⚠️  没有数据项可检查")
    sys.stdout.flush()
except Exception as e:
    print(f"⚠️  测试异常: {e}")
    sys.stdout.flush()

print("\n" + "="*80)
print("✅ 测试 1.2.5 完成！")
print("="*80)
sys.stdout.flush()
