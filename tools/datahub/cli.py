#!/usr/bin/env python3
"""
DataHub CLI - 数据源管理命令行工具

用法:
  python cli.py fetch-all              # 获取所有数据源
  python cli.py fetch <source_name>    # 获取单个数据源
  python cli.py list                   # 列出所有数据源
  python cli.py test                   # 测试所有数据源连接
  python cli.py status                 # 查看缓存状态
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datahub import SourceRegistry


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1]
    
    # 初始化注册中心
    project_root = Path(__file__).parent
    config_path = project_root / 'config' / 'sources.yaml'
    cache_dir = project_root / 'cache'
    report_dir = project_root / 'reports'
    
    registry = SourceRegistry(
        config_path=str(config_path),
        cache_dir=str(cache_dir)
    )
    
    if command == 'fetch-all':
        cmd_fetch_all(registry, report_dir)
    
    elif command == 'fetch':
        if len(sys.argv) < 3:
            print("错误: 请指定数据源名称")
            print("用法: python cli.py fetch <source_name>")
            sys.exit(1)
        source_name = sys.argv[2]
        cmd_fetch_single(registry, source_name)
    
    elif command == 'list':
        cmd_list(registry)
    
    elif command == 'test':
        cmd_test(registry)
    
    elif command == 'status':
        cmd_status(registry)
    
    else:
        print(f"未知命令: {command}")
        print_help()
        sys.exit(1)


def cmd_fetch_all(registry: SourceRegistry, report_dir: Path):
    """获取所有数据源"""
    print("=" * 80)
    print("开始获取所有数据源...")
    print("=" * 80)
    print()
    
    results = registry.fetch_all()
    
    # 生成报告
    print()
    print("=" * 80)
    print("生成报告...")
    print("=" * 80)
    
    report = registry.generate_report(results)
    
    # 保存报告
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = report_dir / f"report_{timestamp}.json"
    
    registry.save_report(report, str(report_path))
    
    # 打印摘要
    print()
    print_summary(report)


def cmd_fetch_single(registry: SourceRegistry, source_name: str):
    """获取单个数据源"""
    source = registry.get_source(source_name)
    
    if not source:
        print(f"错误: 未找到数据源 '{source_name}'")
        print(f"可用数据源: {', '.join(registry.list_sources())}")
        sys.exit(1)
    
    print(f"获取数据源: {source_name}")
    print("-" * 80)
    
    result = source.fetch()
    
    print(f"状态: {result.status}")
    print(f"数据项: {len(result.items)}")
    
    if result.error:
        print(f"错误: {result.error}")
    
    if result.validation:
        print(f"验证分数: {result.validation.score}/100")
        if result.validation.issues:
            print("问题:")
            for issue in result.validation.issues:
                print(f"  - {issue}")
    
    print()
    print("数据项预览:")
    for i, item in enumerate(result.items[:5], 1):
        print(f"{i}. {item.title}")
        print(f"   发布时间: {item.published.strftime('%Y-%m-%d %H:%M')}")
        print()


def cmd_list(registry: SourceRegistry):
    """列出所有数据源"""
    print("=" * 80)
    print("已注册的数据源")
    print("=" * 80)
    print()
    
    sources = registry.list_sources()
    
    if not sources:
        print("没有注册的数据源")
        return
    
    # 按类别分组
    by_category = {}
    for source_name in sources:
        source = registry.get_source(source_name)
        category = source.category
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(source)
    
    # 打印
    for category, source_list in sorted(by_category.items()):
        print(f"【{category.upper()}】")
        for source in source_list:
            priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(source.priority, '⚪')
            status = '✅' if source.enabled else '❌'
            print(f"  {status} {priority_icon} {source.name:30s} [{source.__class__.__name__}]")
        print()
    
    print(f"总计: {len(sources)} 个数据源")


def cmd_test(registry: SourceRegistry):
    """测试所有数据源连接"""
    print("=" * 80)
    print("测试数据源连接")
    print("=" * 80)
    print()
    
    sources = registry.list_sources()
    success_count = 0
    fail_count = 0
    
    for source_name in sources:
        source = registry.get_source(source_name)
        
        try:
            result = source.fetch()
            if result.status == 'success':
                print(f"✅ {source_name:30s} - 成功 ({len(result.items)} 项)")
                success_count += 1
            elif result.status == 'degraded':
                print(f"⚠️  {source_name:30s} - 降级 ({len(result.items)} 项)")
                success_count += 1
            else:
                print(f"❌ {source_name:30s} - 失败: {result.error}")
                fail_count += 1
        except Exception as e:
            print(f"❌ {source_name:30s} - 异常: {str(e)}")
            fail_count += 1
    
    print()
    print(f"成功: {success_count}/{len(sources)}")
    print(f"失败: {fail_count}/{len(sources)}")


def cmd_status(registry: SourceRegistry):
    """查看缓存状态"""
    print("=" * 80)
    print("缓存状态")
    print("=" * 80)
    print()
    
    if not registry.cache_dir or not registry.cache_dir.exists():
        print("没有缓存数据")
        return
    
    cache_files = list(registry.cache_dir.glob('*.json'))
    
    if not cache_files:
        print("没有缓存数据")
        return
    
    print(f"缓存目录: {registry.cache_dir}")
    print(f"缓存文件: {len(cache_files)} 个")
    print()
    
    for cache_file in sorted(cache_files):
        import json
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            source_name = data.get('source_name', cache_file.stem)
            status = data.get('status', 'unknown')
            items_count = len(data.get('items', []))
            fetched_at = data.get('fetched_at', 'unknown')
            
            # 计算缓存年龄
            try:
                fetched_time = datetime.fromisoformat(fetched_at)
                age = datetime.now() - fetched_time
                age_str = f"{age.seconds // 3600}小时{age.seconds % 3600 // 60}分钟前"
            except:
                age_str = '未知'
            
            status_icon = {'success': '✅', 'degraded': '⚠️', 'failed': '❌'}.get(status, '❓')
            print(f"{status_icon} {source_name:30s} - {items_count:3d} 项 ({age_str})")
        
        except Exception as e:
            print(f"❓ {cache_file.stem:30s} - 读取失败: {str(e)}")


def print_summary(report: dict):
    """打印报告摘要"""
    summary = report['summary']
    
    print("=" * 80)
    print("数据获取摘要")
    print("=" * 80)
    print()
    print(f"总计数据源: {summary['total_sources']}")
    print(f"成功: {summary['success']} ({summary['success_rate']:.1f}%)")
    print(f"降级: {summary['degraded']}")
    print(f"失败: {summary['failed']}")
    print(f"总数据项: {report['total_items']}")
    print()
    
    # 按类别统计
    print("按类别统计:")
    for category, stats in report['by_category'].items():
        success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {category:20s} - {stats['success']}/{stats['total']} 成功, {stats['items_count']} 项数据")
    print()


def print_help():
    """打印帮助信息"""
    print("=" * 80)
    print("DataHub CLI - 数据源管理工具")
    print("=" * 80)
    print()
    print("用法:")
    print("  python cli.py fetch-all              # 获取所有数据源")
    print("  python cli.py fetch <source_name>    # 获取单个数据源")
    print("  python cli.py list                   # 列出所有数据源")
    print("  python cli.py test                   # 测试所有数据源连接")
    print("  python cli.py status                 # 查看缓存状态")
    print()
    print("示例:")
    print("  python cli.py list")
    print("  python cli.py fetch-all")
    print("  python cli.py fetch federal_reserve")
    print("  python cli.py test")
    print()


if __name__ == '__main__':
    main()
