#!/usr/bin/env python3
"""
通用财报监控系统
- 从 watchlist.yaml 和 Maybe 持仓构建关注列表
- 用 yfinance 查财报日历，web search 确认发布
- 财报发布后第一时间发送飞书卡片通知
- 状态文件避免重复通知
"""

import argparse
import json
import os
import sys
import subprocess
import time
from datetime import datetime, timedelta, date, timezone
from pathlib import Path

import yaml


# ─── 财报期/季度推算（纯函数，可离线单元测试）───
#
# 这些函数不碰网络，只做日期/季度推算与对账，便于测试。核心目的：
#   1) 不再用「发布日的自然月」瞎猜季度（旧 bug，把美光 FQ3 标成 Q2）；
#   2) 把营收/净利润所属的「财报期」和 EPS 的「发布日」做新鲜度对账，
#      yfinance 基本面没更新时如实标注，而不是把上一季度数字当本季度。


def epoch_to_date(ts):
    """yfinance info 里的 epoch 时间戳 -> date；无法解析返回 None。"""
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def compute_fiscal_quarter(period_end, fye_month):
    """财报期末日 + 财年末月(1-12) -> (财年季度 1-4, 财年)。输入不全返回 None。

    例：美光财年 8 月底结束(fye_month=8)，财报期截至 2026-05-28 ->
        (3, 2026) 即 FQ3-2026（旧代码会错标成 Q2）。
    """
    if not period_end or not fye_month:
        return None
    try:
        m = period_end.month
        fye_month = int(fye_month)
    except (AttributeError, TypeError, ValueError):
        return None
    if not (1 <= fye_month <= 12):
        return None
    offset = (m - fye_month - 1) % 12      # 距财年起始的月偏移
    fq = offset // 3 + 1
    fiscal_year = period_end.year if m <= fye_month else period_end.year + 1
    return fq, fiscal_year


def period_label(period_end, fye_month):
    """生成季度标签。优先 'FQ3-2026（截至 2026-05-28）'；
    财年末月未知时只显示期末日，绝不臆造季度号。"""
    fq = compute_fiscal_quarter(period_end, fye_month)
    if fq:
        return f"FQ{fq[0]}-{fq[1]}（截至 {period_end.isoformat()}）"
    if period_end:
        return f"截至 {period_end.isoformat()}"
    return "财报期未知"


def quarter_key(period_end, earnings_date):
    """去重用的稳定键的一部分：优先财报期末日，否则发布日，否则空。"""
    if period_end:
        return period_end.isoformat()
    if earnings_date:
        return earnings_date.isoformat()
    return ""


def assess_freshness(earnings_date, period_end, max_gap_days=110):
    """对账营收/净利润所属财报期 vs 发布日，判断 yfinance 基本面是否已更新。

    返回 {fresh, gap_days, note}。fresh=False 表示基本面很可能还是上一季度，
    此时营收/净利润不能当作本次财报数字 —— 卡片必须如实标注。
    """
    if not earnings_date or not period_end:
        return {
            "fresh": None, "gap_days": None,
            "note": "财报期或发布日缺失，营收/净利润未二次核实",
        }
    gap = (earnings_date - period_end).days
    if gap < 0:
        return {
            "fresh": None, "gap_days": gap,
            "note": "财报期晚于发布日，数据异常，未核实",
        }
    if gap <= max_gap_days:
        return {
            "fresh": True, "gap_days": gap,
            "note": f"营收/净利润对应财报期 {period_end.isoformat()}，距发布日 {gap} 天，判定为本次财报",
        }
    return {
        "fresh": False, "gap_days": gap,
        "note": (f"⚠️ yfinance 基本面最新期 {period_end.isoformat()} 距发布日 {gap} 天，"
                 f"可能尚未更新——营收/净利润或为上一季度，未确认"),
    }

# ─── 配置 ───

SCRIPT_DIR = Path(__file__).parent.parent  # skill 目录（含模板）
CONFIG_DIR = Path.home() / ".config" / "maybe-finance" / "earnings-monitor"
WATCHLIST_PATH = CONFIG_DIR / "watchlist.yaml"
STATE_PATH = CONFIG_DIR / "earnings_state.json"
WATCHLIST_TEMPLATE = SCRIPT_DIR / "watchlist.example.yaml"
MAYBE_PYTHON = os.environ.get("MAYBE_PYTHON", os.path.expanduser("~/pyenv/maybe/bin/python3"))
# 飞书目标 chat id 不写进源码（属隐私）。运行时按优先级解析：
#   环境变量 FEISHU_TARGET > watchlist.yaml 的 feishu_target 键（均为非版本化的本地配置）
FEISHU_TARGET = os.environ.get("FEISHU_TARGET", "")

QUIET_MODE = False


def log(msg: str):
    if not QUIET_MODE:
        print(msg, file=sys.stderr)


# ─── Watchlist 管理 ───


def load_watchlist() -> dict:
    # 首次运行：从模板创建配置
    if not WATCHLIST_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if WATCHLIST_TEMPLATE.exists():
            import shutil
            shutil.copy2(WATCHLIST_TEMPLATE, WATCHLIST_PATH)
            log(f"📋 首次运行，已从模板创建配置: {WATCHLIST_PATH}")
        else:
            # 没有模板就创建空配置
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            WATCHLIST_PATH.write_text(
                "auto_sync_holdings: true\nextra_tickers: []\nexclude_tickers: []\n",
                encoding="utf-8"
            )
            log(f"📋 首次运行，已创建空配置: {WATCHLIST_PATH}")

    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_watchlist(data: dict):
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def get_maybe_holdings_tickers() -> list[str]:
    """从 Maybe Finance 获取持仓中的股票 ticker"""
    try:
        result = subprocess.run(
            [MAYBE_PYTHON, "-c", """
import json, subprocess, sys
try:
    r = subprocess.run([""" + repr(MAYBE_PYTHON) + """, "-m", "maybe_cli", "holding", "list", "--json"],
                       capture_output=True, text=True, timeout=15)
    data = json.loads(r.stdout) if r.stdout else []
    if isinstance(data, dict):
        data = data.get("holdings", [data])
    tickers = set()
    for h in data:
        t = h.get("ticker") or h.get("security", {}).get("ticker", "")
        if t and t != "CASH":
            tickers.add(t)
    print(json.dumps(sorted(tickers)))
"""],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        log(f"⚠️ 获取 Maybe 持仓失败: {e}")
    return []


def build_ticker_list(watchlist: dict) -> list[dict]:
    """合并 auto-sync 持仓和额外关注，去重，排除"""
    all_tickers = {}  # ticker -> {ticker, name}

    # 1. Maybe 持仓自动同步
    if watchlist.get("auto_sync_holdings", True):
        maybe_tickers = get_maybe_holdings_tickers()
        for t in maybe_tickers:
            if t and t != "CASH":
                all_tickers[t] = {"ticker": t, "name": t}

    # 2. 额外关注
    for item in watchlist.get("extra_tickers", []):
        t = item["ticker"]
        all_tickers[t] = {"ticker": t, "name": item.get("name", t)}

    # 3. 排除
    exclude = set(watchlist.get("exclude_tickers", []))
    for t in exclude:
        all_tickers.pop(t, None)

    return list(all_tickers.values())


# ─── 状态管理 ───


def load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    return {"notified": {}, "last_check": {}}


def save_state(state: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def is_already_notified(state: dict, ticker: str, quarter: str) -> bool:
    key = f"{ticker}:{quarter}"
    return key in state.get("notified", {})


def mark_notified(state: dict, ticker: str, quarter: str, data: dict):
    key = f"{ticker}:{quarter}"
    state.setdefault("notified", {})[key] = {
        "notified_at": datetime.now().isoformat(),
        "earnings_date": data.get("earnings_date", ""),
        "quarter": quarter,
    }


def cleanup_state(state: dict, days: int = 100):
    """清理超过 N 天的通知记录"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    notified = state.get("notified", {})
    state["notified"] = {
        k: v for k, v in notified.items()
        if v.get("notified_at", "") > cutoff
    }


# ─── 财报检查 ───


def check_earnings_calendar(ticker: str) -> dict | None:
    """用 yfinance 检查财报日历，返回最近财报信息或 None"""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)

        # 方法1: earnings_dates (最可靠)
        ed = t.earnings_dates
        if ed is not None and len(ed) > 0:
            today = datetime.now().date()
            # 找最近过去的财报日期（3天内）
            for idx, row in ed.iterrows():
                earnings_date = idx.date() if hasattr(idx, 'date') else idx
                if isinstance(earnings_date, datetime):
                    earnings_date = earnings_date.date()

                days_ago = (today - earnings_date).days
                if 0 <= days_ago <= 3:
                    # 检查是否有 EPS 数据（财报已发布的标志）
                    eps = row.get("Reported EPS", None)
                    eps_est = row.get("EPS Estimate", None)
                    # 不在此处臆造季度标签：真正的财年季度由 run_check 用财报期推算
                    return {
                        "ticker": ticker,
                        "earnings_date": earnings_date.isoformat(),
                        "quarter": None,           # 待 run_check 用财报期回填真实 FQ
                        "eps_reported": eps if eps == eps else None,  # NaN check
                        "eps_estimate": eps_est if eps_est == eps_est else None,
                        "days_ago": days_ago,
                    }

            # 方法2: 查找最近的未来财报日期（预告）
            for idx, row in ed.iterrows():
                earnings_date = idx.date() if hasattr(idx, 'date') else idx
                if isinstance(earnings_date, datetime):
                    earnings_date = earnings_date.date()
                if earnings_date >= today:
                    days_until = (earnings_date - today).days
                    return {
                        "ticker": ticker,
                        "earnings_date": earnings_date.isoformat(),
                        # 预告还没有财报期，标签按预计发布日给出，不臆造季度号
                        "quarter": f"预计 {earnings_date.isoformat()}",
                        "upcoming": True,
                        "days_until": days_until,
                        "eps_reported": None,
                    }
                    break  # 只取最近一个

        return None
    except Exception as e:
        log(f"  ⚠️ {ticker}: yfinance 查询失败: {e}")
        return None


def web_search_earnings(ticker: str, quarter: str) -> dict | None:
    """用 OpenClaw web search 搜索财报详情"""
    try:
        result = subprocess.run(
            ["openclaw", "infer", "web", "search",
             "--query", f"{ticker} {quarter} earnings results revenue EPS",
             "--limit", "5", "--json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        data = json.loads(result.stdout.strip())
        outputs = data.get("outputs", [])
        if not outputs:
            return None

        results = outputs[0].get("result", {}).get("results", [])
        if not results:
            return None

        # 收集搜索结果摘要
        snippets = []
        for r in results[:3]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            url = r.get("url", "")
            if snippet:
                snippets.append(f"[{title}]\n{snippet}\n{url}")

        return {
            "search_snippets": snippets,
            "first_url": results[0].get("url", ""),
        }
    except Exception as e:
        log(f"  ⚠️ {ticker}: web search 失败: {e}")
        return None


def fetch_earnings_details(ticker: str) -> dict:
    """用 yfinance 获取最新财报详情。

    额外返回 `period_end`(date) 和 `fye_month`(int)，供 run_check 推算真实财年季度
    并对账营收/净利润的新鲜度——确保「营收/净利润」与「EPS/发布日」指向同一季度。
    """
    details = {}
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)

        # 季度财报：取最新一列，并记录该列对应的财报期末日
        qf = t.quarterly_financials
        if qf is not None and len(qf) > 0:
            latest = qf.columns[0]
            pe = latest.date() if hasattr(latest, "date") else None
            if pe:
                details["period_end"] = pe
            if "Total Revenue" in qf.index:
                rev = qf.loc["Total Revenue", latest]
                if rev == rev:  # NaN check
                    details["revenue"] = f"${rev/1e9:.2f}B" if rev > 1e9 else f"${rev/1e6:.0f}M"
            if "Net Income" in qf.index:
                ni = qf.loc["Net Income", latest]
                if ni == ni:
                    details["net_income"] = f"${ni/1e9:.2f}B" if ni > 1e9 else f"${ni/1e6:.0f}M"

        # 基本信息
        info = t.info or {}
        # 财年末月：用于把财报期末日换算成真实财年季度（如美光 8 月 -> FQ3）
        fye = epoch_to_date(info.get("lastFiscalYearEnd"))
        if fye:
            details["fye_month"] = fye.month
        if info.get("currentPrice"):
            details["current_price"] = f"${info['currentPrice']:.2f}"  # 修正：键名是 currentPrice
        if info.get("earningsGrowth"):
            details["earnings_growth"] = f"{info['earningsGrowth']*100:.1f}%"
        if info.get("revenueGrowth"):
            details["revenue_growth"] = f"{info['revenueGrowth']*100:.1f}%"

    except Exception as e:
        log(f"  ⚠️ {ticker}: 获取财报详情失败: {e}")

    return details


# ─── 飞书通知 ───


def send_feishu_card(card_json: str) -> bool:
    """通过 OpenClaw 发送飞书卡片"""
    if not FEISHU_TARGET:
        log("  ⚠️ 未配置飞书目标（FEISHU_TARGET 环境变量或 watchlist.yaml 的 feishu_target），跳过发送")
        return False
    try:
        result = subprocess.run(
            ["openclaw", "message", "send",
             "--channel", "feishu",
             "-t", FEISHU_TARGET,
             "-m", "财报通知",
             "--presentation", card_json],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        log(f"  ⚠️ 飞书通知失败: {e}")
        return False


def build_earnings_card(ticker: str, name: str, earnings: dict, details: dict, web: dict | None) -> str:
    """构建飞书卡片 JSON"""
    blocks = []

    # 标题
    blocks.append({"type": "text", "text": f"📊 {name}（{ticker}）{earnings['quarter']} 财报发布"})
    blocks.append({"type": "divider"})

    # 财报日期
    blocks.append({"type": "text", "text": f"📅 财报日期：{earnings['earnings_date']}"})

    # EPS
    if earnings.get("eps_reported") is not None:
        eps_str = f"EPS：${earnings['eps_reported']:.2f}"
        if earnings.get("eps_estimate") is not None:
            eps_str += f"（预期 ${earnings['eps_estimate']:.2f}）"
        blocks.append({"type": "text", "text": eps_str})

    # 财报详情
    fresh = earnings.get("freshness", {})
    stale = fresh.get("fresh") is False  # 营收/净利润可能为上一季度
    rev_suffix = "（⚠️ 可能为上一季度，未确认）" if stale else ""
    detail_lines = []
    if "revenue" in details:
        detail_lines.append(f"💰 营收：{details['revenue']}{rev_suffix}")
    if "net_income" in details:
        detail_lines.append(f"📊 净利润：{details['net_income']}{rev_suffix}")
    if "earnings_growth" in details:
        detail_lines.append(f"📈 盈利增长：{details['earnings_growth']}")
    if "revenue_growth" in details:
        detail_lines.append(f"📈 营收增长：{details['revenue_growth']}")
    if "current_price" in details:
        detail_lines.append(f"💲 当前股价：{details['current_price']}")

    if detail_lines:
        blocks.append({"type": "text", "text": "\n".join(detail_lines)})

    # Web 搜索摘要（二手来源，仅供参考，未与上方数字逐项核对）
    if web and web.get("search_snippets"):
        blocks.append({"type": "divider"})
        blocks.append({"type": "text", "text": "🔍 相关报道（二手来源，未逐项核对）"})
        for snippet in web["search_snippets"][:2]:
            blocks.append({"type": "text", "text": snippet})

    if web and web.get("first_url"):
        blocks.append({"type": "text", "text": f"📎 [查看详情]({web['first_url']})"})

    # 数据来源与可信度（evidence-first：每个数字说清来源 + 是否对账）
    blocks.append({"type": "divider"})
    src = "EPS/预期 来自 yfinance earnings_dates；营收/净利润 来自 yfinance quarterly_financials"
    if fresh.get("note"):
        src += f"。{fresh['note']}"
    blocks.append({"type": "context", "text": f"📌 {src}"})

    blocks.append({"type": "context", "text": "🤖 家庭理财助手 | 自动财报监控"})

    return json.dumps({"blocks": blocks}, ensure_ascii=False)


def build_upcoming_card(ticker: str, name: str, earnings: dict) -> str:
    """构建财报预告卡片"""
    blocks = []
    blocks.append({"type": "text", "text": f"📌 {name}（{ticker}）财报预告"})
    blocks.append({"type": "divider"})
    blocks.append({"type": "text", "text": f"📅 预计日期：{earnings['earnings_date']}"})
    if earnings.get("days_until") is not None:
        blocks.append({"type": "text", "text": f"⏰ 距今还有 {earnings['days_until']} 天"})
    blocks.append({"type": "divider"})
    blocks.append({"type": "context", "text": "🤖 家庭理财助手 | 自动财报监控"})
    return json.dumps({"blocks": blocks}, ensure_ascii=False)


# ─── 主逻辑 ───


def run_check(notify_upcoming: bool = False):
    """执行一次财报检查"""
    watchlist = load_watchlist()
    # 飞书目标：env 优先，否则取 watchlist.yaml 的 feishu_target（本地非版本化配置）
    global FEISHU_TARGET
    if not FEISHU_TARGET:
        FEISHU_TARGET = watchlist.get("feishu_target", "") or ""
    tickers = build_ticker_list(watchlist)
    state = load_state()
    cleanup_state(state)

    log(f"📋 关注列表：{', '.join(t['ticker'] for t in tickers)}（共 {len(tickers)} 只）")

    notifications_sent = 0

    for item in tickers:
        ticker = item["ticker"]
        name = item.get("name", ticker)

        # 检查财报日历
        earnings = check_earnings_calendar(ticker)

        if not earnings:
            log(f"  {ticker}: 无财报信息")
            state["last_check"][ticker] = datetime.now().isoformat()
            continue

        quarter = earnings.get("quarter")

        if earnings.get("upcoming"):
            # 财报即将发布
            days = earnings.get("days_until", 999)
            if notify_upcoming and days <= 3 and not is_already_notified(state, ticker, quarter + "-pre"):
                log(f"  {ticker}: 财报 {days} 天后发布，发送预告")
                card = build_upcoming_card(ticker, name, earnings)
                if send_feishu_card(card):
                    mark_notified(state, ticker, quarter + "-pre", earnings)
                    notifications_sent += 1
            else:
                log(f"  {ticker}: 财报 {days} 天后发布")
        else:
            # 财报已发布：用稳定的发布日做去重键（标签格式变化不会触发重复通知）
            dedup_key = earnings["earnings_date"]
            if is_already_notified(state, ticker, dedup_key):
                log(f"  {ticker}: {dedup_key} 财报已通知过，跳过")
            else:
                log(f"  {ticker}: {dedup_key} 财报已发布！获取详情...")
                details = fetch_earnings_details(ticker)
                # 用财报期 + 财年末月推算真实财年季度，回填标签（不再用发布日瞎猜）
                period_end = details.get("period_end")
                fye_month = details.get("fye_month")
                earnings["quarter"] = period_label(period_end, fye_month)
                # 营收/净利润 与 EPS/发布日 的新鲜度对账
                try:
                    ed_obj = date.fromisoformat(earnings["earnings_date"])
                except (ValueError, TypeError):
                    ed_obj = None
                earnings["freshness"] = assess_freshness(ed_obj, period_end)
                web = web_search_earnings(ticker, earnings["quarter"])
                card = build_earnings_card(ticker, name, earnings, details, web)
                if send_feishu_card(card):
                    mark_notified(state, ticker, dedup_key, earnings)
                    notifications_sent += 1
                    log(f"  ✅ {ticker}: 已发送飞书通知（{earnings['quarter']}）")

        state["last_check"][ticker] = datetime.now().isoformat()

    save_state(state)
    log(f"\n完成：{notifications_sent} 条通知发送")

    return notifications_sent


# ─── Watchlist 命令（供 SKILL.md 调用）───


def cmd_add(ticker: str, name: str = ""):
    """添加关注股票"""
    ticker = ticker.upper()
    watchlist = load_watchlist()
    extras = watchlist.get("extra_tickers", [])

    # 去重检查
    for item in extras:
        if item["ticker"] == ticker:
            print(f"⚠️ {ticker} 已在关注列表中")
            return

    extras.append({
        "ticker": ticker,
        "name": name or ticker,
        "added_at": datetime.now().strftime("%Y-%m-%d")
    })
    watchlist["extra_tickers"] = extras

    # 如果在排除列表中，移除它
    excludes = watchlist.get("exclude_tickers", [])
    if ticker in excludes:
        excludes.remove(ticker)
        watchlist["exclude_tickers"] = excludes
        print(f"✅ 已添加 {ticker}（{name or ticker}）并从排除列表移除")
    else:
        print(f"✅ 已添加 {ticker}（{name or ticker}）到财报关注列表")

    save_watchlist(watchlist)


def cmd_remove(ticker: str):
    """移除关注股票"""
    ticker = ticker.upper()
    watchlist = load_watchlist()

    # 从 extra_tickers 移除
    extras = watchlist.get("extra_tickers", [])
    before = len(extras)
    watchlist["extra_tickers"] = [x for x in extras if x["ticker"] != ticker]

    # 加入排除列表（防止 auto-sync 重新加入）
    excludes = watchlist.get("exclude_tickers", [])
    if ticker not in excludes:
        excludes.append(ticker)
    watchlist["exclude_tickers"] = excludes

    save_watchlist(watchlist)
    removed = before - len(watchlist["extra_tickers"])
    if removed > 0:
        print(f"✅ 已从关注列表移除 {ticker}")
    else:
        print(f"✅ {ticker} 已加入排除列表（不会自动同步）")


def cmd_list():
    """列出所有关注股票"""
    watchlist = load_watchlist()
    tickers = build_ticker_list(watchlist)

    maybe_tickers = set()
    if watchlist.get("auto_sync_holdings", True):
        maybe_tickers = set(get_maybe_holdings_tickers())

    print(f"📋 财报关注列表（共 {len(tickers)} 只）")
    print(f"   Auto-sync 持仓：{'开启' if watchlist.get('auto_sync_holdings') else '关闭'}")
    print()
    for item in tickers:
        t = item["ticker"]
        source = "持仓同步" if t in maybe_tickers else "手动添加"
        print(f"  {t:6s} | {item.get('name', t):20s} | 来源: {source}")

    excludes = watchlist.get("exclude_tickers", [])
    if excludes:
        print(f"\n  排除列表: {', '.join(excludes)}")


# ─── CLI ───


def main():
    parser = argparse.ArgumentParser(description="通用财报监控")
    parser.add_argument("--quiet", action="store_true", help="安静模式")
    parser.add_argument("--notify-upcoming", action="store_true", help="财报预告也通知（3天内）")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="执行一次检查")

    add_p = sub.add_parser("add", help="添加关注股票")
    add_p.add_argument("ticker")
    add_p.add_argument("--name", default="")

    rm_p = sub.add_parser("remove", help="移除关注股票")
    rm_p.add_argument("ticker")

    sub.add_parser("list", help="列出关注列表")

    args = parser.parse_args()

    global QUIET_MODE
    QUIET_MODE = args.quiet

    if args.command == "add":
        cmd_add(args.ticker, args.name)
    elif args.command == "remove":
        cmd_remove(args.ticker)
    elif args.command == "list":
        cmd_list()
    else:
        run_check(notify_upcoming=args.notify_upcoming)


if __name__ == "__main__":
    main()
