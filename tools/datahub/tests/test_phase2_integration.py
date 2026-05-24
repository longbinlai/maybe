#!/usr/bin/env python3
"""
Phase 2: 集成测试

测试目标：
1. 多数据源协作
2. 完整 fetch-all 流程
3. 缓存集成
4. 报告生成
5. 错误恢复
"""

import sys
import os
from pathlib import Path
import yaml
import json
import time
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datahub.core.source_registry import SourceRegistry
from datahub.core.base_source import DataSourceResult, DataItem


def create_test_config(config_path: Path):
    """创建测试配置文件"""
    config = {
        'sources': {
            # RSS 数据源
            'test_rss_1': {
                'type': 'rss',
                'category': 'news',
                'url': 'https://feeds.bbci.co.uk/news/rss.xml',
                'max_items': 5,
                'enabled': True
            },
            'test_rss_2': {
                'type': 'rss',
                'category': 'tech',
                'url': 'https://hnrss.org/frontpage',
                'max_items': 5,
                'enabled': True
            },
            # YFinance 数据源
            'test_stocks': {
                'type': 'yfinance',
                'category': 'stocks',
                'tickers': ['AAPL', 'GOOGL'],
                'data_type': 'price',
                'enabled': True
            },
            'test_forex': {
                'type': 'yfinance',
                'category': 'forex',
                'tickers': ['USDCNY=X', 'EURUSD=X'],
                'data_type': 'price',
                'enabled': True
            },
            # 禁用的数据源
            'disabled_source': {
                'type': 'rss',
                'category': 'news',
                'url': 'https://example.com/rss',
                'enabled': False
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def test_01_multi_source_integration():
    """测试 2.1: 多数据源协作"""
    print("\n" + "="*80)
    print("测试 2.1: 多数据源协作")
    print("="*80)
    
    # 创建临时配置
    config_path = project_root / 'tests' / 'test_config.yaml'
    cache_dir = project_root / 'tests' / 'cache'
    
    try:
        create_test_config(config_path)
        print(f"✅ 创建测试配置: {config_path}")
        
        # 创建 SourceRegistry
        registry = SourceRegistry(
            config_path=str(config_path),
            cache_dir=str(cache_dir)
        )
        
        # 验证数据源加载
        sources = registry.list_sources()
        print(f"\n已加载 {len(sources)} 个数据源:")
        for source in sources:
            print(f"  - {source}")
        
        assert len(sources) == 4, f"应该加载 4 个数据源，实际加载了 {len(sources)} 个"
        assert 'test_rss_1' in sources
        assert 'test_rss_2' in sources
        assert 'test_stocks' in sources
        assert 'test_forex' in sources
        assert 'disabled_source' not in sources
        
        print("\n✅ 数据源加载验证通过")
        
        # 按类别获取数据
        print("\n按类别获取数据:")
        
        # 新闻类别
        news_results = registry.fetch_by_category('news')
        print(f"\n新闻类别 (news): {len(news_results)} 个数据源")
        for name, result in news_results.items():
            print(f"  - {name}: {result.status} ({len(result.items)} 条)")
        
        # 科技类别
        tech_results = registry.fetch_by_category('tech')
        print(f"\n科技类别 (tech): {len(tech_results)} 个数据源")
        for name, result in tech_results.items():
            print(f"  - {name}: {result.status} ({len(result.items)} 条)")
        
        # 股票类别
        stocks_results = registry.fetch_by_category('stocks')
        print(f"\n股票类别 (stocks): {len(stocks_results)} 个数据源")
        for name, result in stocks_results.items():
            print(f"  - {name}: {result.status} ({len(result.items)} 条)")
        
        print("\n✅ 多数据源协作测试通过")
        
    finally:
        # 清理配置文件
        if config_path.exists():
            config_path.unlink()


def test_02_fetch_all_flow():
    """测试 2.2: 完整 fetch-all 流程"""
    print("\n" + "="*80)
    print("测试 2.2: 完整 fetch-all 流程")
    print("="*80)
    
    # 创建临时配置
    config_path = project_root / 'tests' / 'test_config.yaml'
    cache_dir = project_root / 'tests' / 'cache'
    
    try:
        create_test_config(config_path)
        
        # 创建 SourceRegistry
        registry = SourceRegistry(
            config_path=str(config_path),
            cache_dir=str(cache_dir)
        )
        
        print(f"开始 fetch-all 流程...")
        print(f"数据源数量: {len(registry.list_sources())}")
        print(f"缓存目录: {cache_dir}")
        
        # 第一次 fetch-all（不使用缓存）
        print("\n第一次 fetch-all（不使用缓存）...")
        start_time = time.time()
        results_no_cache = registry.fetch_all(use_cache=False)
        duration_no_cache = time.time() - start_time
        
        print(f"耗时: {duration_no_cache:.2f} 秒")
        print(f"结果数量: {len(results_no_cache)}")
        
        # 统计结果
        success_count = sum(1 for r in results_no_cache.values() if r.status == 'success')
        degraded_count = sum(1 for r in results_no_cache.values() if r.status == 'degraded')
        failed_count = sum(1 for r in results_no_cache.values() if r.status == 'failed')
        
        print(f"\n结果统计:")
        print(f"  ✅ 成功: {success_count}")
        print(f"  ⚠️  降级: {degraded_count}")
        print(f"  ❌ 失败: {failed_count}")
        
        # 显示每个数据源的详情
        print(f"\n详细结果:")
        for name, result in results_no_cache.items():
            items_count = len(result.items)
            validation_score = result.validation.score if result.validation else 0
            print(f"  - {name}: {result.status}, {items_count} 条, 验证分数: {validation_score}")
        
        # 第二次 fetch-all（使用缓存）
        print("\n第二次 fetch-all（使用缓存）...")
        start_time = time.time()
        results_cached = registry.fetch_all(use_cache=True)
        duration_cached = time.time() - start_time
        
        print(f"耗时: {duration_cached:.2f} 秒")
        print(f"结果数量: {len(results_cached)}")
        
        # 验证缓存效果
        speedup = duration_no_cache / duration_cached if duration_cached > 0 else 1
        print(f"\n缓存加速比: {speedup:.2f}x")
        
        assert speedup > 2, f"缓存应该至少加速 2 倍，实际加速 {speedup:.2f} 倍"
        
        # 验证结果一致性
        assert len(results_no_cache) == len(results_cached), "缓存前后结果数量应该一致"
        
        print("\n✅ 完整 fetch-all 流程测试通过")
        
    finally:
        # 清理配置文件
        if config_path.exists():
            config_path.unlink()


def test_03_cache_integration():
    """测试 2.3: 缓存集成"""
    print("\n" + "="*80)
    print("测试 2.3: 缓存集成")
    print("="*80)
    
    # 创建临时配置
    config_path = project_root / 'tests' / 'test_config.yaml'
    cache_dir = project_root / 'tests' / 'cache_integration'
    
    try:
        create_test_config(config_path)
        
        # 清理缓存目录
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
        
        # 创建 SourceRegistry
        registry = SourceRegistry(
            config_path=str(config_path),
            cache_dir=str(cache_dir)
        )
        
        print(f"缓存目录: {cache_dir}")
        print(f"初始缓存文件数量: {len(list(cache_dir.glob('*.json')) if cache_dir.exists() else [])}")
        
        # 第一次 fetch（创建缓存）
        print("\n第一次 fetch（创建缓存）...")
        results_1 = registry.fetch_all(use_cache=True)
        
        cache_files = list(cache_dir.glob('*.json'))
        print(f"缓存文件数量: {len(cache_files)}")
        print(f"缓存文件列表:")
        for cache_file in cache_files:
            size = cache_file.stat().st_size
            print(f"  - {cache_file.name}: {size} bytes")
        
        # 验证缓存文件数量
        success_count = sum(1 for r in results_1.values() if r.status == 'success')
        assert len(cache_files) == success_count, f"缓存文件数量应该等于成功的数据源数量"
        
        # 验证缓存文件内容
        print("\n验证缓存文件内容...")
        for cache_file in cache_files[:2]:  # 只验证前 2 个
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            assert 'source_name' in cache_data
            assert 'items' in cache_data
            assert 'fetched_at' in cache_data
            
            print(f"  ✅ {cache_file.name}: 结构正确")
        
        # 第二次 fetch（使用缓存）
        print("\n第二次 fetch（使用缓存）...")
        results_2 = registry.fetch_all(use_cache=True)
        
        # 验证结果一致性
        for name in results_1.keys():
            if results_1[name].status == 'success':
                assert results_2[name].status == 'success'
                assert len(results_1[name].items) == len(results_2[name].items)
        
        print("\n✅ 缓存集成测试通过")
        
    finally:
        # 清理
        if config_path.exists():
            config_path.unlink()
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)


def test_04_report_generation():
    """测试 2.4: 报告生成"""
    print("\n" + "="*80)
    print("测试 2.4: 报告生成")
    print("="*80)
    
    # 创建临时配置
    config_path = project_root / 'tests' / 'test_config.yaml'
    cache_dir = project_root / 'tests' / 'cache_report'
    report_dir = project_root / 'tests' / 'reports'
    
    try:
        create_test_config(config_path)
        report_dir.mkdir(exist_ok=True)
        
        # 创建 SourceRegistry
        registry = SourceRegistry(
            config_path=str(config_path),
            cache_dir=str(cache_dir)
        )
        
        # 获取数据
        print("获取数据...")
        results = registry.fetch_all(use_cache=True)
        
        # 生成报告
        print("\n生成报告...")
        report = registry.generate_report(results)
        
        # 验证报告结构
        print("\n验证报告结构...")
        assert 'summary' in report
        assert 'by_category' in report
        assert 'total_items' in report
        assert 'sources' in report
        
        print(f"  ✅ 报告结构正确")
        
        # 验证汇总信息
        summary = report['summary']
        print(f"\n汇总信息:")
        print(f"  总数据源数: {summary['total_sources']}")
        print(f"  成功: {summary['success']}")
        print(f"  降级: {summary['degraded']}")
        print(f"  失败: {summary['failed']}")
        print(f"  成功率: {summary['success_rate']:.1f}%")
        
        assert summary['total_sources'] == len(results)
        
        # 验证分类统计
        print(f"\n分类统计:")
        for category, stats in report['by_category'].items():
            print(f"  - {category}: {stats['total']} 个数据源, {stats['success']} 个成功, {stats['items_count']} 条数据")
        
        # 保存报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = report_dir / f'integration_report_{timestamp}.json'
        
        print(f"\n保存报告到: {report_path}")
        registry.save_report(report, str(report_path))
        
        # 验证报告文件
        assert report_path.exists()
        report_size = report_path.stat().st_size
        print(f"  ✅ 报告文件已创建: {report_size} bytes")
        
        # 读取并验证报告内容
        with open(report_path, 'r') as f:
            saved_report = json.load(f)
        
        assert saved_report['summary']['total_sources'] == summary['total_sources']
        print(f"  ✅ 报告内容验证通过")
        
        print("\n✅ 报告生成测试通过")
        
    finally:
        # 清理
        if config_path.exists():
            config_path.unlink()
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)


def test_05_error_recovery():
    """测试 2.5: 错误恢复"""
    print("\n" + "="*80)
    print("测试 2.5: 错误恢复")
    print("="*80)
    
    # 创建包含无效数据源的配置
    config_path = project_root / 'tests' / 'test_config_error.yaml'
    cache_dir = project_root / 'tests' / 'cache_error'
    
    try:
        # 创建包含无效 URL 的配置
        config = {
            'sources': {
                'valid_rss': {
                    'type': 'rss',
                    'category': 'news',
                    'url': 'https://feeds.bbci.co.uk/news/rss.xml',
                    'max_items': 5,
                    'enabled': True
                },
                'invalid_rss': {
                    'type': 'rss',
                    'category': 'news',
                    'url': 'https://invalid-url-that-does-not-exist.com/rss',
                    'max_items': 5,
                    'enabled': True
                },
                'valid_stocks': {
                    'type': 'yfinance',
                    'category': 'stocks',
                    'tickers': ['AAPL'],
                    'data_type': 'price',
                    'enabled': True
                },
                'invalid_stocks': {
                    'type': 'yfinance',
                    'category': 'stocks',
                    'tickers': ['INVALID_TICKER_12345'],
                    'data_type': 'price',
                    'enabled': True
                }
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"创建包含无效数据源的配置: {config_path}")
        
        # 创建 SourceRegistry
        registry = SourceRegistry(
            config_path=str(config_path),
            cache_dir=str(cache_dir)
        )
        
        print(f"加载 {len(registry.list_sources())} 个数据源")
        
        # 执行 fetch-all
        print("\n执行 fetch-all（包含无效数据源）...")
        results = registry.fetch_all(use_cache=False)
        
        # 验证结果
        print(f"\n结果统计:")
        success_count = sum(1 for r in results.values() if r.status == 'success')
        degraded_count = sum(1 for r in results.values() if r.status == 'degraded')
        failed_count = sum(1 for r in results.values() if r.status == 'failed')
        
        print(f"  ✅ 成功: {success_count}")
        print(f"  ⚠️  降级: {degraded_count}")
        print(f"  ❌ 失败: {failed_count}")
        
        # 验证错误处理
        print(f"\n详细结果:")
        for name, result in results.items():
            status_icon = "✅" if result.status == 'success' else ("⚠️" if result.status == 'degraded' else "❌")
            print(f"  {status_icon} {name}: {result.status}")
            
            if result.status == 'failed' and result.error:
                print(f"     错误: {result.error[:100]}...")
        
        # 验证系统没有崩溃
        assert len(results) == 4, "应该返回所有数据源的结果"
        
        # 验证有效数据源成功
        assert results['valid_rss'].status in ['success', 'degraded']
        assert results['valid_stocks'].status in ['success', 'degraded']
        
        # 验证无效数据源失败或降级
        assert results['invalid_rss'].status in ['failed', 'degraded']
        assert results['invalid_stocks'].status in ['failed', 'degraded']
        
        # 生成报告（验证报告生成不会因为错误而失败）
        print("\n生成报告（验证错误恢复）...")
        report = registry.generate_report(results)
        
        assert report['summary']['total_sources'] == 4
        print(f"  ✅ 报告生成成功，包含 {report['summary']['total_sources']} 个数据源")
        
        print("\n✅ 错误恢复测试通过")
        
    finally:
        # 清理
        if config_path.exists():
            config_path.unlink()
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)


def main():
    """运行所有集成测试"""
    print("\n" + "="*80)
    print("Phase 2: 集成测试")
    print("="*80)
    
    tests = [
        ("2.1 多数据源协作", test_01_multi_source_integration),
        ("2.2 完整 fetch-all 流程", test_02_fetch_all_flow),
        ("2.3 缓存集成", test_03_cache_integration),
        ("2.4 报告生成", test_04_report_generation),
        ("2.5 错误恢复", test_05_error_recovery),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"\n✅ {test_name} - 通过\n")
        except AssertionError as e:
            failed += 1
            errors.append((test_name, str(e)))
            print(f"\n❌ {test_name} - 失败: {e}\n")
        except Exception as e:
            failed += 1
            errors.append((test_name, str(e)))
            print(f"\n❌ {test_name} - 错误: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("Phase 2 测试结果汇总")
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
