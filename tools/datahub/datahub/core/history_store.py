"""
历史数据存储 — PostgreSQL (analytics schema)

将 DataHub 获取的数据持久化到 Maybe 的 PostgreSQL 数据库中，
使用独立的 analytics schema 避免与 Maybe 的 public schema 冲突。

功能：
- UPSERT 写入数据项（ON CONFLICT DO NOTHING）
- 按源、类别、时间、关键词查询历史数据
- 基于 retention_days 的过期清理
- 获取日志记录与统计
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# psycopg2 是可选依赖，延迟导入避免未安装时影响其他功能
_psycopg2 = None


def _get_psycopg2():
    global _psycopg2
    if _psycopg2 is None:
        try:
            import psycopg2
            import psycopg2.extras
            _psycopg2 = psycopg2
        except ImportError:
            raise ImportError(
                "psycopg2-binary 未安装。请运行: "
                "~/pyenv/maybe/bin/pip install psycopg2-binary"
            )
    return _psycopg2


# ── 默认保留天数 ────────────────────────────────────────────────
DEFAULT_RETENTION = {
    "rss": 180,
    "yfinance_price": 365,
    "yfinance_news": 90,
    "newsapi": 90,
}

FETCH_LOG_RETENTION_DAYS = 30


class HistoryStore:
    """
    PostgreSQL 历史数据存储

    使用 analytics schema，与 Maybe 的 public schema 隔离。
    连接失败时 graceful degrade — 不影响 DataHub 主流程。
    """

    def __init__(self, connection_string: str = None):
        """
        初始化连接

        Args:
            connection_string: PostgreSQL DSN。优先从参数读取，
                               其次从 MAYBE_DB_URL 环境变量，
                               最后使用默认值（db:5432）
        """
        self.connection_string = (
            connection_string
            or os.environ.get("MAYBE_DB_URL")
            or "postgresql://maybe_user:maybe_password@db:5432/maybe_production"
        )
        self._conn = None
        self._available = False

        try:
            self._connect()
            self.ensure_schema()
            self._available = True
            logger.info("HistoryStore: PostgreSQL 连接成功")
        except Exception as e:
            logger.warning(f"HistoryStore: PostgreSQL 不可用 ({e})，历史存储已禁用")

    @property
    def available(self) -> bool:
        """数据库是否可用"""
        return self._available

    def _connect(self):
        """建立数据库连接"""
        psycopg2 = _get_psycopg2()
        self._conn = psycopg2.connect(self.connection_string)
        self._conn.autocommit = True

    def _execute(self, sql: str, params=None, fetch=False):
        """执行 SQL，自动重连"""
        psycopg2 = _get_psycopg2()
        try:
            with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                if fetch:
                    return [dict(row) for row in cur.fetchall()]
                return cur.rowcount
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            # 连接断开，重连后重试
            logger.warning("HistoryStore: 连接断开，尝试重连...")
            self._connect()
            with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                if fetch:
                    return [dict(row) for row in cur.fetchall()]
                return cur.rowcount

    # ── Schema 管理 ─────────────────────────────────────────────

    def ensure_schema(self):
        """创建 analytics schema 和所需的表（如果不存在）"""
        self._execute("""
            CREATE SCHEMA IF NOT EXISTS analytics;
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS analytics.datahub_items (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                category TEXT,
                title TEXT NOT NULL,
                content TEXT,
                url TEXT,
                published_at TIMESTAMPTZ,
                metadata JSONB DEFAULT '{}',
                fetched_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        self._execute("""
            CREATE INDEX IF NOT EXISTS idx_datahub_source
                ON analytics.datahub_items(source, fetched_at DESC);
        """)

        self._execute("""
            CREATE INDEX IF NOT EXISTS idx_datahub_published
                ON analytics.datahub_items(published_at DESC);
        """)

        self._execute("""
            CREATE INDEX IF NOT EXISTS idx_datahub_category
                ON analytics.datahub_items(category);
        """)

        # 全文搜索索引 — 'simple' 配置支持中文
        self._execute("""
            CREATE INDEX IF NOT EXISTS idx_datahub_fulltext
                ON analytics.datahub_items
                USING gin(to_tsvector('simple',
                    coalesce(title, '') || ' ' || coalesce(content, '')));
        """)

        # 执行日志表
        self._execute("""
            CREATE TABLE IF NOT EXISTS analytics.fetch_logs (
                id BIGSERIAL PRIMARY KEY,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                items_count INTEGER DEFAULT 0,
                duration_ms INTEGER,
                error TEXT,
                fetched_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        logger.info("HistoryStore: schema 和表已就绪")

    # ── 数据写入 ────────────────────────────────────────────────

    def save_items(self, source_name: str, items: list):
        """
        保存数据项到历史存储

        使用 UPSERT (ON CONFLICT DO NOTHING) 避免重复写入。
        同一数据项的内容不会变化，所以 DO NOTHING 即可。

        Args:
            source_name: 数据源名称
            items: DataItem 列表
        """
        if not self._available or not items:
            return 0

        psycopg2 = _get_psycopg2()
        inserted = 0

        try:
            with self._conn.cursor() as cur:
                for item in items:
                    item_dict = item.to_dict() if hasattr(item, "to_dict") else item
                    cur.execute("""
                        INSERT INTO analytics.datahub_items
                            (id, source, category, title, content, url, published_at, metadata)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (
                        item_dict["id"],
                        item_dict.get("source", source_name),
                        item_dict.get("category"),
                        item_dict.get("title", ""),
                        item_dict.get("content"),
                        item_dict.get("url"),
                        self._parse_datetime(item_dict.get("published")),
                        json.dumps(item_dict.get("metadata", {}), ensure_ascii=False),
                    ))
                    if cur.rowcount > 0:
                        inserted += 1

            if inserted > 0:
                logger.info(f"HistoryStore: {source_name} 写入 {inserted}/{len(items)} 条新数据")

            return inserted

        except Exception as e:
            logger.error(f"HistoryStore: 写入失败 ({source_name}): {e}")
            return 0

    def log_fetch(self, source_name: str, status: str, items_count: int,
                  duration_ms: int = None, error: str = None):
        """
        记录一次数据获取的执行日志

        Args:
            source_name: 数据源名称
            status: 获取状态 (success/failed/degraded)
            items_count: 获取的数据项数量
            duration_ms: 耗时（毫秒）
            error: 错误信息（如果有）
        """
        if not self._available:
            return

        try:
            self._execute("""
                INSERT INTO analytics.fetch_logs
                    (source, status, items_count, duration_ms, error)
                VALUES (%s, %s, %s, %s, %s)
            """, (source_name, status, items_count, duration_ms, error))
        except Exception as e:
            logger.error(f"HistoryStore: 写入 fetch_log 失败: {e}")

    # ── 查询 ────────────────────────────────────────────────────

    def query(self, source: str = None, category: str = None,
              from_date=None, to_date=None, keyword: str = None,
              limit: int = 50) -> List[Dict[str, Any]]:
        """
        查询历史数据

        Args:
            source: 数据源名称过滤
            category: 类别过滤
            from_date: 起始日期 (datetime 或 ISO 字符串)
            to_date: 截止日期
            keyword: 全文搜索关键词
            limit: 返回条数上限

        Returns:
            匹配的数据项列表（按 published_at DESC 排序）
        """
        if not self._available:
            return []

        conditions = []
        params = []

        if source:
            conditions.append("source = %s")
            params.append(source)

        if category:
            conditions.append("category = %s")
            params.append(category)

        if from_date:
            conditions.append("published_at >= %s")
            params.append(self._parse_datetime(from_date))

        if to_date:
            conditions.append("published_at <= %s")
            params.append(self._parse_datetime(to_date))

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # 关键词搜索：用 ILIKE 同时支持中文和英文
        # （PostgreSQL 'simple' 分词器对中文效果差，ILIKE 更可靠）
        if keyword:
            ilike_condition = (
                "(title ILIKE %s OR content ILIKE %s)"
            )
            if where_clause:
                where_clause += f" AND {ilike_condition}"
            else:
                where_clause = f"WHERE {ilike_condition}"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        sql = f"""
            SELECT id, source, category, title, content, url,
                   published_at, metadata, fetched_at
            FROM analytics.datahub_items
            {where_clause}
            ORDER BY published_at DESC
            LIMIT %s
        """
        params.append(limit)

        try:
            rows = self._execute(sql, params, fetch=True)
            # 将 datetime 对象转为 ISO 字符串方便序列化
            for row in rows:
                for key in ("published_at", "fetched_at"):
                    if row.get(key) and isinstance(row[key], datetime):
                        row[key] = row[key].isoformat()
                if row.get("metadata") and isinstance(row["metadata"], str):
                    row["metadata"] = json.loads(row["metadata"])
            return rows
        except Exception as e:
            logger.error(f"HistoryStore: 查询失败: {e}")
            return []

    def query_fetch_logs(self, source: str = None, limit: int = 20) -> List[Dict]:
        """查询执行日志"""
        if not self._available:
            return []

        where = ""
        params = []
        if source:
            where = "WHERE source = %s"
            params.append(source)

        params.append(limit)
        sql = f"""
            SELECT * FROM analytics.fetch_logs
            {where}
            ORDER BY fetched_at DESC
            LIMIT %s
        """

        try:
            rows = self._execute(sql, params, fetch=True)
            for row in rows:
                if row.get("fetched_at") and isinstance(row["fetched_at"], datetime):
                    row["fetched_at"] = row["fetched_at"].isoformat()
            return rows
        except Exception as e:
            logger.error(f"HistoryStore: 查询 fetch_logs 失败: {e}")
            return []

    # ── 清理 ────────────────────────────────────────────────────

    def cleanup(self, retention_days: int = None, source: str = None,
                dry_run: bool = False) -> Dict[str, Any]:
        """
        清理过期数据

        Args:
            retention_days: 保留天数（覆盖所有源的默认值）
            source: 仅清理指定源
            dry_run: 仅统计，不实际删除

        Returns:
            清理统计信息
        """
        if not self._available:
            return {"error": "数据库不可用"}

        result = {"deleted_items": 0, "deleted_logs": 0, "by_source": {}}

        # 清理数据项 — 按源类型使用不同保留期限
        if source:
            # 清理指定源
            days = retention_days or 180
            deleted = self._cleanup_source_items(source, days, dry_run)
            result["by_source"][source] = deleted
            result["deleted_items"] += deleted
        else:
            # 按源分组清理，使用各源配置的 retention_days
            sources_in_db = self._get_distinct_sources()
            for src in sources_in_db:
                days = retention_days or self._get_retention_days(src)
                deleted = self._cleanup_source_items(src, days, dry_run)
                result["by_source"][src] = deleted
                result["deleted_items"] += deleted

        # 清理 fetch_logs（统一 30 天）
        log_sql = """
            DELETE FROM analytics.fetch_logs
            WHERE fetched_at < NOW() - INTERVAL '%s days'
        """
        if not dry_run:
            try:
                # 使用参数化查询不能直接用在 INTERVAL 中，改用拼接
                psycopg2 = _get_psycopg2()
                with self._conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM analytics.fetch_logs WHERE fetched_at < NOW() - make_interval(days => %s)",
                        (FETCH_LOG_RETENTION_DAYS,)
                    )
                    result["deleted_logs"] = cur.rowcount
            except Exception as e:
                logger.error(f"HistoryStore: 清理 fetch_logs 失败: {e}")
        else:
            try:
                rows = self._execute(
                    "SELECT COUNT(*) as cnt FROM analytics.fetch_logs WHERE fetched_at < NOW() - make_interval(days => %s)",
                    (FETCH_LOG_RETENTION_DAYS,),
                    fetch=True,
                )
                result["deleted_logs"] = rows[0]["cnt"] if rows else 0
            except Exception:
                pass

        action = "将删除" if dry_run else "已删除"
        logger.info(
            f"HistoryStore: {action} {result['deleted_items']} 条数据项, "
            f"{result['deleted_logs']} 条执行日志"
        )
        return result

    def _cleanup_source_items(self, source_name: str, days: int, dry_run: bool) -> int:
        """清理指定源的过期数据项"""
        try:
            if dry_run:
                rows = self._execute(
                    "SELECT COUNT(*) as cnt FROM analytics.datahub_items "
                    "WHERE source = %s AND fetched_at < NOW() - make_interval(days => %s)",
                    (source_name, days),
                    fetch=True,
                )
                return rows[0]["cnt"] if rows else 0
            else:
                return self._execute(
                    "DELETE FROM analytics.datahub_items "
                    "WHERE source = %s AND fetched_at < NOW() - make_interval(days => %s)",
                    (source_name, days),
                )
        except Exception as e:
            logger.error(f"HistoryStore: 清理 {source_name} 失败: {e}")
            return 0

    def _get_distinct_sources(self) -> List[str]:
        """获取数据库中所有不同的源名称"""
        try:
            rows = self._execute(
                "SELECT DISTINCT source FROM analytics.datahub_items", fetch=True
            )
            return [row["source"] for row in rows]
        except Exception:
            return []

    def _get_retention_days(self, source_name: str) -> int:
        """
        根据源名称推断保留天数

        规则基于 sources.yaml 中的源类型：
        - yfinance_*_news → 90 天
        - yfinance_* (价格) → 365 天
        - newsapi_* → 90 天
        - 其他 RSS → 180 天
        """
        name = source_name.lower()
        if "news" in name and "yfinance" in name:
            return DEFAULT_RETENTION["yfinance_news"]
        if name.startswith("yfinance_"):
            return DEFAULT_RETENTION["yfinance_price"]
        if name.startswith("newsapi"):
            return DEFAULT_RETENTION["newsapi"]
        return DEFAULT_RETENTION["rss"]

    # ── 统计 ────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """
        返回存储统计信息

        Returns:
            包含总条数、各源条数、最早/最新时间、磁盘占用等
        """
        if not self._available:
            return {"error": "数据库不可用"}

        result = {}

        try:
            # 总条数
            rows = self._execute(
                "SELECT COUNT(*) as total FROM analytics.datahub_items", fetch=True
            )
            result["total_items"] = rows[0]["total"] if rows else 0

            # 按源统计
            rows = self._execute("""
                SELECT source, COUNT(*) as count,
                       MIN(published_at) as earliest,
                       MAX(published_at) as latest
                FROM analytics.datahub_items
                GROUP BY source
                ORDER BY count DESC
            """, fetch=True)
            result["by_source"] = []
            for row in rows:
                entry = {
                    "source": row["source"],
                    "count": row["count"],
                    "earliest": row["earliest"].isoformat() if row.get("earliest") else None,
                    "latest": row["latest"].isoformat() if row.get("latest") else None,
                }
                result["by_source"].append(entry)

            # fetch_logs 条数
            rows = self._execute(
                "SELECT COUNT(*) as total FROM analytics.fetch_logs", fetch=True
            )
            result["total_fetch_logs"] = rows[0]["total"] if rows else 0

            # 表大小（需要 pg_total_relation_size）
            rows = self._execute("""
                SELECT
                    pg_size_pretty(pg_total_relation_size('analytics.datahub_items')) as items_size,
                    pg_size_pretty(pg_total_relation_size('analytics.fetch_logs')) as logs_size
            """, fetch=True)
            if rows:
                result["items_table_size"] = rows[0].get("items_size", "unknown")
                result["logs_table_size"] = rows[0].get("logs_size", "unknown")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"HistoryStore: 获取统计信息失败: {e}")

        return result

    # ── 工具方法 ────────────────────────────────────────────────

    @staticmethod
    def _parse_datetime(value) -> Optional[datetime]:
        """解析多种日期格式"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in (
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
            ):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._available = False

    def __del__(self):
        self.close()
