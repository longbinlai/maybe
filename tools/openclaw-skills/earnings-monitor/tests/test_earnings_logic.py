"""离线单元测试：财年季度推算 + 营收新鲜度对账（earnings_monitor 纯函数）。

不碰网络。运行：
  ~/pyenv/maybe/bin/python -m pytest \
    tools/openclaw-skills/earnings-monitor/tests/test_earnings_logic.py -q
"""

import sys
from datetime import date
from pathlib import Path

# 把 skill 的 scripts 目录加入 path 后再导入（脚本非包，main 有 __main__ 守卫）
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import earnings_monitor as em  # noqa: E402


# ── compute_fiscal_quarter ────────────────────────────────────────────────

def test_micron_fq3_not_q2():
    # 美光财年 8 月底结束；财报期截至 2026-05-28 -> FQ3-2026（旧代码错标成 Q2）
    assert em.compute_fiscal_quarter(date(2026, 5, 28), 8) == (3, 2026)


def test_micron_full_fiscal_year_quarters():
    fye = 8  # 8 月末财年
    assert em.compute_fiscal_quarter(date(2025, 11, 27), fye) == (1, 2026)  # Q1 ends Nov
    assert em.compute_fiscal_quarter(date(2026, 2, 26), fye) == (2, 2026)   # Q2 ends Feb
    assert em.compute_fiscal_quarter(date(2026, 5, 28), fye) == (3, 2026)   # Q3 ends May
    assert em.compute_fiscal_quarter(date(2026, 8, 28), fye) == (4, 2026)   # Q4 ends Aug


def test_calendar_fiscal_year_dec_end():
    # 财年=自然年（12 月末）：季度号应等于自然季度
    assert em.compute_fiscal_quarter(date(2026, 3, 31), 12) == (1, 2026)
    assert em.compute_fiscal_quarter(date(2026, 6, 30), 12) == (2, 2026)
    assert em.compute_fiscal_quarter(date(2026, 9, 30), 12) == (3, 2026)
    assert em.compute_fiscal_quarter(date(2026, 12, 31), 12) == (4, 2026)


def test_compute_fiscal_quarter_invalid_inputs():
    assert em.compute_fiscal_quarter(None, 8) is None
    assert em.compute_fiscal_quarter(date(2026, 5, 28), None) is None
    assert em.compute_fiscal_quarter(date(2026, 5, 28), 0) is None
    assert em.compute_fiscal_quarter(date(2026, 5, 28), 13) is None


# ── period_label ──────────────────────────────────────────────────────────

def test_period_label_with_fye():
    assert em.period_label(date(2026, 5, 28), 8) == "FQ3-2026（截至 2026-05-28）"


def test_period_label_without_fye_falls_back_to_date():
    # 财年末月未知时只显示期末日，绝不臆造季度号
    assert em.period_label(date(2026, 5, 28), None) == "截至 2026-05-28"


def test_period_label_no_period_end():
    assert em.period_label(None, 8) == "财报期未知"


# ── assess_freshness ──────────────────────────────────────────────────────

def test_freshness_fresh_micron():
    # 发布日 2026-06-24，财报期截至 2026-05-28，相隔 27 天 -> 本次财报
    r = em.assess_freshness(date(2026, 6, 24), date(2026, 5, 28))
    assert r["fresh"] is True
    assert r["gap_days"] == 27


def test_freshness_stale_lagging_fundamentals():
    # 财报期还是上一季度（相隔 ~118 天）-> yfinance 基本面未更新，标 False
    r = em.assess_freshness(date(2026, 6, 24), date(2026, 2, 26))
    assert r["fresh"] is False
    assert "未确认" in r["note"]


def test_freshness_missing_data():
    assert em.assess_freshness(None, date(2026, 5, 28))["fresh"] is None
    assert em.assess_freshness(date(2026, 6, 24), None)["fresh"] is None


def test_freshness_period_after_announce_is_anomaly():
    r = em.assess_freshness(date(2026, 6, 24), date(2026, 7, 1))
    assert r["fresh"] is None
    assert "异常" in r["note"]


# ── epoch_to_date ─────────────────────────────────────────────────────────

def test_epoch_to_date_roundtrip():
    # 2026-08-28 ~ epoch；只验证月份正确即可（财年末月用途）
    d = em.epoch_to_date(1788000000)  # 2026-09-... range
    assert d is not None and d.year == 2026


def test_epoch_to_date_bad_input():
    assert em.epoch_to_date(None) is None
    assert em.epoch_to_date("not-a-number") is None


# ── quarter_key（去重键）──────────────────────────────────────────────────

def test_quarter_key_prefers_period_end():
    assert em.quarter_key(date(2026, 5, 28), date(2026, 6, 24)) == "2026-05-28"
    assert em.quarter_key(None, date(2026, 6, 24)) == "2026-06-24"
    assert em.quarter_key(None, None) == ""
