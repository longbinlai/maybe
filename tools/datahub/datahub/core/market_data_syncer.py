"""
市场数据同步器

从 Maybe DB 获取持仓，从 YF 获取价格，写回 Maybe DB
同样处理汇率数据
"""

import yfinance as yf
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from .maybe_db_writer import MaybeDBWriter


# 汇率方向/量级合理性区间（宽松 sanity 区间，不做精确拟合）。
# key 为 (from_currency, to_currency)，value 为 (min_rate, max_rate)。
# 目的：API 返回反向汇率或异常值时拒绝写入，避免污染 exchange_rates 表。
# 例如 USD->CNY 约 6-8，若 yf 误返回 ~0.14（CNY->USD）会被拦截。
_FX_SANITY_RANGES: Dict[Tuple[str, str], Tuple[float, float]] = {
    ("USD", "CNY"): (4.0, 12.0),
    ("USD", "JPY"): (80.0, 250.0),
    ("USD", "AUD"): (0.8, 2.5),
    ("EUR", "USD"): (0.7, 1.7),
}


def _fx_rate_is_sane(from_currency: str, to_currency: str, rate: float) -> bool:
    """校验汇率落在已知合理区间内。无定义区间的对默认通过（只做正数校验）。"""
    if rate is None or rate <= 0:
        return False
    bounds = _FX_SANITY_RANGES.get((from_currency, to_currency))
    if bounds is None:
        return True
    low, high = bounds
    return low <= rate <= high


class MarketDataSyncer:
    """市场数据同步器"""

    def __init__(self, maybe_db_writer: MaybeDBWriter = None):
        self.maybe_db = maybe_db_writer or MaybeDBWriter()

    def sync_holding_prices(self, dry_run: bool = False) -> Dict:
        """
        同步持仓价格

        流程：
        1. 从 Maybe DB 获取持仓 ticker
        2. 从 YF 批量获取价格
        3. 写入 Maybe DB security_prices 表

        Args:
            dry_run: 如果为 True，只返回结果不写入数据库

        Returns:
            {"updated": [...], "skipped": [...], "errors": [...]}
        """
        result = {"updated": [], "skipped": [], "errors": []}

        # 1. 获取持仓 ticker
        holdings = self.maybe_db.get_holdings_tickers()
        if not holdings:
            result["skipped"].append({"reason": "no holdings"})
            return result

        tickers = [h["ticker"] for h in holdings]
        print(f"📊 获取 {len(tickers)} 个持仓价格: {', '.join(tickers)}")

        # 2. 从 YF 批量获取价格
        try:
            df = yf.download(
                tickers,
                period="5d",
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=False,
            )

            if df.empty:
                result["skipped"].append({"reason": "yf returned empty data"})
                return result

        except Exception as e:
            result["errors"].append({"error": str(e)})
            return result

        # 3. 解析价格并写入 Maybe DB
        today = date.today()
        for holding in holdings:
            ticker = holding["ticker"]
            security_id = holding["security_id"]

            try:
                # 提取单个 ticker 的价格
                if len(tickers) == 1:
                    ticker_df = df
                else:
                    ticker_df = df[ticker] if ticker in df.columns.get_level_values(0) else None

                if ticker_df is None or ticker_df.empty:
                    result["skipped"].append({"ticker": ticker, "reason": "no data"})
                    continue

                # 获取最近 5 天的价格
                prices = []
                for idx, row in ticker_df.tail(5).iterrows():
                    close_price = row["Close"]
                    if not isinstance(close_price, (int, float)):
                        continue
                    prices.append({
                        "date": idx.date() if hasattr(idx, 'date') else today,
                        "price": float(close_price)
                    })

                if not prices:
                    result["skipped"].append({"ticker": ticker, "reason": "no valid prices"})
                    continue

                # 写入 Maybe DB
                if not dry_run:
                    affected = self.maybe_db.upsert_security_prices(
                        security_id=security_id,
                        prices=prices,
                        currency="USD"
                    )
                    result["updated"].append({
                        "ticker": ticker,
                        "security_id": security_id,
                        "prices": prices,
                        "affected_rows": affected
                    })
                else:
                    result["updated"].append({
                        "ticker": ticker,
                        "security_id": security_id,
                        "prices": prices,
                        "dry_run": True
                    })

            except Exception as e:
                result["errors"].append({"ticker": ticker, "error": str(e)})

        return result

    def sync_exchange_rates(self, dry_run: bool = False) -> Dict:
        """
        同步汇率

        流程：
        1. 定义需要获取的汇率对
        2. 从 YF 获取汇率
        3. 写入 Maybe DB exchange_rates 表

        Args:
            dry_run: 如果为 True，只返回结果不写入数据库

        Returns:
            {"updated": [...], "skipped": [...], "errors": [...]}
        """
        result = {"updated": [], "skipped": [], "errors": []}

        # 定义汇率对
        fx_pairs = [
            ("USDCNY=X", "USD", "CNY"),
            ("USDJPY=X", "USD", "JPY"),
            ("USDAUD=X", "USD", "AUD"),
            ("EURUSD=X", "EUR", "USD"),
        ]

        tickers = [pair[0] for pair in fx_pairs]
        print(f"💱 获取 {len(tickers)} 个汇率: {', '.join(tickers)}")

        # 从 YF 批量获取
        try:
            df = yf.download(
                tickers,
                period="5d",
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=False,
            )

            if df.empty:
                result["skipped"].append({"reason": "yf returned empty data"})
                return result

        except Exception as e:
            result["errors"].append({"error": str(e)})
            return result

        # 解析并写入
        today = date.today()
        for ticker, from_currency, to_currency in fx_pairs:
            try:
                # 提取汇率数据
                if len(tickers) == 1:
                    ticker_df = df
                else:
                    ticker_df = df[ticker] if ticker in df.columns.get_level_values(0) else None

                if ticker_df is None or ticker_df.empty:
                    result["skipped"].append({"pair": f"{from_currency}/{to_currency}", "reason": "no data"})
                    continue

                # 获取最近 5 天的汇率
                rates = []
                for idx, row in ticker_df.tail(5).iterrows():
                    close_rate = row["Close"]
                    if not isinstance(close_rate, (int, float)):
                        continue
                    rate_val = float(close_rate)
                    # 方向/量级合理性校验：拒绝明显反向或异常的汇率，
                    # 避免 API 异常时写入错误数据。
                    if not _fx_rate_is_sane(from_currency, to_currency, rate_val):
                        result["skipped"].append({
                            "pair": f"{from_currency}/{to_currency}",
                            "reason": f"rate {rate_val} out of sanity range",
                        })
                        continue
                    rates.append({
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "rate": rate_val,
                        "date": idx.date() if hasattr(idx, 'date') else today
                    })

                if not rates:
                    result["skipped"].append({"pair": f"{from_currency}/{to_currency}", "reason": "no valid rates"})
                    continue

                # 写入 Maybe DB
                if not dry_run:
                    affected = self.maybe_db.upsert_exchange_rates(rates)
                    result["updated"].append({
                        "pair": f"{from_currency}/{to_currency}",
                        "rates": rates,
                        "affected_rows": affected
                    })
                else:
                    result["updated"].append({
                        "pair": f"{from_currency}/{to_currency}",
                        "rates": rates,
                        "dry_run": True
                    })

            except Exception as e:
                result["errors"].append({"pair": f"{from_currency}/{to_currency}", "error": str(e)})

        return result

    def sync_all(self, dry_run: bool = False) -> Dict:
        """
        同步所有市场数据

        Returns:
            {"holdings": {...}, "fx": {...}}
        """
        print("\n" + "="*60)
        print("🔄 同步市场数据")
        print("="*60)

        result = {
            "holdings": self.sync_holding_prices(dry_run),
            "fx": self.sync_exchange_rates(dry_run)
        }

        # 打印汇总
        print("\n" + "="*60)
        print("📈 同步结果汇总")
        print("="*60)

        # 持仓
        h = result["holdings"]
        print(f"\n持仓价格:")
        print(f"  ✅ 更新: {len(h['updated'])}")
        print(f"  ⏭️  跳过: {len(h['skipped'])}")
        print(f"  ❌ 错误: {len(h['errors'])}")

        # 汇率
        fx = result["fx"]
        print(f"\n汇率:")
        print(f"  ✅ 更新: {len(fx['updated'])}")
        print(f"  ⏭️  跳过: {len(fx['skipped'])}")
        print(f"  ❌ 错误: {len(fx['errors'])}")

        return result
