"""Tests for portfolio allocation analysis (maybe_cli.portfolio).

纯函数测试，不需要 Maybe 服务。用合成的 snapshot/汇率/policy。
运行: PYTHONPATH=tools/maybe-cli ~/pyenv/maybe/bin/python -m pytest \
        tools/maybe-cli/tests/test_portfolio.py -q
"""

from maybe_cli.portfolio import (
    build_fx_converter,
    classify_account,
    analyze,
    DEFAULT_POLICY,
    load_policy,
)


# ── FX 换算 ──────────────────────────────────────────────────────────────

def test_fx_identity_for_base():
    conv = build_fx_converter([], "USD")
    assert conv(100, "USD") == 100


def test_fx_direct_and_inverse():
    rates = [{"from_currency": "CNY", "to_currency": "USD", "rate": 0.14}]
    conv = build_fx_converter(rates, "USD")
    assert round(conv(100, "CNY"), 6) == 14.0  # direct
    # inverse: base->cur given, convert cur->base
    conv2 = build_fx_converter(
        [{"from_currency": "USD", "to_currency": "CNY", "rate": 7.0}], "USD")
    assert round(conv2(700, "CNY"), 2) == 100.0


def test_fx_unconvertible_returns_none():
    conv = build_fx_converter([], "USD")
    assert conv(100, "JPY") is None


# ── 账户分类 ─────────────────────────────────────────────────────────────

def test_classify_by_account_name_overrides_type():
    policy = {
        "account_classes": {"高端理财": "bond"},
        "account_type_classes": {"investment": "equity", "depository": "cash"},
    }
    assert classify_account({"name": "高端理财", "account_type": "investment"}, policy) == "bond"
    assert classify_account({"name": "其它", "account_type": "investment"}, policy) == "equity"
    assert classify_account({"name": "银行", "account_type": "depository"}, policy) == "cash"
    assert classify_account({"name": "x", "account_type": "unknown"}, policy) == "other"


# ── 端到端 analyze ───────────────────────────────────────────────────────

def _policy():
    return {
        "targets": {"equity": 50, "bond": 30, "cash": 20},
        "limits": {"max_single_security_pct": 15},
        "drift": {"threshold_pct": 5},
        "account_classes": {"理财A": "bond"},
        "account_type_classes": {"depository": "cash", "investment": "equity"},
        "security_classes": {},
    }


def _snapshot():
    # base USD; 一个 USD 股票账户(含 BABA 持仓), 一个 CNY 现金账户, 一个 CNY 理财账户, 一个负债
    return {
        "currency": "USD",
        "total_assets": 2000.0,
        "accounts": [
            {"name": "美股", "account_type": "investment", "classification": "asset",
             "balance": "1000", "currency": "USD"},
            {"name": "现金", "account_type": "depository", "classification": "asset",
             "balance": "700", "currency": "CNY"},   # /7 = 100 USD
            {"name": "理财A", "account_type": "investment", "classification": "asset",
             "balance": "900", "currency": "USD"},
            {"name": "房贷", "account_type": "loan", "classification": "liability",
             "balance": "5000", "currency": "USD"},  # 负债不计入
        ],
        "holdings": [
            {"security": {"ticker": "BABA"}, "market_value": "1000", "currency": "USD"},
        ],
    }


def _rates():
    return [{"from_currency": "USD", "to_currency": "CNY", "rate": 7.0}]


def test_analyze_allocation_and_total():
    r = analyze(_snapshot(), _rates(), _policy())
    # equity(美股1000) + bond(理财A900) + cash(现金700CNY=100USD) = 2000
    assert r["total_assets"] == 2000.0
    alloc = {a["class"]: a for a in r["allocation"]}
    assert alloc["equity"]["actual_pct"] == 50.0   # 1000/2000
    assert alloc["bond"]["actual_pct"] == 45.0     # 900/2000
    assert alloc["cash"]["actual_pct"] == 5.0      # 100/2000


def test_analyze_drift_and_rebalance():
    r = analyze(_snapshot(), _rates(), _policy())
    alloc = {a["class"]: a for a in r["allocation"]}
    # bond 实际45 vs 目标30 → drift +15 → over
    assert alloc["bond"]["status"] == "over"
    # cash 实际5 vs 目标20 → drift -15 → under
    assert alloc["cash"]["status"] == "under"
    # equity 50 vs 50 → ok
    assert alloc["equity"]["status"] == "ok"
    classes_to_rebalance = {x["class"]: x for x in r["rebalance"]}
    assert classes_to_rebalance["cash"]["action"] == "增持"
    assert classes_to_rebalance["bond"]["action"] == "减持"


def test_analyze_concentration_breach():
    r = analyze(_snapshot(), _rates(), _policy())
    conc = {c["ticker"]: c for c in r["concentration"]}
    # BABA 1000/2000 = 50% > 15% 红线
    assert conc["BABA"]["pct"] == 50.0
    assert conc["BABA"]["breach"] is True


def test_analyze_reconciliation_matches_maybe_total():
    r = analyze(_snapshot(), _rates(), _policy())
    assert r["reconciliation"]["diff_pct"] == 0.0  # 自算 2000 == Maybe total_assets 2000


def test_analyze_warns_on_unconvertible_currency():
    snap = _snapshot()
    snap["accounts"].append({"name": "日股", "account_type": "investment",
                             "classification": "asset", "balance": "100", "currency": "JPY"})
    r = analyze(snap, _rates(), _policy())  # no JPY rate
    assert any("JPY" in w for w in r["warnings"])
