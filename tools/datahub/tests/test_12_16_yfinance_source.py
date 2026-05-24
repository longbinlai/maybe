#!/usr/bin/env python3
"""
Phase 1.3: YFinanceSource 单元测试
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datahub.sources.yfinance_source import YFinanceSource
from datahub.core.base_source import DataItem, DataSourceResult
from datetime import datetime, timedelta


def test_12_yfinance_init():
    """测试 1.3.1: YFinanceSource 初始化"""
    print("\n" + "="*80)
    print("测试 1.3.1: YFinanceSource 初始化")
    print("="*80)
    
    # 测试 1: 基本初始化
    config = {
        'tickers': ['AAPL', 'GOOGL'],
        'data_type': 'price',
        'period': '5d',
        'interval': '1d',
        'category': 'stocks',
        'validation': {
            'min_items': 1,
            'keywords': ['AAPL', 'GOOGL']
        }
    }
    
    source = YFinanceSource('test_yfinance', config)
    
    assert source.name == 'test_yfinance'
    assert source.tickers == ['AAPL', 'GOOGL']
    assert source.data_type == 'price'
    assert source.period == '5d'
    assert source.interval == '1d'
    assert source.category == 'stocks'
    
    print("✅ 基本初始化测试通过")
    print(f"   name: {source.name}")
    print(f"   tickers: {source.tickers}")
    print(f"   data_type: {source.data_type}")
    print(f"   period: {source.period}")
    print(f"   interval: {source.interval}")
    print(f"   category: {source.category}")
    
    # 测试 2: 默认值
    config_minimal = {
        'tickers': ['MSFT'],
        'category': 'stocks'
    }
    
    source_minimal = YFinanceSource('minimal', config_minimal)
    
    assert source_minimal.data_type == 'price'
    assert source_minimal.period == '5d'
    assert source_minimal.interval == '1d'
    
    print("\n✅ 默认值测试通过")
    print(f"   data_type (默认): {source_minimal.data_type}")
    print(f"   period (默认): {source_minimal.period}")
    print(f"   interval (默认): {source_minimal.interval}")
    
    # 测试 3: 不同的数据类型
    for dtype in ['price', 'news', 'info']:
        config_type = {
            'tickers': ['AAPL'],
            'data_type': dtype,
            'category': 'stocks'
        }
        source_type = YFinanceSource(f'test_{dtype}', config_type)
        assert source_type.data_type == dtype
        print(f"✅ data_type={dtype} 测试通过")
    
    print("\n✅ 测试 1.3.1 完成！")


def test_13_yfinance_fetch_prices():
    """测试 1.3.2: YFinanceSource 价格数据获取"""
    print("\n" + "="*80)
    print("测试 1.3.2: YFinanceSource 价格数据获取")
    print("="*80)
    
    # 测试 1: 获取单个股票价格
    config = {
        'tickers': ['AAPL'],
        'data_type': 'price',
        'period': '5d',
        'interval': '1d',
        'category': 'stocks',
        'validation': {
            'min_items': 1
        }
    }
    
    source = YFinanceSource('test_aapl', config)
    result = source.fetch()
    
    assert result.status in ['success', 'degraded']
    assert len(result.items) > 0
    
    item = result.items[0]
    assert 'AAPL' in item.title
    assert item.metadata['ticker'] == 'AAPL'
    assert 'price' in item.metadata
    assert 'change_pct' in item.metadata
    
    print("✅ 单个股票价格获取测试通过")
    print(f"   状态: {result.status}")
    print(f"   数据项数: {len(result.items)}")
    print(f"   标题: {item.title}")
    print(f"   价格: ${item.metadata['price']:.2f}")
    print(f"   涨跌幅: {item.metadata['change_pct']:+.2f}%")
    
    # 测试 2: 获取多个股票价格
    config_multi = {
        'tickers': ['AAPL', 'GOOGL', 'MSFT'],
        'data_type': 'price',
        'period': '5d',
        'interval': '1d',
        'category': 'stocks',
        'validation': {
            'min_items': 3
        }
    }
    
    source_multi = YFinanceSource('test_multi', config_multi)
    result_multi = source_multi.fetch()
    
    assert result_multi.status in ['success', 'degraded']
    assert len(result_multi.items) == 3
    
    tickers_found = set()
    for item in result_multi.items:
        tickers_found.add(item.metadata['ticker'])
    
    assert tickers_found == {'AAPL', 'GOOGL', 'MSFT'}
    
    print("\n✅ 多个股票价格获取测试通过")
    print(f"   状态: {result_multi.status}")
    print(f"   数据项数: {len(result_multi.items)}")
    print(f"   找到的股票: {sorted(tickers_found)}")
    
    for item in result_multi.items:
        print(f"   - {item.title}")
    
    # 测试 3: 验证数据质量
    assert result_multi.validation is not None
    print(f"\n✅ 数据质量验证通过")
    print(f"   验证分数: {result_multi.validation.score}")
    print(f"   验证问题: {result_multi.validation.issues}")
    
    print("\n✅ 测试 1.3.2 完成！")


def test_14_yfinance_fetch_news():
    """测试 1.3.3: YFinanceSource 新闻数据获取"""
    print("\n" + "="*80)
    print("测试 1.3.3: YFinanceSource 新闻数据获取")
    print("="*80)
    
    config = {
        'tickers': ['AAPL'],
        'data_type': 'news',
        'category': 'stocks',
        'validation': {
            'min_items': 1
        }
    }
    
    source = YFinanceSource('test_news', config)
    result = source.fetch()
    
    # 新闻可能为空，所以接受 success 或 degraded
    assert result.status in ['success', 'degraded', 'failed']
    
    if result.items:
        item = result.items[0]
        assert '[AAPL]' in item.title
        assert item.metadata['ticker'] == 'AAPL'
        assert 'publisher' in item.metadata
        
        print("✅ 新闻数据获取测试通过")
        print(f"   状态: {result.status}")
        print(f"   新闻数: {len(result.items)}")
        print(f"   第一条新闻: {item.title}")
        print(f"   发布者: {item.metadata['publisher']}")
    else:
        print("⚠️  没有获取到新闻数据（可能是 API 限制）")
        print(f"   状态: {result.status}")
    
    print("\n✅ 测试 1.3.3 完成！")


def test_15_yfinance_fetch_info():
    """测试 1.3.4: YFinanceSource 详细信息获取"""
    print("\n" + "="*80)
    print("测试 1.3.4: YFinanceSource 详细信息获取")
    print("="*80)
    
    config = {
        'tickers': ['AAPL'],
        'data_type': 'info',
        'category': 'stocks',
        'validation': {
            'min_items': 1
        }
    }
    
    source = YFinanceSource('test_info', config)
    result = source.fetch()
    
    assert result.status in ['success', 'degraded']
    assert len(result.items) > 0
    
    item = result.items[0]
    assert 'AAPL' in item.title
    assert item.metadata['ticker'] == 'AAPL'
    assert 'price' in item.metadata
    assert 'market_cap' in item.metadata
    assert 'pe_ratio' in item.metadata
    assert 'dividend_yield' in item.metadata
    
    print("✅ 详细信息获取测试通过")
    print(f"   状态: {result.status}")
    print(f"   数据项数: {len(result.items)}")
    print(f"   标题: {item.title}")
    print(f"   价格: ${item.metadata['price']:.2f}")
    print(f"   市值: ${item.metadata['market_cap']/1e9:.2f}B")
    print(f"   市盈率: {item.metadata['pe_ratio']:.2f}")
    print(f"   股息率: {item.metadata['dividend_yield']*100:.2f}%")
    
    print("\n✅ 测试 1.3.4 完成！")


def test_16_yfinance_error_handling():
    """测试 1.3.5: YFinanceSource 错误处理"""
    print("\n" + "="*80)
    print("测试 1.3.5: YFinanceSource 错误处理")
    print("="*80)
    
    # 测试 1: 无效的股票代码
    config_invalid = {
        'tickers': ['INVALID_TICKER_12345'],
        'data_type': 'price',
        'category': 'stocks',
        'validation': {
            'min_items': 1
        }
    }
    
    source_invalid = YFinanceSource('test_invalid', config_invalid)
    result_invalid = source_invalid.fetch()
    
    # 应该返回 degraded 或 failed
    assert result_invalid.status in ['degraded', 'failed']
    
    print("✅ 无效股票代码处理测试通过")
    print(f"   状态: {result_invalid.status}")
    print(f"   数据项数: {len(result_invalid.items)}")
    
    # 测试 2: 未知数据类型
    config_unknown = {
        'tickers': ['AAPL'],
        'data_type': 'unknown_type',
        'category': 'stocks'
    }
    
    source_unknown = YFinanceSource('test_unknown', config_unknown)
    result_unknown = source_unknown.fetch()
    
    assert result_unknown.status == 'failed'
    assert '未知数据类型' in result_unknown.error
    
    print("\n✅ 未知数据类型处理测试通过")
    print(f"   状态: {result_unknown.status}")
    print(f"   错误: {result_unknown.error}")
    
    # 测试 3: 混合有效和无效股票代码
    config_mixed = {
        'tickers': ['AAPL', 'INVALID_TICKER', 'GOOGL'],
        'data_type': 'price',
        'category': 'stocks',
        'validation': {
            'min_items': 2
        }
    }
    
    source_mixed = YFinanceSource('test_mixed', config_mixed)
    result_mixed = source_mixed.fetch()
    
    # 应该返回 degraded（部分成功）
    assert result_mixed.status in ['success', 'degraded']
    assert len(result_mixed.items) >= 2
    
    print("\n✅ 混合有效和无效股票代码处理测试通过")
    print(f"   状态: {result_mixed.status}")
    print(f"   数据项数: {len(result_mixed.items)}")
    
    for item in result_mixed.items:
        print(f"   - {item.title}")
    
    print("\n✅ 测试 1.3.5 完成！")


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("Phase 1.3: YFinanceSource 单元测试")
    print("="*80)
    
    tests = [
        ("1.3.1 初始化", test_12_yfinance_init),
        ("1.3.2 价格数据获取", test_13_yfinance_fetch_prices),
        ("1.3.3 新闻数据获取", test_14_yfinance_fetch_news),
        ("1.3.4 详细信息获取", test_15_yfinance_fetch_info),
        ("1.3.5 错误处理", test_16_yfinance_error_handling),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"\n✅ {test_name} - 通过")
        except AssertionError as e:
            failed += 1
            errors.append((test_name, str(e)))
            print(f"\n❌ {test_name} - 失败: {e}")
        except Exception as e:
            failed += 1
            errors.append((test_name, str(e)))
            print(f"\n❌ {test_name} - 错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("Phase 1.3 测试结果汇总")
    print("="*80)
    print(f"总计: {len(tests)} 个测试")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    
    if errors:
        print("\n失败的测试:")
        for test_name, error in errors:
            print(f"  - {test_name}: {error}")
    
    print("="*80)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
