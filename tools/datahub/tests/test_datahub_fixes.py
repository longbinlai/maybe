"""
针对 datahub 工具包修复缺陷的回归测试。

运行方式（用 repo 源码而非已安装副本）：
  cd /Users/longbinlai/Documents/git/maybe && \
  PYTHONPATH=tools/datahub ~/pyenv/maybe/bin/python -m pytest \
    tools/datahub/tests/test_datahub_fixes.py -q
"""

import os
import numpy as np
import pandas as pd
import pytest

from datahub.core.base_source import DataItem
from datahub.sources import yfinance_source
from datahub.sources.yfinance_source import YFinanceSource
from datahub.sources.rss_source import RSSSource
from datahub.core.market_data_syncer import _fx_rate_is_sane


# ---------------------------------------------------------------------------
# 缺陷 1: yfinance 多 ticker 解析逻辑
# ---------------------------------------------------------------------------

def _multi_df(tickers, fail=None):
    """构造 MultiIndex DataFrame；fail 中的 ticker 全部为 NaN（模拟下载失败）。"""
    fail = fail or set()
    idx = pd.date_range("2024-01-01", periods=3)
    cols = pd.MultiIndex.from_product(
        [tickers, ["Open", "High", "Low", "Close", "Volume"]]
    )
    df = pd.DataFrame(np.arange(len(idx) * len(cols)).reshape(len(idx), len(cols)) + 1.0,
                      index=idx, columns=cols)
    for t in fail:
        for field in ["Open", "High", "Low", "Close", "Volume"]:
            df[(t, field)] = np.nan
    return df


def _flat_df():
    """构造扁平列 DataFrame（单 ticker 下载时 yf 的返回形态）。"""
    idx = pd.date_range("2024-01-01", periods=3)
    return pd.DataFrame(
        np.arange(15).reshape(3, 5) + 1.0,
        index=idx,
        columns=["Open", "High", "Low", "Close", "Volume"],
    )


def _make_source(tickers, monkeypatch, df):
    src = YFinanceSource("test_yf", {"tickers": tickers, "data_type": "price"})
    monkeypatch.setattr(yfinance_source.yf, "download", lambda *a, **k: df)
    return src


def test_multi_ticker_parses_each_independently(monkeypatch):
    """多 ticker 正常情况：每个 ticker 得到自己的数据。"""
    df = _multi_df(["AAPL", "MSFT"])
    src = _make_source(["AAPL", "MSFT"], monkeypatch, df)
    result = src.fetch()
    tickers = sorted(i.metadata["ticker"] for i in result.items)
    assert tickers == ["AAPL", "MSFT"]
    prices = {i.metadata["ticker"]: i.metadata["price"] for i in result.items}
    assert prices["AAPL"] != prices["MSFT"]  # 不同 ticker 数据不应相同


def test_multi_ticker_skips_failed_ticker(monkeypatch):
    """多 ticker 中某个下载失败（全 NaN），应被跳过而不混入错误数据。"""
    df = _multi_df(["AAPL", "BAD"], fail={"BAD"})
    src = _make_source(["AAPL", "BAD"], monkeypatch, df)
    result = src.fetch()
    tickers = [i.metadata["ticker"] for i in result.items]
    assert tickers == ["AAPL"]


def test_multi_ticker_flat_df_does_not_duplicate(monkeypatch):
    """核心修复点：请求多 ticker 但 yf 返回扁平列时，
    不能把同一份 df 套到每个 ticker。修复前会为每个 ticker 都产出一条
    （重复错误数据），修复后应全部跳过。"""
    df = _flat_df()
    src = _make_source(["AAPL", "MSFT"], monkeypatch, df)
    result = src.fetch()
    # 扁平列无法可靠归属到多个 ticker -> 不应产出任何带错误归属的数据
    assert result.items == []


def test_single_ticker_flat_df_still_works(monkeypatch):
    """单 ticker 请求返回扁平列：仍应正常解析。"""
    df = _flat_df()
    src = _make_source(["AAPL"], monkeypatch, df)
    result = src.fetch()
    assert len(result.items) == 1
    assert result.items[0].metadata["ticker"] == "AAPL"


# ---------------------------------------------------------------------------
# 缺陷 2: ID 去重确定性
# ---------------------------------------------------------------------------

def test_generate_id_deterministic():
    a = DataItem.generate_id("yf", "AAPL", "2024-01-03T00:00:00")
    b = DataItem.generate_id("yf", "AAPL", "2024-01-03T00:00:00")
    assert a == b


def test_yfinance_id_stable_across_runs(monkeypatch):
    """相同 (source, ticker, date) 两次抓取应生成相同 ID（去重依赖）。"""
    df1 = _multi_df(["AAPL", "MSFT"])
    src1 = _make_source(["AAPL", "MSFT"], monkeypatch, df1)
    ids1 = {i.metadata["ticker"]: i.id for i in src1.fetch().items}

    # 第二次：同样的日期索引，新的 DataFrame 对象
    df2 = _multi_df(["AAPL", "MSFT"])
    src2 = _make_source(["AAPL", "MSFT"], monkeypatch, df2)
    ids2 = {i.metadata["ticker"]: i.id for i in src2.fetch().items}

    assert ids1 == ids2


def test_yfinance_id_uses_normalized_date(monkeypatch):
    """ID 应基于规范化 ISO 日期，而非 pandas Timestamp 的 str() 表示。"""
    df = _multi_df(["AAPL", "MSFT"])
    src = _make_source(["AAPL", "MSFT"], monkeypatch, df)
    item = next(i for i in src.fetch().items if i.metadata["ticker"] == "AAPL")
    expected = DataItem.generate_id("test_yf", "AAPL", item.published.isoformat())
    assert item.id == expected


# ---------------------------------------------------------------------------
# 缺陷 3: 汇率方向合理性校验
# ---------------------------------------------------------------------------

def test_fx_sanity_accepts_normal_rates():
    assert _fx_rate_is_sane("USD", "CNY", 7.1)
    assert _fx_rate_is_sane("USD", "JPY", 150.0)
    assert _fx_rate_is_sane("EUR", "USD", 1.08)


def test_fx_sanity_rejects_inverted_rate():
    # USD->CNY 误返回 CNY->USD (~0.14)
    assert not _fx_rate_is_sane("USD", "CNY", 0.14)
    # EUR->USD 误返回反向 (~0.93 仍在区间内不会被拦，但极端反向值会)
    assert not _fx_rate_is_sane("USD", "JPY", 0.0066)


def test_fx_sanity_rejects_nonpositive():
    assert not _fx_rate_is_sane("USD", "CNY", 0)
    assert not _fx_rate_is_sane("USD", "CNY", -1)


def test_fx_sanity_unknown_pair_passes_positive():
    assert _fx_rate_is_sane("GBP", "SGD", 1.7)
    assert not _fx_rate_is_sane("GBP", "SGD", -1)


# ---------------------------------------------------------------------------
# 缺陷 4: RSS SSL 校验默认开启 + 显式开关
# ---------------------------------------------------------------------------

def test_rss_ssl_verify_default_on(monkeypatch):
    monkeypatch.delenv("DATAHUB_RSS_INSECURE", raising=False)
    src = RSSSource("feed", {"url": "https://example.com/rss"})
    assert src.verify_ssl is True


def test_rss_ssl_insecure_via_config():
    src = RSSSource("feed", {"url": "https://example.com/rss", "insecure": True})
    assert src.verify_ssl is False


def test_rss_ssl_verify_ssl_field_overrides():
    src = RSSSource("feed", {"url": "https://example.com/rss", "verify_ssl": False})
    assert src.verify_ssl is False


def test_rss_ssl_insecure_via_env(monkeypatch):
    monkeypatch.setenv("DATAHUB_RSS_INSECURE", "1")
    src = RSSSource("feed", {"url": "https://example.com/rss"})
    assert src.verify_ssl is False


def test_rss_fetch_passes_verify_flag(monkeypatch):
    """fetch() 应把 verify 标志透传给 requests.get（默认 True）。"""
    captured = {}

    class _Resp:
        content = b"<rss></rss>"

        def raise_for_status(self):
            pass

    def fake_get(url, headers=None, timeout=None, verify=None):
        captured["verify"] = verify
        return _Resp()

    import datahub.sources.rss_source as rss_mod
    monkeypatch.delenv("DATAHUB_RSS_INSECURE", raising=False)
    monkeypatch.setattr(rss_mod.requests, "get", fake_get)

    src = RSSSource("feed", {"url": "https://example.com/rss"})
    src.fetch()
    assert captured["verify"] is True
