#!/usr/bin/env python3
"""
DataHub CLI - 数据源管理命令行工具

用法:
  datahub-cli fetch-all              # 获取所有数据源
  datahub-cli fetch <source_name>    # 获取单个数据源
  datahub-cli list                   # 列出所有数据源
  datahub-cli test                   # 测试所有数据源连接
  datahub-cli status                 # 查看缓存状态
"""

import sys
import os
import re
from pathlib import Path
from datetime import datetime, timedelta

from datahub import SourceRegistry, get_config_path, get_cache_dir
from datahub.core.history_store import HistoryStore


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1]

    # 初始化注册中心
    config_path = get_config_path("sources.yaml")
    cache_dir = get_cache_dir()
    report_dir = Path.home() / ".datahub" / "reports"
    
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

    elif command == 'history':
        cmd_history(sys.argv[2:])

    elif command == 'cleanup':
        cmd_cleanup(sys.argv[2:])

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


def cmd_history(args: list):
    """
    查询历史数据

    用法:
      python cli.py history --source federal_reserve --from 2026-03-01 --to 2026-03-31
      python cli.py history --keyword "美联储" --last 30d
      python cli.py history --category central_bank --limit 10
      python cli.py history --stats
      python cli.py history --logs
    """
    # 解析参数
    params = _parse_history_args(args)

    # 初始化 HistoryStore
    store = HistoryStore()
    if not store.available:
        print("错误: 无法连接到 PostgreSQL 历史存储")
        print("请确保:")
        print("  1. PostgreSQL 容器正在运行 (docker compose -f compose.local.yml up -d db)")
        print("  2. db 服务已映射端口 (5433:5432)")
        print("  3. psycopg2-binary 已安装 (~/pyenv/maybe/bin/pip install psycopg2-binary)")
        sys.exit(1)

    # --stats: 显示统计信息
    if params.get("stats"):
        _print_history_stats(store)
        store.close()
        return

    # --logs: 显示执行日志
    if params.get("logs"):
        source = params.get("source")
        logs = store.query_fetch_logs(source=source, limit=params.get("limit", 20))
        _print_fetch_logs(logs)
        store.close()
        return

    # 查询历史数据
    results = store.query(
        source=params.get("source"),
        category=params.get("category"),
        from_date=params.get("from_date"),
        to_date=params.get("to_date"),
        keyword=params.get("keyword"),
        limit=params.get("limit", 50),
    )

    if not results:
        print("未找到匹配的历史数据")
        store.close()
        return

    print("=" * 80)
    print(f"历史数据查询结果 ({len(results)} 条)")
    print("=" * 80)
    print()

    for i, item in enumerate(results, 1):
        published = item.get("published_at", "未知")
        if isinstance(published, str) and len(published) > 19:
            published = published[:19]
        print(f"{i:3d}. [{item.get('source', '?')}] {item.get('title', '无标题')}")
        print(f"     发布: {published}  |  类别: {item.get('category', '-')}")
        if item.get("url"):
            print(f"     链接: {item['url']}")
        if item.get("content"):
            # 显示前 120 字符的摘要
            content = item["content"][:120].replace("\n", " ")
            print(f"     摘要: {content}...")
        print()

    store.close()


def cmd_cleanup(args: list):
    """
    清理过期历史数据

    用法:
      python cli.py cleanup --dry-run     # 仅统计，不删除
      python cli.py cleanup               # 执行清理
      python cli.py cleanup --source federal_reserve --days 90
    """
    dry_run = "--dry-run" in args
    source = None
    days = None

    i = 0
    while i < len(args):
        if args[i] == "--source" and i + 1 < len(args):
            source = args[i + 1]
            i += 2
        elif args[i] == "--days" and i + 1 < len(args):
            days = int(args[i + 1])
            i += 2
        else:
            i += 1

    store = HistoryStore()
    if not store.available:
        print("错误: 无法连接到 PostgreSQL 历史存储")
        sys.exit(1)

    action = "预览" if dry_run else "执行"
    print("=" * 80)
    print(f"{action}清理过期历史数据...")
    print("=" * 80)
    print()

    result = store.cleanup(retention_days=days, source=source, dry_run=dry_run)

    if dry_run:
        print("【预览模式 — 未实际删除】")
        print()

    if "error" in result:
        print(f"错误: {result['error']}")
    else:
        if result.get("by_source"):
            print("按源清理:")
            for src, count in result["by_source"].items():
                if count > 0:
                    print(f"  {src:30s} — {count} 条")
            print()

        print(f"数据项: {result.get('deleted_items', 0)} 条{'将被删除' if dry_run else '已删除'}")
        print(f"执行日志: {result.get('deleted_logs', 0)} 条{'将被删除' if dry_run else '已删除'}")

    store.close()


def _parse_history_args(args: list) -> dict:
    """解析 history 子命令的参数"""
    params = {}
    i = 0

    while i < len(args):
        arg = args[i]

        if arg == "--stats":
            params["stats"] = True
            i += 1
        elif arg == "--logs":
            params["logs"] = True
            i += 1
        elif arg == "--source" and i + 1 < len(args):
            params["source"] = args[i + 1]
            i += 2
        elif arg == "--category" and i + 1 < len(args):
            params["category"] = args[i + 1]
            i += 2
        elif arg == "--keyword" and i + 1 < len(args):
            params["keyword"] = args[i + 1]
            i += 2
        elif arg == "--from" and i + 1 < len(args):
            params["from_date"] = args[i + 1]
            i += 2
        elif arg == "--to" and i + 1 < len(args):
            params["to_date"] = args[i + 1]
            i += 2
        elif arg == "--last" and i + 1 < len(args):
            # 支持 30d, 7d, 1w, 3m 等格式
            last_str = args[i + 1]
            from_date = _parse_last_duration(last_str)
            if from_date:
                params["from_date"] = from_date.isoformat()
                params["to_date"] = datetime.now().isoformat()
            i += 2
        elif arg == "--limit" and i + 1 < len(args):
            params["limit"] = int(args[i + 1])
            i += 2
        else:
            i += 1

    return params


def _parse_last_duration(s: str) -> datetime:
    """解析 --last 参数的时间范围 (如 30d, 7d, 1w, 3m)"""
    match = re.match(r'^(\d+)([dwmDWM])$', s)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()

    if unit == 'd':
        return datetime.now() - timedelta(days=amount)
    elif unit == 'w':
        return datetime.now() - timedelta(weeks=amount)
    elif unit == 'm':
        return datetime.now() - timedelta(days=amount * 30)
    return None


def _print_history_stats(store: HistoryStore):
    """打印历史存储统计信息"""
    stats = store.stats()

    if "error" in stats:
        print(f"错误: {stats['error']}")
        return

    print("=" * 80)
    print("历史数据存储统计")
    print("=" * 80)
    print()
    print(f"数据项总数: {stats.get('total_items', 0)}")
    print(f"执行日志总数: {stats.get('total_fetch_logs', 0)}")
    print(f"数据表大小: {stats.get('items_table_size', '未知')}")
    print(f"日志表大小: {stats.get('logs_table_size', '未知')}")
    print()

    if stats.get("by_source"):
        print(f"{'数据源':30s} {'条数':>8s} {'最早':>20s} {'最新':>20s}")
        print("-" * 80)
        for src in stats["by_source"]:
            earliest = (src.get("earliest") or "-")[:19]
            latest = (src.get("latest") or "-")[:19]
            print(f"{src['source']:30s} {src['count']:8d} {earliest:>20s} {latest:>20s}")
        print()


def _print_fetch_logs(logs: list):
    """打印执行日志"""
    if not logs:
        print("没有执行日志")
        return

    print("=" * 80)
    print(f"执行日志 (最近 {len(logs)} 条)")
    print("=" * 80)
    print()

    for log in logs:
        fetched_at = log.get("fetched_at", "?")
        if isinstance(fetched_at, str) and len(fetched_at) > 19:
            fetched_at = fetched_at[:19]
        status = log.get("status", "?")
        icon = {"success": "+", "degraded": "~", "failed": "!"}.get(status, "?")
        items = log.get("items_count", 0)
        duration = log.get("duration_ms")
        dur_str = f"{duration}ms" if duration else "-"

        print(f"  [{icon}] {fetched_at}  {log.get('source', '?'):30s}  {status:8s}  {items:3d} 项  {dur_str}")
        if log.get("error"):
            print(f"      错误: {log['error'][:80]}")
    print()


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
    print("数据获取:")
    print("  python cli.py fetch-all              # 获取所有数据源")
    print("  python cli.py fetch <source_name>    # 获取单个数据源")
    print("  python cli.py list                   # 列出所有数据源")
    print("  python cli.py test                   # 测试所有数据源连接")
    print("  python cli.py status                 # 查看缓存状态")
    print()
    print("历史数据 (PostgreSQL):")
    print("  python cli.py history --stats        # 存储统计")
    print("  python cli.py history --source <name>           # 按源查询")
    print("  python cli.py history --category <cat>          # 按类别查询")
    print("  python cli.py history --keyword <kw>            # 全文搜索")
    print("  python cli.py history --from 2026-03-01 --to 2026-03-31  # 时间范围")
    print("  python cli.py history --last 30d                # 最近 30 天")
    print("  python cli.py history --logs                    # 查看执行日志")
    print()
    print("数据清理:")
    print("  python cli.py cleanup --dry-run      # 预览清理")
    print("  python cli.py cleanup                # 执行清理")
    print("  python cli.py cleanup --source <name> --days 90  # 清理指定源")
    print()


if __name__ == '__main__':
    main()
