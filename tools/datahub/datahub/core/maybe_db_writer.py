"""
Maybe Finance 数据库写入器

将持仓价格和汇率写入 Maybe Finance 的 PostgreSQL 数据库
- security_prices 表：股价历史
- exchange_rates 表：汇率历史
"""

import os
import psycopg2
import psycopg2.extras
from datetime import date, datetime
from typing import Dict, List, Optional
from pathlib import Path


class MaybeDBWriter:
    """Maybe Finance 数据库写入器"""

    def __init__(self, db_url: Optional[str] = None):
        """
        初始化数据库连接

        Args:
            db_url: PostgreSQL 连接字符串，默认从环境变量 MAYBE_DATABASE_URL 读取
        """
        self.db_url = db_url or os.environ.get(
            "MAYBE_DATABASE_URL",
            "postgresql://maybe_user:maybe_password@db:5432/maybe_production"
        )
        self.conn = None
        self._connect()

    def _connect(self):
        """建立数据库连接"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.conn.autocommit = True
            print(f"✅ Maybe DB 连接成功")
        except Exception as e:
            print(f"⚠️ Maybe DB 连接失败: {e}")
            self.conn = None

    def is_available(self) -> bool:
        """检查数据库是否可用"""
        return self.conn is not None and self.conn.closed == 0

    def upsert_security_prices(
        self,
        security_id: str,
        prices: List[Dict],
        currency: str = "USD"
    ) -> int:
        """
        写入证券价格历史

        Args:
            security_id: Security UUID
            prices: 价格列表 [{"date": date, "price": float}, ...]
            currency: 货币代码

        Returns:
            写入的行数
        """
        if not self.is_available():
            print("⚠️ Maybe DB 不可用，跳过价格写入")
            return 0

        if not prices:
            return 0

        try:
            cursor = self.conn.cursor()

            # UPSERT：如果存在则更新，否则插入
            query = """
                INSERT INTO security_prices (id, security_id, date, price, currency, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (security_id, date, currency)
                DO UPDATE SET price = EXCLUDED.price, updated_at = NOW()
            """

            values = []
            for p in prices:
                values.append((
                    str(uuid.uuid4()),  # id
                    security_id,
                    p["date"],
                    p["price"],
                    currency
                ))

            psycopg2.extras.execute_values(cursor, query, values)
            affected = len(values)

            cursor.close()
            print(f"✅ 写入 {affected} 条价格记录 (security_id={security_id[:8]}...)")
            return affected

        except Exception as e:
            print(f"⚠️ 写入价格失败: {e}")
            self._reconnect()
            return 0

    def upsert_exchange_rates(
        self,
        rates: List[Dict]
    ) -> int:
        """
        写入汇率历史

        Args:
            rates: 汇率列表 [
                {
                    "from_currency": "USD",
                    "to_currency": "CNY",
                    "rate": 7.25,
                    "date": date
                },
                ...
            ]

        Returns:
            写入的行数
        """
        if not self.is_available():
            print("⚠️ Maybe DB 不可用，跳过汇率写入")
            return 0

        if not rates:
            return 0

        try:
            cursor = self.conn.cursor()

            # UPSERT
            query = """
                INSERT INTO exchange_rates (id, from_currency, to_currency, rate, date, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (from_currency, to_currency, date)
                DO UPDATE SET rate = EXCLUDED.rate, updated_at = NOW()
            """

            values = []
            for r in rates:
                values.append((
                    str(uuid.uuid4()),  # id
                    r["from_currency"],
                    r["to_currency"],
                    r["rate"],
                    r["date"]
                ))

            psycopg2.extras.execute_values(cursor, query, values)
            affected = len(values)

            cursor.close()
            print(f"✅ 写入 {affected} 条汇率记录")
            return affected

        except Exception as e:
            print(f"⚠️ 写入汇率失败: {e}")
            self._reconnect()
            return 0

    def get_holdings_tickers(self) -> List[Dict]:
        """
        获取所有持仓的 ticker 列表

        Returns:
            [{"ticker": "AAPL", "security_id": "uuid"}, ...]
        """
        if not self.is_available():
            print("⚠️ Maybe DB 不可用，无法获取持仓")
            return []

        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # 查询所有持仓的证券信息（去重）
            query = """
                SELECT DISTINCT s.ticker, s.id as security_id
                FROM holdings h
                JOIN securities s ON h.security_id = s.id
                ORDER BY s.ticker
            """

            cursor.execute(query)
            results = cursor.fetchall()

            tickers = [
                {"ticker": row["ticker"], "security_id": row["security_id"]}
                for row in results
            ]

            cursor.close()
            print(f"✅ 获取 {len(tickers)} 个持仓 ticker")
            return tickers

        except Exception as e:
            print(f"⚠️ 获取持仓失败: {e}")
            self._reconnect()
            return []

    def _reconnect(self):
        """尝试重新连接"""
        try:
            if self.conn:
                self.conn.close()
        except:
            pass

        try:
            self._connect()
        except:
            pass

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("✅ Maybe DB 连接已关闭")


# 需要导入 uuid
import uuid
