"""Markdown → Mem0 migration tool.

解析 memory/ 目录下的 Markdown 文件，提取结构化的投资决策、市场事件和回顾记录，
迁移到 Mem0 向量存储中。

⚠️ 遗留工具：markdown → migrate 是**一次性的手动迁移工具**，仅用于把历史的
   memory/*.md 文件搬进 Mem0。常规捕获已改为「决策时捕获 + 周度复盘」：
   - 决策时捕获：由 finance-write 的 `--reason` 触发，直接写入 Mem0。
   - 周度/月度复盘：由 `memory review --weekly/--monthly` 生成。
   不要再依赖「OpenClaw 写每日 markdown → migrate」这条链路（已废弃）。
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class MemoryEntry:
    """A single parsed memory entry from a Markdown file."""
    content: str
    category: str
    date: str
    title: str
    metadata: dict = field(default_factory=dict)
    source_file: str = ""


class MarkdownMigrator:
    """Parses Markdown memory files and produces structured MemoryEntry objects.

    支持的文件格式：
    - memory/YYYY-MM-DD.md: 每日决策记录和市场事件
    - memory/YYYY-MM-DD-weekly.md: 周度回顾
    - memory/YYYY-MM-monthly.md: 月度回顾
    """

    # 决策记录标题：### YYYY-MM-DD: 买入/卖出...
    DECISION_PATTERN = re.compile(
        r"^###\s+(\d{4}-\d{2}-\d{2})[:：]\s+(.+?)$",
        re.MULTILINE,
    )

    # 市场事件标题：### YYYY-MM-DD HH:MM: 事件标题
    EVENT_PATTERN = re.compile(
        r"^###\s+(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)[:：]\s+(.+?)$",
        re.MULTILINE,
    )

    # 字段提取：- **字段名**: 值
    FIELD_PATTERN = re.compile(
        r"-\s+\*\*(.+?)\*\*[:：]\s*(.+?)$",
        re.MULTILINE,
    )

    # 分类字段名到标准 key 的映射
    FIELD_ALIASES = {
        "行动": "action",
        "账户": "account",
        "证券": "security",
        "数量": "quantity",
        "价格": "price",
        "总价值": "total_value",
        "理由": "rationale",
        "预期结果": "expected_outcome",
        "信心指数": "confidence",
        "市场背景": "market_context",
        "状态": "status",
        "类别": "event_type",
        "市场": "market",
        "关键数据": "key_data",
        "情绪": "sentiment",
        "影响板块": "affected_sectors",
        "相关性": "relevance",
        "来源": "source",
        "链接": "link",
        "摘要": "summary",
    }

    # 决策相关关键词（用于区分决策和市场事件）
    DECISION_KEYWORDS = {
        "买入", "卖出", "加仓", "减仓", "清仓", "调仓",
        "buy", "sell", "add", "remove",
        "行动", "账户", "证券", "数量", "价格",
    }

    def __init__(self, source_dir: str):
        """Initialize the migrator.

        Args:
            source_dir: Path to the memory/ directory containing Markdown files.
        """
        self.source_dir = Path(source_dir)
        if not self.source_dir.is_dir():
            raise FileNotFoundError(f"Directory not found: {source_dir}")

    def parse_all(self) -> list[MemoryEntry]:
        """Parse all Markdown files in the source directory.

        Returns:
            List of parsed MemoryEntry objects.
        """
        entries = []

        # 收集所有 .md 文件
        md_files = sorted(self.source_dir.glob("*.md"))

        for filepath in md_files:
            filename = filepath.name

            # 跳过 MEMORY.md 等索引文件
            if filename == "MEMORY.md":
                continue

            # 判断文件类型
            if filename.endswith("-weekly.md"):
                entries.extend(self._parse_review_file(filepath, "weekly_review"))
            elif filename.endswith("-monthly.md"):
                entries.extend(self._parse_review_file(filepath, "monthly_review"))
            else:
                entries.extend(self._parse_daily_file(filepath))

        return entries

    def _parse_daily_file(self, filepath: Path) -> list[MemoryEntry]:
        """Parse a daily memory file (YYYY-MM-DD.md).

        每日文件可能包含决策记录和市场事件两种类型。
        """
        text = filepath.read_text(encoding="utf-8")
        entries = []

        # 从文件名提取日期
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", filepath.stem)
        file_date = date_match.group(1) if date_match else ""

        # 按 ### 标题分段
        sections = self._split_sections(text)

        for header, body in sections:
            # 提取日期和标题
            m = self.EVENT_PATTERN.match(f"### {header}")
            if not m:
                continue

            entry_date = m.group(1).strip()
            title = m.group(2).strip()

            # 提取字段
            fields = self._extract_fields(body)

            # 判断分类：含决策关键词→investment_decision，否则→market_view（不再产出已废弃的 market_event）
            category = self._classify_entry(title, fields)

            # 构建内容
            content = self._build_content(title, fields, body)

            # 构建 metadata
            metadata = {
                "date": entry_date or file_date,
                "title": title,
                "source_file": filepath.name,
            }
            metadata.update({
                self.FIELD_ALIASES.get(k, k): v
                for k, v in fields.items()
            })

            entries.append(MemoryEntry(
                content=content,
                category=category,
                date=metadata["date"],
                title=title,
                metadata=metadata,
                source_file=filepath.name,
            ))

        return entries

    def _parse_review_file(self, filepath: Path, category: str) -> list[MemoryEntry]:
        """Parse a weekly or monthly review file.

        将整个回顾文件作为一条记忆记录，保留完整内容。
        """
        text = filepath.read_text(encoding="utf-8")

        if not text.strip():
            return []

        # 从文件名提取日期
        date_match = re.match(r"(\d{4}-\d{2}(?:-\d{2})?)", filepath.stem)
        file_date = date_match.group(1) if date_match else ""

        # 提取文件标题（第一个 # 行）
        title_match = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else filepath.stem

        # 限制内容长度（月度/周度回顾可能很长）
        content = text.strip()
        if len(content) > 4000:
            content = content[:4000] + "\n\n... (truncated)"

        metadata = {
            "date": file_date,
            "title": title,
            "source_file": filepath.name,
            "review_type": "weekly" if "weekly" in category else "monthly",
        }

        return [MemoryEntry(
            content=content,
            category=category,
            date=file_date,
            title=title,
            metadata=metadata,
            source_file=filepath.name,
        )]

    def _split_sections(self, text: str) -> list[tuple[str, str]]:
        """Split text by ### headers, returning (header, body) pairs."""
        sections = []
        current_header = None
        current_body_lines = []

        for line in text.split("\n"):
            if line.startswith("### "):
                if current_header is not None:
                    sections.append((current_header, "\n".join(current_body_lines)))
                current_header = line[4:].strip()
                current_body_lines = []
            else:
                if current_header is not None:
                    current_body_lines.append(line)

        if current_header is not None:
            sections.append((current_header, "\n".join(current_body_lines)))

        return sections

    def _extract_fields(self, body: str) -> dict[str, str]:
        """Extract - **key**: value fields from a section body."""
        fields = {}
        for match in self.FIELD_PATTERN.finditer(body):
            key = match.group(1).strip()
            value = match.group(2).strip()
            fields[key] = value
        return fields

    def _classify_entry(self, title: str, fields: dict) -> str:
        """Classify an entry into a VALID active category.

        基于标题和字段中的关键词判断分类。
        绝不产出已废弃分类（如 market_event）——含决策关键词的归为
        investment_decision，其余的客观/市场类条目映射到 market_view
        （主观市场看法），而非已废弃的 market_event。
        """
        combined = f"{title} {' '.join(fields.keys())} {' '.join(fields.values())}".lower()

        for keyword in self.DECISION_KEYWORDS:
            if keyword.lower() in combined:
                return "investment_decision"

        # 历史上这里返回 market_event（已废弃）。现映射到有效分类 market_view，
        # 避免脏分类污染向量库。validate_category() 会再做一次兜底校验。
        return "market_view"

    def _build_content(self, title: str, fields: dict, body: str) -> str:
        """Build a natural-language content string for Mem0.

        将标题和字段组合成自然语言描述，便于向量搜索。
        """
        parts = [title]

        # 关键字段优先
        important_fields = [
            "行动", "证券", "数量", "价格", "理由",
            "预期结果", "信心指数", "市场背景",
            "摘要", "类别", "情绪",
        ]

        for field_name in important_fields:
            if field_name in fields:
                parts.append(f"{field_name}: {fields[field_name]}")

        # 其他字段
        for key, value in fields.items():
            if key not in important_fields:
                parts.append(f"{key}: {value}")

        return "\n".join(parts)

    def migrate(self, client, dry_run: bool = False) -> dict:
        """Run the migration.

        Args:
            client: A Mem0Client instance.
            dry_run: If True, only report what would be migrated.

        Returns:
            A dict with migration statistics.
        """
        entries = self.parse_all()

        stats = {
            "total_files": len(set(e.source_file for e in entries)),
            "total_entries": len(entries),
            "migrated": 0,
            "skipped": 0,
            "errors": [],
            "entries": entries,
        }

        if dry_run:
            return stats

        for entry in entries:
            try:
                client.add(
                    content=entry.content,
                    category=entry.category,
                    metadata=entry.metadata,
                )
                stats["migrated"] += 1
            except Exception as e:
                stats["skipped"] += 1
                stats["errors"].append({
                    "file": entry.source_file,
                    "title": entry.title,
                    "error": str(e),
                })

        return stats
