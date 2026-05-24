#!/usr/bin/env python3
"""
Phase 1: 单元测试
1.1 DataItem 类测试
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_dataitem_basic():
    """测试 1.1.1: DataItem 基本创建"""
    print("\n" + "="*80)
    print("测试 1.1.1: DataItem 基本创建")
    print("="*80)
    
    from datahub.core.base_source import DataItem
    
    item = DataItem(
        id="test_001",
        source="test_source",
        category="test_category",
        title="测试标题",
        content="测试内容",
        url="https://example.com/test",
        published=datetime(2024, 1, 1, 12, 0, 0)
    )
    
    assert item.id == "test_001"
    assert item.source == "test_source"
    assert item.category == "test_category"
    assert item.title == "测试标题"
    assert item.content == "测试内容"
    assert item.url == "https://example.com/test"
    assert item.published == datetime(2024, 1, 1, 12, 0, 0)
    assert item.metadata == {}  # 默认空字典
    
    print("✅ 基本创建成功")
    print(f"   ID: {item.id}")
    print(f"   标题: {item.title}")
    print(f"   元数据: {item.metadata}")
    return True


def test_dataitem_with_metadata():
    """测试 1.1.2: DataItem 带元数据"""
    print("\n" + "="*80)
    print("测试 1.1.2: DataItem 带元数据")
    print("="*80)
    
    from datahub.core.base_source import DataItem
    
    item = DataItem(
        id="test_002",
        source="yfinance",
        category="forex",
        title="USD/CNY 汇率",
        content="美元兑人民币汇率",
        url="https://finance.yahoo.com",
        published=datetime.now(),
        metadata={
            'ticker': 'CNY=X',
            'price': 7.25,
            'change_pct': 0.15,
            'volume': 1000000
        }
    )
    
    assert item.metadata['ticker'] == 'CNY=X'
    assert item.metadata['price'] == 7.25
    assert item.metadata['change_pct'] == 0.15
    assert item.metadata['volume'] == 1000000
    
    print("✅ 带元数据创建成功")
    print(f"   Ticker: {item.metadata['ticker']}")
    print(f"   Price: {item.metadata['price']}")
    print(f"   Change: {item.metadata['change_pct']}%")
    return True


def test_dataitem_to_dict():
    """测试 1.1.3: DataItem 序列化"""
    print("\n" + "="*80)
    print("测试 1.1.3: DataItem 序列化")
    print("="*80)
    
    from datahub.core.base_source import DataItem
    
    item = DataItem(
        id="test_003",
        source="rss",
        category="central_bank",
        title="美联储利率决议",
        content="美联储宣布维持利率不变",
        url="https://federalreserve.gov",
        published=datetime(2024, 1, 15, 14, 30, 0),
        metadata={'author': 'Federal Reserve'}
    )
    
    data = item.to_dict()
    
    # 验证所有字段
    assert data['id'] == "test_003"
    assert data['source'] == "rss"
    assert data['category'] == "central_bank"
    assert data['title'] == "美联储利率决议"
    assert data['content'] == "美联储宣布维持利率不变"
    assert data['url'] == "https://federalreserve.gov"
    assert data['published'] == "2024-01-15T14:30:00"  # ISO 格式
    assert data['metadata'] == {'author': 'Federal Reserve'}
    
    print("✅ 序列化成功")
    print(f"   字段数: {len(data)}")
    print(f"   字段: {list(data.keys())}")
    print(f"   发布时间格式: {data['published']}")
    return True


def test_dataitem_generate_id():
    """测试 1.1.4: DataItem ID 生成"""
    print("\n" + "="*80)
    print("测试 1.1.4: DataItem ID 生成")
    print("="*80)
    
    from datahub.core.base_source import DataItem
    
    # 测试相同输入生成相同 ID
    id1 = DataItem.generate_id("source1", "url1", "title1")
    id2 = DataItem.generate_id("source1", "url1", "title1")
    assert id1 == id2
    
    # 测试不同输入生成不同 ID
    id3 = DataItem.generate_id("source2", "url1", "title1")
    assert id1 != id3
    
    # 测试 ID 格式（MD5 前 12 位）
    assert len(id1) == 12
    assert all(c in '0123456789abcdef' for c in id1)
    
    print("✅ ID 生成成功")
    print(f"   ID1: {id1}")
    print(f"   ID2: {id2}")
    print(f"   ID3: {id3}")
    print(f"   ID1 == ID2: {id1 == id2}")
    print(f"   ID1 != ID3: {id1 != id3}")
    return True


def test_dataitem_empty_content():
    """测试 1.1.5: DataItem 空内容处理"""
    print("\n" + "="*80)
    print("测试 1.1.5: DataItem 空内容处理")
    print("="*80)
    
    from datahub.core.base_source import DataItem
    
    # 空标题
    item1 = DataItem(
        id="test_005a",
        source="test",
        category="test",
        title="",
        content="内容",
        url="https://example.com",
        published=datetime.now()
    )
    assert item1.title == ""
    
    # 空内容
    item2 = DataItem(
        id="test_005b",
        source="test",
        category="test",
        title="标题",
        content="",
        url="https://example.com",
        published=datetime.now()
    )
    assert item2.content == ""
    
    # 空元数据
    item3 = DataItem(
        id="test_005c",
        source="test",
        category="test",
        title="标题",
        content="内容",
        url="https://example.com",
        published=datetime.now(),
        metadata={}
    )
    assert item3.metadata == {}
    
    print("✅ 空内容处理成功")
    print(f"   空标题: '{item1.title}'")
    print(f"   空内容: '{item2.content}'")
    print(f"   空元数据: {item3.metadata}")
    return True


def test_dataitem_special_characters():
    """测试 1.1.6: DataItem 特殊字符处理"""
    print("\n" + "="*80)
    print("测试 1.1.6: DataItem 特殊字符处理")
    print("="*80)
    
    from datahub.core.base_source import DataItem
    
    item = DataItem(
        id="test_006",
        source="test",
        category="test",
        title="测试 '引号' \"双引号\" & 符号 <标签>",
        content="内容包含\n换行\t制表符\r回车",
        url="https://example.com/path?param=value&foo=bar#anchor",
        published=datetime.now(),
        metadata={
            'key_with_underscore': 'value',
            'key-with-dash': 'value',
            'key.with.dots': 'value'
        }
    )
    
    # 验证特殊字符被正确保存
    assert "'" in item.title
    assert '"' in item.title
    assert '&' in item.title
    assert '<' in item.title
    assert '\n' in item.content
    assert '\t' in item.content
    assert '?' in item.url
    assert '&' in item.url
    assert '#' in item.url
    
    # 验证序列化
    data = item.to_dict()
    assert data['title'] == item.title
    assert data['content'] == item.content
    assert data['url'] == item.url
    
    print("✅ 特殊字符处理成功")
    print(f"   标题: {item.title}")
    print(f"   内容长度: {len(item.content)}")
    print(f"   URL: {item.url}")
    return True


def test_dataitem_unicode():
    """测试 1.1.7: DataItem Unicode 字符"""
    print("\n" + "="*80)
    print("测试 1.1.7: DataItem Unicode 字符")
    print("="*80)
    
    from datahub.core.base_source import DataItem
    
    item = DataItem(
        id="test_007",
        source="test",
        category="test",
        title="测试中文、日文、한글、العربية、עברית、🎉🎊",
        content="多语言内容: 中文 日本語 한국어 العربية עברית 🚀",
        url="https://example.com",
        published=datetime.now(),
        metadata={'emoji': '🎉🎊🚀'}
    )
    
    # 验证 Unicode 字符
    assert '中文' in item.title
    assert '日本語' in item.content
    assert '한국어' in item.content
    assert 'العربية' in item.content
    assert '🎉' in item.title
    assert '🚀' in item.content
    
    # 验证序列化
    data = item.to_dict()
    assert data['title'] == item.title
    assert data['metadata']['emoji'] == '🎉🎊🚀'
    
    print("✅ Unicode 字符处理成功")
    print(f"   标题: {item.title}")
    print(f"   表情: {item.metadata['emoji']}")
    return True


def test_dataitem_long_content():
    """测试 1.1.8: DataItem 长内容处理"""
    print("\n" + "="*80)
    print("测试 1.1.8: DataItem 长内容处理")
    print("="*80)
    
    from datahub.core.base_source import DataItem
    
    # 生成 10000 字符的长内容
    long_content = "这是一段很长的内容。" * 1000
    
    item = DataItem(
        id="test_008",
        source="test",
        category="test",
        title="长内容测试",
        content=long_content,
        url="https://example.com",
        published=datetime.now()
    )
    
    assert len(item.content) == 10000
    
    # 验证序列化
    data = item.to_dict()
    assert len(data['content']) == 10000
    
    print("✅ 长内容处理成功")
    print(f"   内容长度: {len(item.content)} 字符")
    print(f"   序列化后长度: {len(data['content'])} 字符")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("Phase 1.1: DataItem 类测试")
    print("="*80)
    
    tests = [
        test_dataitem_basic,
        test_dataitem_with_metadata,
        test_dataitem_to_dict,
        test_dataitem_generate_id,
        test_dataitem_empty_content,
        test_dataitem_special_characters,
        test_dataitem_unicode,
        test_dataitem_long_content,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result, None))
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False, str(e)))
    
    # 汇总结果
    print("\n" + "="*80)
    print("Phase 1.1 测试汇总")
    print("="*80)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
        if error:
            print(f"   错误: {error}")
    
    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
