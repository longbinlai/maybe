#!/usr/bin/env python3
"""
Phase 1.4: SourceRegistry 单元测试
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datahub.core.source_registry import SourceRegistry
from datahub.core.base_source import BaseDataSource, DataSourceResult, DataItem
from datetime import datetime, timedelta
import tempfile
import json
from pathlib import Path


class MockDataSource(BaseDataSource):
    """模拟数据源用于测试"""
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.fetch_count = 0
    
    def fetch(self) -> DataSourceResult:
        self.fetch_count += 1
        
        # 创建模拟数据
        items = [
            DataItem(
                id=f"{self.name}_item_{i}",
                source=self.name,
                category=self.category,
                title=f"Test Item {i}",
                content=f"Test content {i}",
                url=f"https://example.com/{i}",
                published=datetime.now() - timedelta(days=i),
                metadata={'test': True}
            )
            for i in range(5)
        ]
        
        return DataSourceResult(
            source_name=self.name,
            source_type='mock',
            category=self.category,
            status='success',
            items=items,
            fetched_at=datetime.now()
        )


def test_17_registry_init():
    """测试 1.4.1: SourceRegistry 初始化"""
    print("\n" + "="*80)
    print("测试 1.4.1: SourceRegistry 初始化")
    print("="*80)
    
    # 测试 1: 基本初始化
    registry = SourceRegistry()
    
    assert registry.sources == {}
    assert registry.config_path is None
    assert registry.cache_dir is None
    
    print("✅ 基本初始化测试通过")
    print(f"   sources: {registry.sources}")
    print(f"   config_path: {registry.config_path}")
    print(f"   cache_dir: {registry.cache_dir}")
    
    # 测试 2: 带配置路径初始化
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("sources: {}")
        config_path = f.name
    
    try:
        registry_with_config = SourceRegistry(config_path=config_path)
        assert registry_with_config.config_path == config_path
        assert registry_with_config.sources == {}
        
        print("\n✅ 带配置路径初始化测试通过")
        print(f"   config_path: {registry_with_config.config_path}")
        print(f"   sources: {registry_with_config.sources}")
    finally:
        os.unlink(config_path)
    
    # 测试 3: 带缓存目录初始化
    with tempfile.TemporaryDirectory() as temp_dir:
        registry_with_cache = SourceRegistry(cache_dir=temp_dir)
        assert registry_with_cache.cache_dir == Path(temp_dir)
        
        print("\n✅ 带缓存目录初始化测试通过")
        print(f"   cache_dir: {registry_with_cache.cache_dir}")
    
    print("\n✅ 测试 1.4.1 完成！")


def test_18_registry_register():
    """测试 1.4.2: 数据源注册和注销"""
    print("\n" + "="*80)
    print("测试 1.4.2: 数据源注册和注销")
    print("="*80)
    
    registry = SourceRegistry()
    
    # 测试 1: 注册数据源
    source1 = MockDataSource('source1', {'category': 'test', 'priority': 'high'})
    source2 = MockDataSource('source2', {'category': 'test', 'priority': 'medium'})
    
    registry.register(source1)
    registry.register(source2)
    
    assert 'source1' in registry.sources
    assert 'source2' in registry.sources
    assert len(registry.sources) == 2
    
    print("✅ 注册数据源测试通过")
    print(f"   已注册: {list(registry.sources.keys())}")
    
    # 测试 2: 获取数据源
    retrieved_source = registry.get_source('source1')
    assert retrieved_source is source1
    
    print("\n✅ 获取数据源测试通过")
    print(f"   获取 source1: {retrieved_source.name}")
    
    # 测试 3: 获取不存在的数据源
    non_existent = registry.get_source('non_existent')
    assert non_existent is None
    
    print("\n✅ 获取不存在的数据源测试通过")
    print(f"   获取 non_existent: {non_existent}")
    
    # 测试 4: 列出所有数据源
    source_list = registry.list_sources()
    assert set(source_list) == {'source1', 'source2'}
    
    print("\n✅ 列出所有数据源测试通过")
    print(f"   数据源列表: {source_list}")
    
    # 测试 5: 注销数据源
    registry.unregister('source1')
    assert 'source1' not in registry.sources
    assert 'source2' in registry.sources
    assert len(registry.sources) == 1
    
    print("\n✅ 注销数据源测试通过")
    print(f"   剩余数据源: {list(registry.sources.keys())}")
    
    # 测试 6: 注销不存在的数据源（应该不报错）
    registry.unregister('non_existent')
    
    print("\n✅ 注销不存在的数据源测试通过（无错误）")
    
    print("\n✅ 测试 1.4.2 完成！")


def test_19_registry_load_config():
    """测试 1.4.3: 从配置文件加载数据源"""
    print("\n" + "="*80)
    print("测试 1.4.3: 从配置文件加载数据源")
    print("="*80)
    
    # 测试 1: 加载有效的配置文件
    config_content = """
sources:
  test_rss:
    type: rss
    category: news
    priority: high
    enabled: true
    url: https://example.com/rss
    max_items: 10
  
  test_yfinance:
    type: yfinance
    category: stocks
    priority: medium
    enabled: true
    tickers:
      - AAPL
      - GOOGL
    data_type: price
  
  disabled_source:
    type: rss
    category: news
    enabled: false
    url: https://example.com/disabled
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        config_path = f.name
    
    try:
        registry = SourceRegistry(config_path=config_path)
        
        # 应该加载 2 个启用的数据源
        assert len(registry.sources) == 2
        assert 'test_rss' in registry.sources
        assert 'test_yfinance' in registry.sources
        assert 'disabled_source' not in registry.sources
        
        # 验证数据源配置
        rss_source = registry.get_source('test_rss')
        assert rss_source.category == 'news'
        assert rss_source.priority == 'high'
        
        yfinance_source = registry.get_source('test_yfinance')
        assert yfinance_source.category == 'stocks'
        assert yfinance_source.priority == 'medium'
        
        print("✅ 加载有效配置文件测试通过")
        print(f"   加载的数据源: {list(registry.sources.keys())}")
        print(f"   test_rss 类别: {rss_source.category}")
        print(f"   test_yfinance 类别: {yfinance_source.category}")
        
    finally:
        os.unlink(config_path)
    
    # 测试 2: 加载未知类型的数据源
    config_unknown = """
sources:
  unknown_source:
    type: unknown_type
    category: test
    enabled: true
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_unknown)
        config_path = f.name
    
    try:
        registry_unknown = SourceRegistry(config_path=config_path)
        
        # 未知类型应该被跳过
        assert len(registry_unknown.sources) == 0
        
        print("\n✅ 加载未知类型数据源测试通过（已跳过）")
        print(f"   加载的数据源: {list(registry_unknown.sources.keys())}")
        
    finally:
        os.unlink(config_path)
    
    # 测试 3: 加载空配置文件
    config_empty = """
sources: {}
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_empty)
        config_path = f.name
    
    try:
        registry_empty = SourceRegistry(config_path=config_path)
        assert len(registry_empty.sources) == 0
        
        print("\n✅ 加载空配置文件测试通过")
        print(f"   加载的数据源: {list(registry_empty.sources.keys())}")
        
    finally:
        os.unlink(config_path)
    
    print("\n✅ 测试 1.4.3 完成！")


def test_20_registry_fetch_all():
    """测试 1.4.4: 获取所有数据源的数据"""
    print("\n" + "="*80)
    print("测试 1.4.4: 获取所有数据源的数据")
    print("="*80)
    
    registry = SourceRegistry()
    
    # 注册多个数据源
    source1 = MockDataSource('source1', {'category': 'test1'})
    source2 = MockDataSource('source2', {'category': 'test2'})
    source3 = MockDataSource('source3', {'category': 'test1'})
    
    registry.register(source1)
    registry.register(source2)
    registry.register(source3)
    
    # 测试 1: 获取所有数据
    results = registry.fetch_all(use_cache=False)
    
    assert len(results) == 3
    assert all(result.status == 'success' for result in results.values())
    assert all(len(result.items) == 5 for result in results.values())
    
    # 验证每个数据源都被调用了一次
    assert source1.fetch_count == 1
    assert source2.fetch_count == 1
    assert source3.fetch_count == 1
    
    print("✅ 获取所有数据测试通过")
    print(f"   获取的数据源数: {len(results)}")
    print(f"   每个数据源的数据项数: {[len(r.items) for r in results.values()]}")
    
    # 测试 2: 按类别获取数据
    results_by_category = registry.fetch_by_category('test1')
    
    assert len(results_by_category) == 2
    assert 'source1' in results_by_category
    assert 'source3' in results_by_category
    assert 'source2' not in results_by_category
    
    print("\n✅ 按类别获取数据测试通过")
    print(f"   test1 类别的数据源: {list(results_by_category.keys())}")
    
    print("\n✅ 测试 1.4.4 完成！")


def test_21_registry_cache():
    """测试 1.4.5: 缓存机制"""
    print("\n" + "="*80)
    print("测试 1.4.5: 缓存机制")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        registry = SourceRegistry(cache_dir=temp_dir)
        
        # 注册数据源
        source = MockDataSource('test_source', {'category': 'test'})
        registry.register(source)
        
        # 测试 1: 第一次获取（应该调用 fetch）
        results1 = registry.fetch_all(use_cache=True, cache_ttl=3600)
        
        assert source.fetch_count == 1
        assert 'test_source' in results1
        
        print("✅ 第一次获取测试通过（调用 fetch）")
        print(f"   fetch 调用次数: {source.fetch_count}")
        
        # 测试 2: 第二次获取（应该使用缓存）
        results2 = registry.fetch_all(use_cache=True, cache_ttl=3600)
        
        assert source.fetch_count == 1  # 没有再次调用
        assert 'test_source' in results2
        
        print("\n✅ 第二次获取测试通过（使用缓存）")
        print(f"   fetch 调用次数: {source.fetch_count}（未增加）")
        
        # 测试 3: 禁用缓存
        results3 = registry.fetch_all(use_cache=False, cache_ttl=3600)
        
        assert source.fetch_count == 2  # 再次调用
        
        print("\n✅ 禁用缓存测试通过")
        print(f"   fetch 调用次数: {source.fetch_count}（增加了）")
        
        # 测试 4: 缓存过期
        # 修改缓存文件的时间戳
        cache_file = Path(temp_dir) / "test_source.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # 设置为 2 小时前
            old_time = datetime.now() - timedelta(hours=2)
            cache_data['fetched_at'] = old_time.isoformat()
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        
        results4 = registry.fetch_all(use_cache=True, cache_ttl=3600)
        
        assert source.fetch_count == 3  # 缓存过期，再次调用
        
        print("\n✅ 缓存过期测试通过")
        print(f"   fetch 调用次数: {source.fetch_count}（缓存过期后再次调用）")
    
    print("\n✅ 测试 1.4.5 完成！")


def test_22_registry_report():
    """测试 1.4.6: 生成和保存报告"""
    print("\n" + "="*80)
    print("测试 1.4.6: 生成和保存报告")
    print("="*80)
    
    registry = SourceRegistry()
    
    # 注册多个数据源
    source1 = MockDataSource('source1', {'category': 'test1'})
    source2 = MockDataSource('source2', {'category': 'test2'})
    source3 = MockDataSource('source3', {'category': 'test1'})
    
    registry.register(source1)
    registry.register(source2)
    registry.register(source3)
    
    # 获取数据
    results = registry.fetch_all(use_cache=False)
    
    # 测试 1: 生成报告
    report = registry.generate_report(results)
    
    assert 'timestamp' in report
    assert 'summary' in report
    assert 'by_category' in report
    assert 'total_items' in report
    assert 'sources' in report
    
    # 验证汇总信息
    summary = report['summary']
    assert summary['total_sources'] == 3
    assert summary['success'] == 3
    assert summary['degraded'] == 0
    assert summary['failed'] == 0
    assert summary['success_rate'] == 100.0
    
    # 验证按类别统计
    by_category = report['by_category']
    assert 'test1' in by_category
    assert 'test2' in by_category
    assert by_category['test1']['total'] == 2
    assert by_category['test2']['total'] == 1
    
    # 验证总数据项数
    assert report['total_items'] == 15  # 3 个数据源 * 5 个数据项
    
    print("✅ 生成报告测试通过")
    print(f"   时间戳: {report['timestamp']}")
    print(f"   总数据源数: {summary['total_sources']}")
    print(f"   成功数: {summary['success']}")
    print(f"   成功率: {summary['success_rate']}%")
    print(f"   总数据项数: {report['total_items']}")
    print(f"   类别统计: {by_category}")
    
    # 测试 2: 保存报告
    with tempfile.TemporaryDirectory() as temp_dir:
        report_path = os.path.join(temp_dir, 'report.json')
        registry.save_report(report, report_path)
        
        # 验证文件存在
        assert os.path.exists(report_path)
        
        # 验证文件内容
        with open(report_path, 'r') as f:
            saved_report = json.load(f)
        
        assert saved_report['summary']['total_sources'] == 3
        assert saved_report['total_items'] == 15
        
        print("\n✅ 保存报告测试通过")
        print(f"   报告路径: {report_path}")
        print(f"   文件大小: {os.path.getsize(report_path)} bytes")
    
    print("\n✅ 测试 1.4.6 完成！")


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("Phase 1.4: SourceRegistry 单元测试")
    print("="*80)
    
    tests = [
        ("1.4.1 初始化", test_17_registry_init),
        ("1.4.2 注册和注销", test_18_registry_register),
        ("1.4.3 加载配置", test_19_registry_load_config),
        ("1.4.4 获取数据", test_20_registry_fetch_all),
        ("1.4.5 缓存机制", test_21_registry_cache),
        ("1.4.6 生成报告", test_22_registry_report),
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
    print("Phase 1.4 测试结果汇总")
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
