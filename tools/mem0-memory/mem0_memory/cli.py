"""mem0-memory CLI: structured memory management for Maybe Finance.

使用 Click 框架，提供 add/search/list/delete/migrate/stats 命令。
"""

import json
import sys

import click

from .client import Mem0Client, validate_category
from .migrator import MarkdownMigrator


# ── 共享选项 ─────────────────────────────────────────────────────────────

_config_opt = click.option(
    "--config", "config_path", default=None,
    help="Path to mem0.yaml config file (default: bundled config/mem0.yaml)",
)


def _get_client(config_path: str | None) -> Mem0Client:
    """Construct a Mem0Client, handling errors gracefully."""
    try:
        return Mem0Client(config_path=config_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Install with: pip install mem0ai", err=True)
        raise SystemExit(1)
    except RuntimeError as e:
        click.echo(f"Error initializing Mem0: {e}", err=True)
        raise SystemExit(1)


# ── CLI group ────────────────────────────────────────────────────────────

@click.group()
@click.version_option(version="0.1.0", prog_name="mem0-memory")
def cli():
    """Mem0 Memory — structured memory management for Maybe Finance."""
    pass


# ── add ──────────────────────────────────────────────────────────────────

@cli.command("add")
@_config_opt
@click.option("--category", "-c", required=True, help="Memory category (e.g. investment_decision)")
@click.option("--content", required=True, help="Memory content (natural language)")
@click.option("--metadata", "-m", multiple=True, help="Extra metadata as key=value pairs")
def add(config_path, category, content, metadata):
    """Add a new memory.

    Example:
        memory add -c investment_decision --content "买入腾讯 100 股，理由：AI 业务增长"
        memory add -c market_view --content "长期看好 A 股，港股处于历史低位" -m confidence=7
    """
    # 先校验分类，避免在连接 Qdrant/Ollama 之前就因脏分类浪费连接
    try:
        category = validate_category(category)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    client = _get_client(config_path)

    # 解析 key=value 元数据
    meta = {}
    for item in metadata:
        if "=" not in item:
            click.echo(f"Warning: ignoring invalid metadata '{item}' (expected key=value)", err=True)
            continue
        key, _, value = item.partition("=")
        meta[key.strip()] = value.strip()

    result = client.add(content=content, category=category, metadata=meta)

    # 提取结果
    memories = result.get("results", result.get("memories", []))
    if isinstance(memories, list) and memories:
        mem_id = memories[0].get("id", "unknown")
        click.echo(f"Memory added: {mem_id}")
    elif isinstance(result, dict) and "id" in result:
        click.echo(f"Memory added: {result['id']}")
    else:
        click.echo(f"Memory added. Response: {json.dumps(result, indent=2, default=str)}")

    click.echo(f"  Category: {category}")
    click.echo(f"  Content:  {content[:80]}{'...' if len(content) > 80 else ''}")


# ── search ───────────────────────────────────────────────────────────────

@cli.command("search")
@_config_opt
@click.option("--query", "-q", required=True, help="Search query (natural language)")
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--limit", "-n", default=10, type=int, help="Maximum results (default: 10)")
def search(config_path, query, category, limit):
    """Search memories semantically.

    Example:
        memory search -q "腾讯买入"
        memory search -q "美联储" -c market_event -n 5
    """
    client = _get_client(config_path)
    results = client.search(query=query, category=category, limit=limit)

    if not results:
        click.echo("No memories found.")
        return

    click.echo(f"Found {len(results)} result(s):\n")

    for i, mem in enumerate(results, 1):
        score = mem.get("score", "N/A")
        content = mem.get("memory", mem.get("content", ""))
        meta = mem.get("metadata", {})
        mem_id = mem.get("id", "unknown")

        # 显示结果
        score_str = f"{score:.4f}" if isinstance(score, float) else str(score)
        click.echo(f"  [{i}] {score_str}  {mem_id}")
        click.echo(f"      Category: {meta.get('category', 'N/A')}")
        click.echo(f"      Date:     {meta.get('date', 'N/A')}")
        click.echo(f"      Content:  {content[:120]}{'...' if len(content) > 120 else ''}")

        # 显示额外元数据（排除标准字段）
        extra = {k: v for k, v in meta.items() if k not in ("category", "date", "created_at")}
        if extra:
            click.echo(f"      Metadata: {json.dumps(extra, ensure_ascii=False)}")
        click.echo()


# ── list ─────────────────────────────────────────────────────────────────

@cli.command("list")
@_config_opt
@click.option("--category", "-c", default=None, help="Filter by category")
def list_memories(config_path, category):
    """List all memories, optionally filtered by category.

    Example:
        memory list
        memory list -c investment_decision
    """
    client = _get_client(config_path)
    memories = client.get_all(category=category)

    if not memories:
        click.echo("No memories found.")
        return

    click.echo(f"Total: {len(memories)} memories\n")

    # 表格头
    header = f"  {'ID':36s}  {'Category':20s}  {'Date':12s}  {'Content':60s}"
    click.echo(header)
    click.echo("  " + "-" * (len(header) - 2))

    for mem in memories:
        mem_id = mem.get("id", "unknown")
        meta = mem.get("metadata", {})
        content = mem.get("memory", mem.get("content", ""))
        cat = meta.get("category", "N/A")
        date = meta.get("date", "N/A")
        preview = content[:80].replace("\n", " ")

        click.echo(f"  {mem_id:36s}  {cat:20s}  {date:12s}  {preview}")


# ── delete ───────────────────────────────────────────────────────────────

@cli.command("delete")
@_config_opt
@click.argument("memory_id")
@click.confirmation_option(prompt="Are you sure you want to delete this memory?")
def delete(config_path, memory_id):
    """Delete a memory by ID.

    Example:
        memory delete abc123-def456
    """
    client = _get_client(config_path)

    if client.delete(memory_id):
        click.echo(f"Deleted: {memory_id}")
    else:
        click.echo(f"Failed to delete: {memory_id}", err=True)
        raise SystemExit(1)


# ── migrate ──────────────────────────────────────────────────────────────

@cli.command("migrate")
@_config_opt
@click.option("--from", "source_dir", required=True, help="Path to memory/ directory with Markdown files")
@click.option("--dry-run", is_flag=True, help="Show what would be migrated without actually doing it")
def migrate(config_path, source_dir, dry_run):
    """Migrate Markdown memory files to Mem0.

    Parses memory/YYYY-MM-DD.md files and extracts structured entries
    (decisions, market events, reviews) into Mem0 with appropriate metadata.

    Example:
        memory migrate --from ./memory
        memory migrate --from ./memory --dry-run
    """
    try:
        migrator = MarkdownMigrator(source_dir)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if dry_run:
        click.echo("=== DRY RUN — no changes will be made ===\n")

    # 如果 dry-run 不需要真正的 client
    client = None
    if not dry_run:
        client = _get_client(config_path)

    stats = migrator.migrate(client, dry_run=dry_run)

    # 显示结果
    click.echo(f"Files scanned:  {stats['total_files']}")
    click.echo(f"Entries found:   {stats['total_entries']}")

    if not dry_run:
        click.echo(f"Migrated:        {stats['migrated']}")
        click.echo(f"Skipped:         {stats['skipped']}")

    if stats.get("errors"):
        click.echo(f"\nErrors ({len(stats['errors'])}):")
        for err in stats["errors"]:
            click.echo(f"  {err['file']}: {err['title']} — {err['error']}")

    # Dry-run 模式下显示将要迁移的条目
    if dry_run and stats["entries"]:
        click.echo(f"\nEntries to migrate:")
        for entry in stats["entries"]:
            click.echo(f"  [{entry.category:20s}] {entry.date}  {entry.title}")
            click.echo(f"    Source: {entry.source_file}")
            click.echo(f"    Content: {entry.content[:100]}{'...' if len(entry.content) > 100 else ''}")
            click.echo()


# ── stats ────────────────────────────────────────────────────────────────

@cli.command("stats")
@_config_opt
def stats(config_path):
    """Show memory statistics — total count, by category, date range.

    Example:
        memory stats
    """
    client = _get_client(config_path)
    memories = client.get_all()

    if not memories:
        click.echo("No memories in the store.")
        return

    total = len(memories)

    # 按分类统计
    by_category: dict[str, int] = {}
    dates: list[str] = []

    for mem in memories:
        meta = mem.get("metadata", {})
        cat = meta.get("category", "uncategorized")
        by_category[cat] = by_category.get(cat, 0) + 1

        date = meta.get("date", "")
        if date:
            dates.append(date)

    click.echo(f"Total memories: {total}\n")

    # 分类统计
    click.echo("By category:")
    for cat in sorted(by_category.keys()):
        count = by_category[cat]
        bar = "#" * min(count, 40)
        click.echo(f"  {cat:25s}  {count:>4d}  {bar}")

    # 日期范围
    if dates:
        dates.sort()
        click.echo(f"\nDate range: {dates[0]} to {dates[-1]}")

    # 配置的分类
    click.echo(f"\nConfigured categories: {len(client.categories)}")
    for cat in client.categories:
        marker = "+" if cat in by_category else "-"
        click.echo(f"  [{marker}] {cat}")


# ── entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
