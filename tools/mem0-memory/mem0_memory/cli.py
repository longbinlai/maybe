"""mem0-memory CLI: structured memory management for Maybe Finance.

使用 Click 框架，提供 add/search/list/delete/migrate/stats 命令。
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import date, timedelta

import click

from .client import Mem0Client, validate_category
from .migrator import MarkdownMigrator


# ── maybe CLI 调用辅助 ────────────────────────────────────────────────────

_MAYBE_TIMEOUT = 30  # subprocess 超时（秒）


def _find_maybe() -> str | None:
    """定位 maybe 二进制：先 PATH，回退 ~/pyenv/maybe/bin/maybe。"""
    found = shutil.which("maybe")
    if found:
        return found
    fallback = os.path.expanduser("~/pyenv/maybe/bin/maybe")
    if os.path.exists(fallback):
        return fallback
    return None


def _run_maybe_json(maybe_bin: str, args: list[str]) -> dict | None:
    """运行 `maybe <args> --json` 并解析 JSON，失败时优雅返回 None。"""
    try:
        proc = subprocess.run(
            [maybe_bin, *args, "--json"],
            capture_output=True,
            text=True,
            timeout=_MAYBE_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        click.echo(f"Warning: failed to run `maybe {' '.join(args)}`: {e}", err=True)
        return None

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        click.echo(
            f"Warning: `maybe {' '.join(args)}` exited {proc.returncode}: {err}",
            err=True,
        )
        return None

    try:
        return json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError) as e:
        click.echo(
            f"Warning: could not parse JSON from `maybe {' '.join(args)}`: {e}",
            err=True,
        )
        return None


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


# ── review ───────────────────────────────────────────────────────────────

def _period_bounds(monthly: bool, today: date) -> tuple[date, date, str]:
    """计算复盘周期的起止日期与 period 标识。

    Returns:
        (start_date, end_date, period_id)
        - weekly: 本周一 ~ today，period 形如 2026-W26
        - monthly: 本月初 ~ today，period 形如 2026-06
    """
    if monthly:
        start = today.replace(day=1)
        period = today.strftime("%Y-%m")
    else:
        # weekday(): Monday=0 ... Sunday=6
        start = today - timedelta(days=today.weekday())
        iso_year, iso_week, _ = today.isocalendar()
        period = f"{iso_year}-W{iso_week:02d}"
    return start, today, period


def _build_review_content(
    label: str,
    period: str,
    start: date,
    end: date,
    trades_count: int,
    net_worth: float | None,
    net_worth_formatted: str | None,
) -> str:
    """组装结构化的复盘 content（中文）：客观变动 + 待填写的反思提示。"""
    nw_line = net_worth_formatted or (f"{net_worth}" if net_worth is not None else "（未取到，请手动补充）")
    return (
        f"# {label}复盘 {period}（{start.isoformat()} ~ {end.isoformat()}）\n"
        f"\n"
        f"## 本{ '月' if label == '月度' else '周' }客观变动（引用 Maybe 数据）\n"
        f"- 交易笔数：{trades_count}\n"
        f"- 当前净资产：{nw_line}\n"
        f"\n"
        f"## 决策回顾（待填写）\n"
        f"- 本{ '月' if label == '月度' else '周' }做了哪些决策？理由是否成立？\n"
        f"\n"
        f"## 经验教训（待填写）\n"
        f"- 哪些判断对了/错了？下次如何改进？\n"
        f"\n"
        f"## 下{ '月' if label == '月度' else '周' }计划（待填写）\n"
        f"- 关注点 / 待执行的调整 / 风险提示。\n"
    )


@cli.command("review")
@_config_opt
@click.option("--weekly", "weekly_flag", is_flag=True, help="Generate a weekly review (default)")
@click.option("--monthly", "monthly_flag", is_flag=True, help="Generate a monthly review")
@click.option("--dry-run", is_flag=True, help="Print what would be written without saving")
def review(config_path, weekly_flag, monthly_flag, dry_run):
    """Generate a weekly/monthly review skeleton and store it in Mem0.

    从 Maybe 拉取本周/本月的客观增量（交易笔数、净资产），组装一段含
    「客观变动 + 待填写反思提示」的复盘记忆，写入 Mem0。

    黄金法则：客观数字只作引用，复盘的价值在反思（决策回顾/教训/计划）。

    Example:
        memory review --weekly --dry-run
        memory review --monthly
    """
    if weekly_flag and monthly_flag:
        click.echo("Error: --weekly and --monthly are mutually exclusive.", err=True)
        raise SystemExit(1)

    monthly = monthly_flag  # 默认 weekly
    category = "monthly_review" if monthly else "weekly_review"
    label = "月度" if monthly else "周度"

    today = date.today()
    start, end, period = _period_bounds(monthly, today)

    # ── 从 Maybe 拉客观增量（优雅降级）──────────────────────────────────
    maybe_bin = _find_maybe()
    trades_count = 0
    net_worth = None
    net_worth_formatted = None

    if maybe_bin is None:
        click.echo(
            "Warning: `maybe` binary not found (checked PATH and ~/pyenv/maybe/bin/maybe). "
            "Objective deltas will be empty; please fill in reflections manually.",
            err=True,
        )
    else:
        trades_data = _run_maybe_json(
            maybe_bin,
            ["trades", "--start-date", start.isoformat(), "--end-date", end.isoformat()],
        )
        if isinstance(trades_data, dict):
            trades = trades_data.get("trades", [])
            if isinstance(trades, list):
                trades_count = len(trades)

        snapshot_data = _run_maybe_json(maybe_bin, ["snapshot"])
        if isinstance(snapshot_data, dict):
            net_worth = snapshot_data.get("net_worth")
            net_worth_formatted = snapshot_data.get("net_worth_formatted")

    content = _build_review_content(
        label, period, start, end, trades_count, net_worth, net_worth_formatted
    )

    metadata = {
        "period": period,
        "trades_count": trades_count,
        "net_worth_change": net_worth,
    }

    if dry_run:
        click.echo("=== DRY RUN — nothing will be written ===\n")
        click.echo(f"Category: {category}")
        click.echo(f"Period:   {period}")
        click.echo(f"Metadata: {json.dumps(metadata, ensure_ascii=False, default=str)}")
        click.echo("\nContent:")
        click.echo(content)
        return

    client = _get_client(config_path)
    result = client.add(content=content, category=category, metadata=metadata)

    memories = result.get("results", result.get("memories", [])) if isinstance(result, dict) else []
    mem_id = memories[0].get("id", "unknown") if isinstance(memories, list) and memories else "unknown"

    click.echo(f"{label}复盘已写入 Mem0: {mem_id}")
    click.echo(f"  Category: {category}")
    click.echo(f"  Period:   {period}")
    click.echo(f"  Trades:   {trades_count}")
    click.echo(f"  Net worth: {net_worth_formatted or net_worth or 'N/A'}")
    click.echo("\n提示：请补全 content 中「待填写」的决策回顾/经验教训/计划部分。")


# ── entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
