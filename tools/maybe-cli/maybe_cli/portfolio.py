"""Portfolio allocation analysis against a target policy.

资产配置分析（仅按资产类别）：读取 Maybe 的 snapshot（账户 + 持仓，原币种）
和汇率，统一换算到基准币种，按资产类别汇总实际配置，对比 policy.yaml 的目标
配置，计算漂移；并按证券计算单一证券集中度（<15% 红线）。

数据来源（佐证）：
- 账户 / 持仓 / 净资产 / 总资产：Maybe Finance（`maybe snapshot --json`）
- 汇率：Maybe Finance（`maybe exchange-rates --json`），其底层来自 Synth/yfinance
- 目标配置与规则：`~/.config/maybe-finance/portfolio/policy.yaml`（用户维护）

本模块只做客观计算，不提供投资建议。
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ASSET_CLASSES = ("equity", "bond", "cash", "commodity", "other")

POLICY_PATH = Path.home() / ".config" / "maybe-finance" / "portfolio" / "policy.yaml"

# policy.yaml 缺省值；用户配置会覆盖这些键。
DEFAULT_POLICY = {
    "targets": {"equity": 60, "bond": 25, "cash": 10, "commodity": 5},
    "limits": {"max_single_security_pct": 15},
    "drift": {"threshold_pct": 5},
    # 账户名 → 资产类别（精确匹配，优先级最高；用于"余额型理财"等账户）
    "account_classes": {},
    # 账户类型 → 资产类别（兜底）
    "account_type_classes": {
        "depository": "cash",
        "investment": "equity",
        "crypto": "commodity",
    },
    # 证券 ticker → 资产类别（默认 equity；债券/商品类在此标注），用于集中度展示与未来细分
    "security_classes": {},
}

# 首次运行写入用户配置目录的模板（含示例 + 说明，用户改成真实数字）。
TEMPLATE_YAML = """\
# 家庭投资组合政策 / Investment policy（仅按资产类别）
# 本文件由用户维护，安装/升级不会覆盖。修改后立即生效。

# 目标配置（百分比，合计应为 100）
targets:
  equity: 60      # 股票
  bond: 25        # 债券 / 固收类理财
  cash: 10        # 现金 / 货币基金
  commodity: 5    # 商品（黄金等）

limits:
  max_single_security_pct: 15   # 单一证券占总组合上限（红线）

drift:
  threshold_pct: 5              # 单类别偏离目标超过该百分点 → 提示再平衡

# 账户名 → 资产类别（精确匹配，优先级最高）。
# 把"余额型理财/固收"等账户在这里标注；不写的投资类账户默认按 equity 处理。
account_classes: {}
  # 示例（改成你的真实账户名）：
  # "某某高端理财": bond
  # "某某货币基金": cash

# 账户类型 → 资产类别（兜底，一般无需改）
account_type_classes:
  depository: cash
  investment: equity
  crypto: commodity

# 证券 ticker → 资产类别（默认 equity；债券/商品 ETF 在此标注）
security_classes: {}
  # 示例：
  # TLT: bond
  # GLD: commodity
"""


def load_policy(path: str | None = None) -> dict:
    """加载 policy.yaml；首次运行从模板写入用户配置目录。返回与缺省合并后的 dict。"""
    cfg_path = Path(path) if path else POLICY_PATH
    if not cfg_path.exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(TEMPLATE_YAML, encoding="utf-8")

    with open(cfg_path, "r", encoding="utf-8") as f:
        user = yaml.safe_load(f) or {}

    # 浅合并：用户提供的键覆盖缺省（dict 子项做一层合并）
    policy = {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_POLICY.items()}
    for k, v in user.items():
        if isinstance(v, dict) and isinstance(policy.get(k), dict):
            merged = policy[k].copy()
            merged.update(v)
            policy[k] = merged
        else:
            policy[k] = v
    return policy


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def build_fx_converter(exchange_rates: list, base: str):
    """返回 convert(amount, currency)->base_amount 或 None（无法换算）。

    exchange_rates: [{"from_currency","to_currency","rate"}, ...]
    """
    direct = {}
    for r in exchange_rates or []:
        fr = (r.get("from_currency") or "").upper()
        to = (r.get("to_currency") or "").upper()
        rate = _num(r.get("rate"))
        if fr and to and rate:
            direct[(fr, to)] = rate

    base = (base or "").upper()

    def convert(amount, currency):
        cur = (currency or "").upper()
        amt = _num(amount)
        if not cur or cur == base:
            return amt
        if (cur, base) in direct:
            return amt * direct[(cur, base)]
        if (base, cur) in direct and direct[(base, cur)]:
            return amt / direct[(base, cur)]
        return None  # 无法换算

    return convert


def classify_account(account: dict, policy: dict) -> str:
    """账户 → 资产类别：账户名精确匹配优先，否则按账户类型兜底，再否则 other。"""
    name = account.get("name", "")
    by_name = policy.get("account_classes", {})
    if name in by_name:
        return by_name[name]
    by_type = policy.get("account_type_classes", {})
    return by_type.get(account.get("account_type", ""), "other")


def analyze(snapshot: dict, exchange_rates: list, policy: dict) -> dict:
    """计算资产配置实际 vs 目标、漂移、单一证券集中度。

    返回结构化结果（含 warnings），不打印、不判断好坏。
    """
    base = (snapshot.get("currency") or "").upper()
    convert = build_fx_converter(exchange_rates, base)
    warnings: list[str] = []

    # 1) 资产账户 → 按资产类别汇总（换算到 base）
    buckets = {c: 0.0 for c in ASSET_CLASSES}
    for acc in snapshot.get("accounts", []):
        if acc.get("classification") != "asset":
            continue  # 负债（贷款等）不计入资产配置
        val = convert(acc.get("balance"), acc.get("currency"))
        if val is None:
            warnings.append(
                f"账户「{acc.get('name')}」币种 {acc.get('currency')} 无法换算到 {base}，已跳过"
            )
            continue
        cls = classify_account(acc, policy)
        if cls not in buckets:
            buckets[cls] = 0.0
        buckets[cls] += val

    total = sum(buckets.values())

    # 未分类资产占比偏高时提醒用户在 policy.yaml 里映射账户
    if total and buckets.get("other", 0) / total * 100 > 5:
        warnings.append(
            f"{buckets['other'] / total * 100:.0f}% 资产归类为 other（未映射），"
            f"请在 policy.yaml 的 account_classes 里把这些账户映射到正确类别"
        )

    # 2) 实际 vs 目标 vs 漂移
    targets = policy.get("targets", {})
    threshold = _num(policy.get("drift", {}).get("threshold_pct", 5))
    allocation = []
    rebalance = []
    for cls in sorted(buckets, key=lambda c: (-buckets[c], c)):
        value = buckets[cls]
        if value == 0 and cls not in targets:
            continue
        actual_pct = (value / total * 100) if total else 0.0
        target_pct = _num(targets.get(cls))
        drift = actual_pct - target_pct
        status = "ok"
        if cls in targets and abs(drift) >= threshold:
            status = "over" if drift > 0 else "under"
        allocation.append({
            "class": cls, "value": round(value, 2),
            "actual_pct": round(actual_pct, 2), "target_pct": target_pct,
            "drift_pct": round(drift, 2), "status": status,
        })
        if status != "ok":
            amount = (target_pct - actual_pct) / 100 * total
            rebalance.append({
                "class": cls,
                "action": "增持" if amount > 0 else "减持",
                "amount": round(abs(amount), 2),
                "currency": base,
            })

    # 3) 单一证券集中度（红线）
    max_single = _num(policy.get("limits", {}).get("max_single_security_pct", 15))
    concentration = []
    by_security: dict[str, dict] = {}
    for h in snapshot.get("holdings", []):
        sec = h.get("security", {})
        ticker = sec.get("ticker") or h.get("ticker") or "?"
        mv = convert(h.get("market_value"), h.get("currency"))
        if mv is None:
            warnings.append(f"持仓 {ticker} 币种无法换算，集中度已跳过")
            continue
        entry = by_security.setdefault(ticker, {"ticker": ticker, "value": 0.0})
        entry["value"] += mv
    for ticker, e in by_security.items():
        pct = (e["value"] / total * 100) if total else 0.0
        concentration.append({
            "ticker": ticker, "value": round(e["value"], 2),
            "pct": round(pct, 2), "limit_pct": max_single,
            "breach": pct > max_single,
        })
    concentration.sort(key=lambda x: -x["pct"])

    # 4) 与 Maybe total_assets 一致性校验（佐证换算无大偏差）
    maybe_total = _num(snapshot.get("total_assets"))
    reconciliation = None
    if maybe_total:
        diff_pct = abs(total - maybe_total) / maybe_total * 100
        reconciliation = {
            "computed_assets": round(total, 2),
            "maybe_total_assets": round(maybe_total, 2),
            "diff_pct": round(diff_pct, 2),
        }
        if diff_pct > 2:
            warnings.append(
                f"自算总资产与 Maybe total_assets 差 {diff_pct:.1f}%（可能汇率缺失或分类遗漏）"
            )

    return {
        "base_currency": base,
        "total_assets": round(total, 2),
        "allocation": allocation,
        "rebalance": rebalance,
        "concentration": concentration,
        "reconciliation": reconciliation,
        "warnings": warnings,
    }
