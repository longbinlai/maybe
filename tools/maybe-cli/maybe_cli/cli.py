"""maybe-cli: command-line interface for Maybe Finance."""
import json
import os
import sys
from pathlib import Path

import click

from .client import MaybeClient


def _float(val):
    """Safely convert any value to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _fmt_num(val, decimals=2):
    """Format a number with comma separators."""
    return f"{_float(val):,.{decimals}f}"

# ── Shared options ──────────────────────────────────────────────────────

_api_key_opt = click.option("--api-key", envvar="MAYBE_API_KEY", help="Maybe API key")
_url_opt = click.option("--url", envvar="MAYBE_URL", default="http://localhost:3000", help="Maybe base URL")
_json_opt = click.option("--json", "as_json", is_flag=True, help="Output raw JSON")


def _client(api_key, url):
    return MaybeClient(base_url=url, api_key=api_key)


def _output(data: dict, as_json: bool):
    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        click.echo(json.dumps(data, indent=2, default=str))


def _today_str() -> str:
    """Today's date as YYYY-MM-DD (local)."""
    from datetime import date
    return date.today().isoformat()


def _confirm_or_abort(message: str, yes: bool, as_json: bool, error_key: str):
    """Block a risky write unless explicitly confirmed.

    - `--yes/-y` 已给：直接放行。
    - 非交互（--json 或非 TTY）：拒绝并退出，要求显式 --yes，绝不静默执行。
    - 交互终端：打印警告并要求人工确认。
    """
    if yes:
        return
    if as_json or not sys.stdin.isatty():
        payload = {
            "error": error_key,
            "message": message,
            "hint": "re-run with --yes / -y to confirm",
        }
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False), err=not as_json)
        sys.exit(1)
    click.echo(f"⚠️  {message}", err=True)
    if not click.confirm("Proceed anyway?"):
        click.echo("Aborted.", err=True)
        sys.exit(1)


# ── Write-path safety: audit log, dry-run, decision capture ──────────────

AUDIT_PATH = Path.home() / ".config" / "maybe-finance" / "audit" / "writes.jsonl"


def _audit(command: str, action: str, *, account=None, details=None,
           result=None, status="ok"):
    """Append one JSON line per write to an append-only audit log.

    Records who/when/what so silent or wrong writes are traceable later.
    Never raises — auditing must not break a financial write.
    """
    try:
        from datetime import datetime
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
            "command": command,
            "action": action,
            "status": status,
            "account": account,
            "details": details or {},
            "result": result or {},
        }
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def _dry_run_preview(command: str, details: dict, as_json: bool):
    """Print the intended write without performing it."""
    if as_json:
        click.echo(json.dumps(
            {"dry_run": True, "command": command, "would_write": details},
            indent=2, ensure_ascii=False, default=str))
    else:
        click.echo("🌵 DRY RUN — no write performed")
        click.echo(f"   Command: {command}")
        for k, v in details.items():
            click.echo(f"   {k}: {v}")


def _capture_decision(reason, confidence, *, action, account=None, ticker=None,
                      amount=None, date=None):
    """Best-effort: record the WHY of an investment decision into Mem0.

    Content = the subjective reason; objective links go in metadata (per the
    golden rule, objective numbers live in Maybe, not Mem0). Never fails the
    financial write — memory capture is strictly secondary.
    """
    if not reason:
        return
    import shutil
    import subprocess
    memory_bin = shutil.which("memory") or os.path.expanduser("~/pyenv/maybe/bin/memory")
    if not (shutil.which("memory") or os.path.exists(memory_bin)):
        click.echo("⚠️  'memory' CLI not found; decision reason not recorded to Mem0", err=True)
        return
    meta = [f"action={action}"]
    if account:
        meta.append(f"account={account}")
    if ticker:
        meta.append(f"ticker={ticker}")
    if amount is not None:
        meta.append(f"amount={amount}")
    if date:
        meta.append(f"date={date}")
    if confidence is not None:
        meta.append(f"confidence={confidence}")
    cmd = [memory_bin, "add", "-c", "investment_decision", "--content", reason]
    for m in meta:
        cmd += ["-m", m]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            click.echo("🧠 Decision reason recorded to Mem0 (investment_decision)")
        else:
            click.echo(f"⚠️  Memory capture failed (write still succeeded): "
                       f"{r.stderr.strip()[:200]}", err=True)
    except Exception as e:
        click.echo(f"⚠️  Memory capture error (write still succeeded): {e}", err=True)


# ── CLI group ───────────────────────────────────────────────────────────

@click.group()
@click.version_option()
def main():
    """Maybe Finance CLI — family investment data at your fingertips."""
    pass


# ── balance-sheet ───────────────────────────────────────────────────────

@main.command("balance-sheet")
@_api_key_opt
@_url_opt
@_json_opt
@click.option("--start-date", default=None, help="Period start (YYYY-MM-DD)")
@click.option("--end-date", default=None, help="Period end (YYYY-MM-DD)")
def balance_sheet(api_key, url, as_json, start_date, end_date):
    """Net worth, assets, liabilities."""
    c = _client(api_key, url)
    data = c.balance_sheet(start_date=start_date, end_date=end_date)
    if not as_json:
        nw = data.get("net_worth", {})
        a = data.get("assets", {})
        li = data.get("liabilities", {})
        click.echo(f"Net Worth:  {nw.get('current_formatted', '?')}")
        click.echo(f"Assets:     {a.get('current_formatted', '?')}")
        click.echo(f"Liabilities:{li.get('current_formatted', '?')}")
        click.echo()
        click.echo("Assets by type:")
        for t in a.get("by_type", []):
            click.echo(f"  {t['name']:20s}  {_float(t['weight']):>5.1f}%")
        click.echo()
        click.echo("Liabilities by type:")
        for t in li.get("by_type", []):
            click.echo(f"  {t['name']:20s}  {_float(t['weight']):>5.1f}%")
    else:
        _output(data, True)


# ── accounts ────────────────────────────────────────────────────────────

@main.command("accounts")
@_api_key_opt
@_url_opt
@_json_opt
def accounts(api_key, url, as_json):
    """List all accounts."""
    c = _client(api_key, url)
    data = c.accounts()
    if not as_json:
        accs = data.get("accounts", [])
        if not accs:
            click.echo("No accounts found.")
            return
        header = f"{'Name':25s} {'Type':15s} {'Class':10s} {'Balance':>15s} {'Status':10s}"
        click.echo(header)
        click.echo("-" * len(header))
        for a in accs:
            click.echo(
                f"{a['name']:25s} {a['account_type']:15s} {a['classification']:10s} "
                f"{a['balance_formatted']:>15s} {a.get('status', '?'):10s}"
            )
    else:
        _output(data, True)


# ── holdings ────────────────────────────────────────────────────────────

@main.command("holdings")
@_api_key_opt
@_url_opt
@_json_opt
@click.option("--account-id", default=None, help="Filter by account UUID")
def holdings(api_key, url, as_json, account_id):
    """Current investment holdings across all accounts."""
    c = _client(api_key, url)
    data = c.holdings(account_id=account_id)
    if not as_json:
        total = _float(data.get("total_portfolio_value", 0))
        click.echo(f"Portfolio value: {_fmt_num(total)} {data.get('currency', '')}")
        click.echo()
        hs = data.get("holdings", [])
        if not hs:
            click.echo("No holdings found. Add trades in Maybe first.")
            return
        header = f"{'Ticker':10s} {'Name':25s} {'Account':15s} {'Qty':>10s} {'Value':>12s} {'Weight':>8s}"
        click.echo(header)
        click.echo("-" * len(header))
        for h in hs:
            click.echo(
                f"{h['security']['ticker']:10s} {(h['security']['name'] or ''):25s} "
                f"{h['account_name']:15s} {_float(h['quantity']):>10.2f} {_fmt_num(h['market_value']):>12s} "
                f"{_float(h['weight']):>7.1f}%"
            )
    else:
        _output(data, True)


# ── trades ──────────────────────────────────────────────────────────────

@main.command("trades")
@_api_key_opt
@_url_opt
@_json_opt
@click.option("--account-id", default=None, help="Filter by account UUID")
@click.option("--security-id", default=None, help="Filter by security UUID")
@click.option("--start-date", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", default=None, help="End date (YYYY-MM-DD)")
@click.option("--type", "trade_type", default=None, help="buy or sell")
def trades(api_key, url, as_json, account_id, security_id, start_date, end_date, trade_type):
    """Buy/sell trade history."""
    c = _client(api_key, url)
    data = c.trades(account_id=account_id, security_id=security_id,
                    start_date=start_date, end_date=end_date, trade_type=trade_type)
    if not as_json:
        ts = data.get("trades", [])
        if not ts:
            click.echo("No trades found.")
            return
        header = f"{'Date':12s} {'Ticker':10s} {'Type':6s} {'Qty':>10s} {'Price':>10s} {'Amount':>12s} {'Account':20s}"
        click.echo(header)
        click.echo("-" * len(header))
        for t in ts:
            click.echo(
                f"{t['date']:12s} {t['security']['ticker']:10s} {t['type']:6s} "
                f"{_float(t['quantity']):>10.4f} {_float(t['price']):>10.2f} {_fmt_num(t['amount']):>12s} "
                f"{t['account']['name']:20s}"
            )
    else:
        _output(data, True)


# ── securities ──────────────────────────────────────────────────────────

@main.command("securities")
@_api_key_opt
@_url_opt
@_json_opt
@click.option("--search", default=None, help="Search by ticker or name")
def securities(api_key, url, as_json, search):
    """List securities (those you hold or traded)."""
    c = _client(api_key, url)
    data = c.securities(search=search)
    if not as_json:
        secs = data.get("securities", [])
        if not secs:
            click.echo("No securities found.")
            return
        header = f"{'Ticker':10s} {'Name':30s} {'Price':>12s} {'Currency':8s}"
        click.echo(header)
        click.echo("-" * len(header))
        for s in secs:
            price = _float(s.get("current_price"))
            cur = s.get("current_price_currency") or ""
            click.echo(f"{s['ticker']:10s} {(s['name'] or ''):30s} {price:>12.2f} {cur:8s}")
    else:
        _output(data, True)


# ── income-statement ────────────────────────────────────────────────────

@main.command("income-statement")
@_api_key_opt
@_url_opt
@_json_opt
@click.option("--start-date", default=None, help="Period start (YYYY-MM-DD)")
@click.option("--end-date", default=None, help="Period end (YYYY-MM-DD)")
def income_statement(api_key, url, as_json, start_date, end_date):
    """Income and expense summary by category."""
    c = _client(api_key, url)
    data = c.income_statement(start_date=start_date, end_date=end_date)
    if not as_json:
        summary = data.get("summary", {})
        click.echo(f"Period: {data.get('period', {}).get('start_date', '?')} to {data.get('period', {}).get('end_date', '?')}")
        click.echo(f"Income:       {_fmt_num(summary.get('total_income', 0)):>15s}")
        click.echo(f"Expenses:     {_fmt_num(summary.get('total_expense', 0)):>15s}")
        click.echo(f"Net Savings:  {_fmt_num(summary.get('net_savings', 0)):>15s}")
        click.echo(f"Savings Rate: {_float(summary.get('savings_rate', 0)):>14.1f}%")
        click.echo()
        exp_cats = data.get("expense_by_category", {})
        if exp_cats:
            click.echo("Expenses by category:")
            for cat_id, cat in exp_cats.items():
                click.echo(f"  {cat['name']:25s}  {_fmt_num(cat['total']):>12s}  ({_float(cat['weight']):.1f}%)")
        inc_cats = data.get("income_by_category", {})
        if inc_cats:
            click.echo()
            click.echo("Income by category:")
            for cat_id, cat in inc_cats.items():
                click.echo(f"  {cat['name']:25s}  {_fmt_num(cat['total']):>12s}  ({_float(cat['weight']):.1f}%)")
    else:
        _output(data, True)


# ── exchange-rates ──────────────────────────────────────────────────────

@main.command("exchange-rates")
@_api_key_opt
@_url_opt
@_json_opt
@click.option("--from", "from_currency", default=None, help="From currency (e.g. USD)")
@click.option("--to", "to_currency", default=None, help="To currency (e.g. CNY)")
def exchange_rates(api_key, url, as_json, from_currency, to_currency):
    """Currency exchange rates."""
    c = _client(api_key, url)
    data = c.exchange_rates(from_currency=from_currency, to_currency=to_currency)
    if not as_json:
        rates = data.get("exchange_rates", [])
        if not rates:
            click.echo("No exchange rates found.")
            return
        header = f"{'From':6s} {'To':6s} {'Rate':>12s} {'Date':12s}"
        click.echo(header)
        click.echo("-" * len(header))
        for r in rates:
            click.echo(f"{r['from_currency']:6s} {r['to_currency']:6s} {_float(r['rate']):>12.4f} {r['date']:12s}")
    else:
        _output(data, True)


# ── snapshot (combined overview for agent use) ──────────────────────────

@main.command("snapshot")
@_api_key_opt
@_url_opt
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def snapshot(api_key, url, as_json):
    """Full family financial snapshot — balance sheet + accounts + holdings summary.

    This is the primary command for OpenClaw to get a complete picture.
    """
    c = _client(api_key, url)
    bs = c.balance_sheet()
    accs = c.accounts()
    hs = c.holdings()

    result = {
        "as_of_date": bs.get("as_of_date"),
        "currency": bs.get("currency"),
        "net_worth": bs.get("net_worth", {}).get("current"),
        "net_worth_formatted": bs.get("net_worth", {}).get("current_formatted"),
        "total_assets": bs.get("assets", {}).get("current"),
        "total_liabilities": bs.get("liabilities", {}).get("current"),
        "accounts": accs.get("accounts", []),
        "portfolio_value": hs.get("total_portfolio_value", 0),
        "holdings_count": len(hs.get("holdings", [])),
        "holdings": [
            {
                "ticker": h["security"]["ticker"],
                "name": h["security"]["name"],
                "account": h["account_name"],
                "quantity": h["quantity"],
                "market_value": h["market_value"],
                "weight": h["weight"],
            }
            for h in hs.get("holdings", [])
        ],
    }

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        click.echo(f"=== Family Financial Snapshot ({result['as_of_date']}) ===")
        click.echo()
        click.echo(f"Net Worth:     {result['net_worth_formatted']}")
        click.echo(f"Total Assets:  {_fmt_num(result['total_assets'])}")
        click.echo(f"Liabilities:   {_fmt_num(result['total_liabilities'])}")
        click.echo()
        click.echo(f"Accounts: {len(result['accounts'])}")
        for a in result["accounts"]:
            click.echo(f"  {a['name']:25s} {a['account_type']:15s} {a['balance_formatted']:>15s}")
        click.echo()
        click.echo(f"Portfolio: {_fmt_num(result['portfolio_value'])} ({result['holdings_count']} holdings)")
        for h in result["holdings"]:
            click.echo(f"  {h['ticker']:10s} {h['account']:15s} {_fmt_num(h['market_value']):>12s}  {_float(h['weight']):.1f}%")


# ── reconcile ───────────────────────────────────────────────────────────

@main.command("reconcile")
@_api_key_opt
@_url_opt
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
@click.option("--account", "account_name", required=True, help="Account name (fuzzy match)")
@click.option("--balance", required=True, type=float, help="New balance amount")
@click.option("--date", default=None, help="Valuation date (YYYY-MM-DD, defaults to today)")
@click.option("--yes", "-y", is_flag=True,
              help="Skip safety confirmation (same-date transaction conflict)")
@click.option("--dry-run", is_flag=True, help="Preview the write without performing it")
def reconcile(api_key, url, as_json, account_name, balance, date, yes, dry_run):
    """Quick reconciliation — update an account's balance.

    This is the primary command for periodic balance updates.
    Just tell Maybe what the current balance is, and it recalculates everything.

    Example:
        maybe reconcile --account <account_name> --balance 12500
        maybe reconcile --account <account_name> --balance 8500 --date 2026-05-20
    """
    c = _client(api_key, url)

    # Find account by fuzzy name match
    accs = c.accounts().get("accounts", [])
    match = _find_account(accs, account_name)
    if not match:
        click.echo(f"Error: No account matching '{account_name}'", err=True)
        click.echo("Available accounts:", err=True)
        for a in accs:
            click.echo(f"  {a['name']} ({a['account_type']}, {a['balance_formatted']})", err=True)
        c.close()
        raise SystemExit(1)

    # Guard: 同一天不要既有 Transaction 又新建 Valuation，会破坏余额历史。
    guard_date = date or _today_str()
    try:
        same_day = c.transactions(
            account_id=match["id"], start_date=guard_date, end_date=guard_date
        ).get("transactions", [])
        if same_day:
            _confirm_or_abort(
                f"Account '{match['name']}' already has {len(same_day)} transaction(s) on "
                f"{guard_date}. Adding a balance valuation on the same date corrupts balance "
                f"history — use a different date or remove those transactions first.",
                yes, as_json, "valuation_transaction_same_date",
            )
    except SystemExit:
        c.close()
        raise
    except Exception as e:
        click.echo(f"⚠️  Could not verify same-date transactions: {e}", err=True)

    old_balance = _float(match["balance"])
    delta = balance - old_balance

    details = {"account": match["name"], "old_balance": old_balance,
               "new_balance": balance, "delta": delta, "date": guard_date}
    if dry_run:
        _dry_run_preview("reconcile", details, as_json)
        c.close()
        return

    if not as_json:
        click.echo(f"Account:  {match['name']} ({match['account_type']})")
        click.echo(f"Old:      {match['balance_formatted']}")
        click.echo(f"New:      {_fmt_num(balance)} {match['currency']}")
        direction = "↑" if delta >= 0 else "↓"
        click.echo(f"Change:   {direction} {_fmt_num(abs(delta))}")
        click.echo()

    try:
        result = c.reconcile(match["id"], balance, date=date)
        _audit("reconcile", "reconcile", account=match["name"], details=details,
               result={"id": result.get("id") if isinstance(result, dict) else None})
    except Exception as e:
        _audit("reconcile", "reconcile", account=match["name"], details=details,
               status="error", result={"error": str(e)})
        click.echo(f"Error: {e}", err=True)
        c.close()
        raise SystemExit(1)
    c.close()

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        click.echo(f"✅ Reconciled. Account balance updated.")


# ── reconcile-all ───────────────────────────────────────────────────────

@main.command("reconcile-all")
@_api_key_opt
@_url_opt
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def reconcile_all(api_key, url, as_json):
    """Interactive batch reconciliation — update all accounts one by one.

    Shows each account with its current balance, prompts for the new balance.
    Press Enter to keep the current balance, type a number to update.

    Example:
        maybe reconcile-all
    """
    c = _client(api_key, url)
    accs = c.accounts().get("accounts", [])

    if not as_json:
        click.echo("=== Batch Reconciliation ===")
        click.echo("Enter new balance or press Enter to keep current.\n")

    results = []
    for a in accs:
        current = _float(a["balance"])
        prompt = f"  {a['name']:25s} [{a['balance_formatted']:>15s}] → "

        if as_json:
            # Non-interactive: skip
            results.append({"account": a["name"], "action": "skipped", "balance": current})
            continue

        answer = click.prompt(prompt, default="", show_default=False, type=str)
        if answer.strip() == "":
            results.append({"account": a["name"], "action": "skipped", "balance": current})
            continue

        try:
            new_balance = float(answer.replace(",", ""))
        except ValueError:
            click.echo(f"    ⚠ Invalid number, skipping.", err=True)
            results.append({"account": a["name"], "action": "skipped", "balance": current})
            continue

        result = c.reconcile(a["id"], new_balance)
        delta = new_balance - current
        direction = "↑" if delta >= 0 else "↓"
        click.echo(f"    ✅ {_fmt_num(current)} → {_fmt_num(new_balance)} ({direction} {_fmt_num(abs(delta))})")
        results.append({
            "account": a["name"],
            "action": "updated",
            "old_balance": current,
            "new_balance": new_balance,
            "delta": delta
        })

    c.close()

    if as_json:
        click.echo(json.dumps({"results": results}, indent=2, default=str))
    else:
        updated = sum(1 for r in results if r["action"] == "updated")
        click.echo(f"\nDone. {updated}/{len(accs)} accounts updated.")


# ── add-transaction ─────────────────────────────────────────────────────

@main.command("add-transaction")
@_api_key_opt
@_url_opt
@_json_opt
@click.option("--account", "-a", required=True, help="Account name (fuzzy match)")
@click.option("--date", "-d", required=True, help="Transaction date (YYYY-MM-DD)")
@click.option("--amount", "-m", required=True, type=float, help="Transaction amount")
@click.option("--name", "-n", required=True, help="Transaction name/title")
@click.option("--description", help="Optional description")
@click.option("--notes", help="Optional notes")
@click.option("--currency", help="Currency (defaults to account currency)")
@click.option("--category", help="Category name (fuzzy match)")
@click.option("--merchant", help="Merchant name (fuzzy match)")
@click.option("--tag", "tags", multiple=True, help="Tag name(s) (can specify multiple)")
@click.option("--nature", type=click.Choice(["income", "expense", "inflow", "outflow"]),
              help="Transaction nature (income/expense)")
@click.option("--yes", "-y", is_flag=True,
              help="Skip safety confirmations (cross-currency / same-date valuation)")
@click.option("--dry-run", is_flag=True, help="Preview the write without performing it")
@click.option("--reason", default=None,
              help="Why this entry — recorded to Mem0 as an investment_decision")
@click.option("--confidence", type=int, default=None,
              help="Confidence 1-10 (stored with the decision reason)")
def add_transaction(api_key, url, as_json, account, date, amount, name,
                   description, notes, currency, category, merchant, tags, nature,
                   yes, dry_run, reason, confidence):
    """Add a new transaction with optional tags."""
    c = _client(api_key, url)

    # 1. Fuzzy match account
    accs = c.accounts().get("accounts", [])
    matched_acc = _fuzzy_match(account, accs, key="name")
    if not matched_acc:
        if as_json:
            _output({"error": "account_not_found", "available": [a["name"] for a in accs]}, True)
        else:
            click.echo(f"❌ Account not found: {account}")
            click.echo(f"   Available: {', '.join(a['name'] for a in accs[:10])}")
        sys.exit(1)

    acct_currency = matched_acc.get("currency")

    # Default currency to the account's currency
    if not currency:
        currency = acct_currency
        if currency:
            click.echo(f"   Using account currency: {currency}", err=True)
    elif acct_currency and currency.strip().upper() != acct_currency.strip().upper():
        # 跨币种：金额会按汇率换算入账，写错币种会让资产记录严重失真。必须显式确认。
        _confirm_or_abort(
            f"Currency mismatch: transaction is {currency.upper()} but account "
            f"'{matched_acc['name']}' is {acct_currency.upper()}. "
            f"Amount {_fmt_num(amount)} {currency.upper()} will be converted via exchange rate.",
            yes, as_json, "currency_mismatch",
        )

    # Guard: 同一天不要既有 Valuation(余额对账) 又有 Transaction，会破坏余额历史。
    try:
        existing_vals = c.valuations(matched_acc["id"]).get("valuations", [])
        if any(v.get("date") == date for v in existing_vals):
            _confirm_or_abort(
                f"Account '{matched_acc['name']}' already has a balance valuation on {date}. "
                f"Mixing a transaction with a valuation on the same date corrupts balance "
                f"history — remove the valuation first or use a different date.",
                yes, as_json, "valuation_transaction_same_date",
            )
    except SystemExit:
        c.close()
        raise
    except Exception as e:
        # 防护查询失败不应阻断正常写入，仅告警（best-effort）
        click.echo(f"⚠️  Could not verify same-date valuation: {e}", err=True)

    # 2. Fuzzy match category (if provided)
    category_id = None
    if category:
        cats = c.categories().get("categories", [])
        matched_cat = _fuzzy_match(category, cats, key="name")
        if matched_cat:
            category_id = matched_cat["id"]
        else:
            click.echo(f"⚠️  Category not found: {category}, skipping", err=True)
    
    # 3. Fuzzy match merchant (if provided)
    merchant_id = None
    if merchant:
        # Maybe doesn't have a merchants endpoint in CLI, skip for now
        click.echo(f"⚠️  Merchant matching not yet implemented, skipping", err=True)
    
    # 4. Fuzzy match tags (if provided)
    tag_ids = []
    if tags:
        all_tags = c.tags().get("tags", [])
        for tag_name in tags:
            matched_tag = _fuzzy_match(tag_name, all_tags, key="name")
            if matched_tag:
                tag_ids.append(matched_tag["id"])
            else:
                click.echo(f"⚠️  Tag not found: {tag_name}, skipping", err=True)
    
    # 5. Create transaction
    details = {"account": matched_acc["name"], "date": date, "amount": amount,
               "currency": currency, "name": name, "nature": nature}
    if dry_run:
        _dry_run_preview("add-transaction", details, as_json)
        c.close()
        return

    try:
        result = c.create_transaction(
            account_id=matched_acc["id"],
            date=date,
            amount=amount,
            name=name,
            description=description,
            notes=notes,
            currency=currency,
            category_id=category_id,
            merchant_id=merchant_id,
            tag_ids=tag_ids if tag_ids else None,
            nature=nature
        )
        _audit("add-transaction", "create_transaction", account=matched_acc["name"],
               details=details, result={"id": result.get("id") if isinstance(result, dict) else None})

        if as_json:
            _output(result, True)
        else:
            click.echo(f"✅ Transaction created:")
            click.echo(f"   Account: {matched_acc['name']}")
            click.echo(f"   Date: {date}")
            click.echo(f"   Amount: {_fmt_num(amount)}")
            click.echo(f"   Name: {name}")
            if category_id:
                click.echo(f"   Category: {category}")
            if tag_ids:
                tag_names = [t["name"] for t in all_tags if t["id"] in tag_ids]
                click.echo(f"   Tags: {', '.join(tag_names)}")
            if nature:
                click.echo(f"   Nature: {nature}")
    except Exception as e:
        _audit("add-transaction", "create_transaction", account=matched_acc["name"],
               details=details, status="error", result={"error": str(e)})
        if as_json:
            _output({"error": str(e)}, True)
        else:
            click.echo(f"❌ Failed to create transaction: {e}", err=True)
        sys.exit(1)
    finally:
        c.close()

    # Best-effort: record the WHY into Mem0 (after the financial write succeeds)
    _capture_decision(reason, confidence, action="transaction",
                      account=matched_acc["name"], amount=amount, date=date)


# ── categories ──────────────────────────────────────────────────────────

@main.command("categories")
@_api_key_opt
@_url_opt
@_json_opt
def categories(api_key, url, as_json):
    """List transaction categories."""
    c = _client(api_key, url)
    data = c.categories()
    if not as_json:
        cats = data.get("categories", [])
        if not cats:
            click.echo("No categories found.")
        else:
            for cat in cats:
                parent = f" (parent: {cat.get('parent_id', '')})" if cat.get("parent_id") else ""
                click.echo(f"  {cat['name']:25s} {cat.get('classification', ''):10s}{parent}")
    else:
        _output(data, True)


# ── tags ────────────────────────────────────────────────────────────────

@main.command("tags")
@_api_key_opt
@_url_opt
@_json_opt
def tags(api_key, url, as_json):
    """List tags."""
    c = _client(api_key, url)
    data = c.tags()
    if not as_json:
        ts = data.get("tags", [])
        if not ts:
            click.echo("No tags found.")
        else:
            for t in ts:
                click.echo(f"  {t['name']:25s} {t.get('color', '')}")
    else:
        _output(data, True)


# ── helpers ─────────────────────────────────────────────────────────────

def _fuzzy_match(query: str, items: list[dict], key: str) -> dict | None:
    """Fuzzy match by name (case-insensitive, substring)."""
    query_lower = query.lower()
    # Exact match first
    for item in items:
        if item.get(key, "").lower() == query_lower:
            return item
    # Substring match
    for item in items:
        if query_lower in item.get(key, "").lower():
            return item
    # Prefix match
    for item in items:
        if item.get(key, "").lower().startswith(query_lower):
            return item
    return None


def _find_account(accounts: list[dict], query: str) -> dict | None:
    """Fuzzy match account by name (case-insensitive, substring)."""
    return _fuzzy_match(query, accounts, key="name")


# ── Holding management group ────────────────────────────────────────────

@main.group("holding")
def holding_group():
    """Manage investment holdings (add, update, delete, sync prices)."""
    pass


@holding_group.command("add")
@_api_key_opt
@_url_opt
@click.option("--account", "account_name", required=True, help="Account name (fuzzy match)")
@click.option("--ticker", required=True, help="Security ticker (e.g. AAPL, 9988.HK)")
@click.option("--qty", required=True, type=float, help="Number of shares to buy")
@click.option("--price", type=float, default=None, help="Price per share (auto-fetched if omitted)")
@click.option("--avg-cost", type=float, default=None, help="Average cost basis per share")
@click.option("--date", default=None, help="Holding date (YYYY-MM-DD)")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
@click.option("--dry-run", is_flag=True, help="Preview the write without performing it")
@click.option("--reason", default=None,
              help="Why this buy — recorded to Mem0 as an investment_decision")
@click.option("--confidence", type=int, default=None, help="Confidence 1-10")
def holding_add(api_key, url, account_name, ticker, qty, price, avg_cost, date, as_json,
                dry_run, reason, confidence):
    """Buy shares in an investment account.

    Cash decreases by (qty × price), total balance stays the same.
    If the ticker already exists in the account, it updates the position.

    Example:
        maybe holding add --account <account_name> --ticker AAPL --qty 100 --price 150
        maybe holding add --account <account_name> --ticker 7203.T --qty 200
    """
    c = _client(api_key, url)
    accs = c.accounts().get("accounts", [])
    match = _find_account(accs, account_name)
    if not match:
        click.echo(f"Error: No account matching '{account_name}'", err=True)
        c.close()
        raise SystemExit(1)

    details = {"account": match["name"], "ticker": ticker, "qty": qty,
               "price": price, "avg_cost": avg_cost, "date": date}
    if dry_run:
        _dry_run_preview("holding add", details, as_json)
        c.close()
        return

    try:
        result = c.create_holding(
            account_id=match["id"], ticker=ticker, qty=qty,
            price=price, avg_cost=avg_cost, date=date
        )
        _audit("holding add", "create_holding", account=match["name"], details=details,
               result={"action": result.get("action") if isinstance(result, dict) else None})
        c.close()
    except Exception as e:
        _audit("holding add", "create_holding", account=match["name"], details=details,
               status="error", result={"error": str(e)})
        click.echo(f"Error: {e}", err=True)
        c.close()
        raise SystemExit(1)

    _capture_decision(reason, confidence, action="buy", account=match["name"],
                      ticker=ticker, amount=qty, date=date)

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        h = result.get("holding", {})
        sec = h.get("security", {})
        acct = result.get("account", {})
        action = result.get("action", "bought")

        if action == "updated":
            click.echo(f"✅ Updated position: {sec.get('ticker')} × {_float(h.get('qty')):.0f}")
        else:
            click.echo(f"✅ Bought: {sec.get('ticker')} × {_float(h.get('qty')):.0f}")

        click.echo(f"   Price:  {_fmt_num(h.get('price'))} {h.get('currency', '')}")
        click.echo(f"   Cost:   {_fmt_num(h.get('amount'))} {h.get('currency', '')}")
        click.echo()
        click.echo(f"   Account: {acct.get('name')}")
        click.echo(f"   Total:   {_fmt_num(acct.get('total_balance'))} {acct.get('currency', '')}")
        click.echo(f"   Stocks:  {_fmt_num(acct.get('holdings_value'))} {acct.get('currency', '')}")
        click.echo(f"   Cash:    {_fmt_num(acct.get('cash'))} {acct.get('currency', '')}")


@holding_group.command("update")
@_api_key_opt
@_url_opt
@click.option("--account", "account_name", required=True, help="Account name")
@click.option("--ticker", required=True, help="Security ticker to update")
@click.option("--qty", type=float, default=None, help="New quantity (buy more or sell some)")
@click.option("--price", type=float, default=None, help="New price per share")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
@click.option("--dry-run", is_flag=True, help="Preview the write without performing it")
@click.option("--reason", default=None,
              help="Why this adjustment — recorded to Mem0 as an investment_decision")
@click.option("--confidence", type=int, default=None, help="Confidence 1-10")
def holding_update(api_key, url, account_name, ticker, qty, price, as_json,
                   dry_run, reason, confidence):
    """Update position: change quantity (buy more/sell some) or update price.

    - Increasing qty: cash decreases (buying more)
    - Decreasing qty: cash increases (selling some)
    - Price change only: cash unchanged, holdings value changes

    Example:
        maybe holding update --account <account_name> --ticker AAPL --qty 120    # buy 20 more
        maybe holding update --account <account_name> --ticker AAPL --qty 80     # sell 20
        maybe holding update --account <account_name> --ticker AAPL --price 160  # price update
    """
    c = _client(api_key, url)
    accs = c.accounts().get("accounts", [])
    match = _find_account(accs, account_name)
    if not match:
        click.echo(f"Error: No account matching '{account_name}'", err=True)
        c.close()
        raise SystemExit(1)

    # Find the holding
    hs = c.holdings(account_id=match["id"]).get("holdings", [])
    target = None
    for h in hs:
        if h.get("security", {}).get("ticker", "").upper() == ticker.upper():
            target = h
            break

    if not target:
        click.echo(f"Error: No holding for {ticker} in {match['name']}", err=True)
        c.close()
        raise SystemExit(1)

    details = {"account": match["name"], "ticker": ticker, "qty": qty, "price": price}
    if dry_run:
        _dry_run_preview("holding update", details, as_json)
        c.close()
        return

    try:
        result = c.update_holding(
            holding_id=target["id"], qty=qty, price=price
        )
        _audit("holding update", "update_holding", account=match["name"], details=details,
               result={"action": result.get("action") if isinstance(result, dict) else None})
        c.close()
    except Exception as e:
        _audit("holding update", "update_holding", account=match["name"], details=details,
               status="error", result={"error": str(e)})
        click.echo(f"Error: {e}", err=True)
        c.close()
        raise SystemExit(1)

    _capture_decision(reason, confidence, action="adjust", account=match["name"],
                      ticker=ticker, amount=qty, date=None)

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        h = result.get("holding", {})
        sec = h.get("security", {})
        acct = result.get("account", {})
        action = result.get("action", "updated")

        action_labels = {
            "bought_more": "📈 Bought more shares",
            "sold_some": "📉 Sold some shares",
            "sold_all": "💰 Sold all shares",
            "price_updated": "💲 Price updated"
        }
        click.echo(f"✅ {action_labels.get(action, action)}: {sec.get('ticker', ticker)}")

        if h:
            click.echo(f"   Qty:    {_float(h.get('qty')):.0f}")
            click.echo(f"   Price:  {_fmt_num(h.get('price'))} {h.get('currency', '')}")
            click.echo(f"   Value:  {_fmt_num(h.get('amount'))} {h.get('currency', '')}")

        click.echo()
        click.echo(f"   Account: {acct.get('name')}")
        click.echo(f"   Total:   {_fmt_num(acct.get('total_balance'))} {acct.get('currency', '')}")
        click.echo(f"   Stocks:  {_fmt_num(acct.get('holdings_value'))} {acct.get('currency', '')}")
        click.echo(f"   Cash:    {_fmt_num(acct.get('cash'))} {acct.get('currency', '')}")


@holding_group.command("sell")
@_api_key_opt
@_url_opt
@click.option("--account", "account_name", required=True, help="Account name")
@click.option("--ticker", required=True, help="Security ticker to sell")
@click.option("--qty", type=float, default=None, help="Shares to sell (omit to sell all)")
@click.option("--price", type=float, default=None, help="Sale price per share")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
@click.option("--dry-run", is_flag=True, help="Preview the write without performing it")
@click.option("--reason", default=None,
              help="Why this sell — recorded to Mem0 as an investment_decision")
@click.option("--confidence", type=int, default=None, help="Confidence 1-10")
def holding_sell(api_key, url, account_name, ticker, qty, price, as_json,
                 dry_run, reason, confidence):
    """Sell shares. Cash increases, holdings decrease.

    - If --qty omitted: sell all shares (delete the holding)
    - If --qty given: sell that many shares (reduce position)

    Example:
        maybe holding sell --account <account_name> --ticker AAPL              # sell all
        maybe holding sell --account <account_name> --ticker AAPL --qty 30     # sell 30 shares
        maybe holding sell --account <account_name> --ticker AAPL --price 160  # sell all at $160
    """
    c = _client(api_key, url)
    accs = c.accounts().get("accounts", [])
    match = _find_account(accs, account_name)
    if not match:
        click.echo(f"Error: No account matching '{account_name}'", err=True)
        c.close()
        raise SystemExit(1)

    # Find the holding
    hs = c.holdings(account_id=match["id"]).get("holdings", [])
    target = None
    for h in hs:
        if h.get("security", {}).get("ticker", "").upper() == ticker.upper():
            target = h
            break

    if not target:
        click.echo(f"Error: No holding for {ticker} in {match['name']}", err=True)
        c.close()
        raise SystemExit(1)

    current_qty = _float(target.get("quantity", 0))
    current_price = _float(target.get("price", 0))
    sale_price = price if price else current_price

    details = {"account": match["name"], "ticker": ticker,
               "qty": "all" if qty is None else qty, "price": sale_price}
    if dry_run:
        _dry_run_preview("holding sell", details, as_json)
        c.close()
        return

    if qty is None:
        # Sell all → delete
        try:
            result = c.delete_holding(target["id"])
            _audit("holding sell", "delete_holding", account=match["name"], details=details)
            c.close()
        except Exception as e:
            _audit("holding sell", "delete_holding", account=match["name"], details=details,
                   status="error", result={"error": str(e)})
            click.echo(f"Error: {e}", err=True)
            c.close()
            raise SystemExit(1)

        if as_json:
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            proceeds = current_qty * sale_price
            click.echo(f"💰 Sold ALL {current_qty:.0f} shares of {ticker} at {sale_price:.2f}")
            click.echo(f"   Proceeds: {proceeds:,.2f} {match['currency']}")
            click.echo(f"   (Cash increases by this amount)")
    else:
        # Sell some → reduce qty
        new_qty = current_qty - qty
        if new_qty <= 0:
            click.echo(f"Selling all {current_qty:.0f} shares (requested {qty:.0f} exceeds holding)")
            new_qty = 0

        try:
            result = c.update_holding(
                holding_id=target["id"], qty=new_qty, price=sale_price
            )
            _audit("holding sell", "update_holding", account=match["name"], details=details)
            c.close()
        except Exception as e:
            _audit("holding sell", "update_holding", account=match["name"], details=details,
                   status="error", result={"error": str(e)})
            click.echo(f"Error: {e}", err=True)
            c.close()
            raise SystemExit(1)

        if as_json:
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            proceeds = qty * sale_price
            acct = result.get("account", {})
            if new_qty <= 0:
                click.echo(f"💰 Sold ALL {current_qty:.0f} shares of {ticker} at {sale_price:.2f}")
            else:
                click.echo(f"📉 Sold {qty:.0f} shares of {ticker} at {sale_price:.2f}")
                click.echo(f"   Remaining: {new_qty:.0f} shares")
            click.echo(f"   Proceeds: {proceeds:,.2f} {match['currency']}")
            click.echo()
            click.echo(f"   Account: {acct.get('name')}")
            click.echo(f"   Total:   {_fmt_num(acct.get('total_balance'))} {acct.get('currency', '')}")
            click.echo(f"   Stocks:  {_fmt_num(acct.get('holdings_value'))} {acct.get('currency', '')}")
            click.echo(f"   Cash:    {_fmt_num(acct.get('cash'))} {acct.get('currency', '')}")

    _capture_decision(reason, confidence, action="sell", account=match["name"],
                      ticker=ticker, amount=qty, date=None)


@holding_group.command("delete")
@_api_key_opt
@_url_opt
@click.option("--account", "account_name", required=True, help="Account name")
@click.option("--ticker", required=True, help="Security ticker to delete")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def holding_delete(api_key, url, account_name, ticker, as_json):
    """Delete a manual holding (sell all, cash restored).

    Example:
        maybe holding delete --account <account_name> --ticker AAPL
    """
    c = _client(api_key, url)
    accs = c.accounts().get("accounts", [])
    match = _find_account(accs, account_name)
    if not match:
        click.echo(f"Error: No account matching '{account_name}'", err=True)
        c.close()
        raise SystemExit(1)

    hs = c.holdings(account_id=match["id"]).get("holdings", [])
    target = None
    for h in hs:
        if h.get("security", {}).get("ticker", "").upper() == ticker.upper():
            target = h
            break

    if not target:
        click.echo(f"Error: No holding for {ticker} in {match['name']}", err=True)
        c.close()
        raise SystemExit(1)

    try:
        result = c.delete_holding(target["id"])
        c.close()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        c.close()
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        msg = result.get("message", "Holding deleted")
        click.echo(f"✅ {msg}")


@holding_group.command("sync")
@_api_key_opt
@_url_opt
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def holding_sync(api_key, url, as_json):
    """Sync security prices from Yahoo Finance.

    Updates all holdings with latest market prices.
    """
    c = _client(api_key, url)
    try:
        result = c.sync_prices()
        c.close()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        c.close()
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        r = result.get("results", {})
        updated = r.get("updated", [])
        skipped = r.get("skipped", [])
        errors = r.get("errors", [])

        click.echo(f"✅ Price sync complete")
        click.echo(f"   Updated: {len(updated)}")
        click.echo(f"   Skipped: {len(skipped)}")
        click.echo(f"   Errors:  {len(errors)}")

        if updated:
            click.echo()
            for u in updated:
                click.echo(f"   {u['ticker']:10s} {u['account']:20s} {_float(u.get('old_price', 0)):.2f} → {_float(u.get('new_price', 0)):.2f}")

        if errors:
            click.echo()
            click.echo("Errors:")
            for e in errors:
                click.echo(f"   {e['ticker']:10s} {e['error']}")


@holding_group.command("rate")
@_api_key_opt
@_url_opt
@click.option("--from", "from_currency", required=True, help="From currency (e.g. USD)")
@click.option("--to", "to_currency", required=True, help="To currency (e.g. CNY)")
@click.option("--rate", "rate_value", type=float, default=None, help="Rate value (auto-fetched from yfinance if omitted)")
@click.option("--date", default=None, help="Date (YYYY-MM-DD)")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def holding_rate(api_key, url, from_currency, to_currency, rate_value, date, as_json):
    """Set exchange rate (auto-fetched from Yahoo Finance if rate not provided).

    Example:
        maybe holding rate --from USD --to CNY
        maybe holding rate --from USD --to CNY --rate 7.24
    """
    if rate_value is None:
        # Fetch from yfinance
        try:
            import yfinance as yf
            ticker = f"{from_currency}{to_currency}=X"
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if hist.empty:
                click.echo(f"Error: Could not fetch rate for {from_currency}/{to_currency}", err=True)
                raise SystemExit(1)
            rate_value = float(hist["Close"].iloc[-1])
            click.echo(f"Fetched rate: {from_currency}/{to_currency} = {rate_value:.4f}")
        except ImportError:
            click.echo("Error: yfinance not installed. Provide --rate or install yfinance.", err=True)
            raise SystemExit(1)

    c = _client(api_key, url)
    try:
        result = c.create_exchange_rate(from_currency, to_currency, rate_value, date=date)
        c.close()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        c.close()
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        r = result.get("rate", {})
        click.echo(f"✅ Exchange rate set:")
        click.echo(f"   {r.get('from_currency')}/{r.get('to_currency')} = {r.get('rate'):.4f}")
        click.echo(f"   {r.get('to_currency')}/{r.get('from_currency')} = {r.get('reverse_rate'):.4f}")


# ── daily-sync ──────────────────────────────────────────────────────────

@main.command("daily-sync")
@_api_key_opt
@_url_opt
@_json_opt
@click.option("--dry-run", is_flag=True, help="Show what would be updated without making changes")
def daily_sync(api_key, url, as_json, dry_run):
    """Sync holding prices and exchange rates from Yahoo Finance.
    
    Fetches current prices from Yahoo Finance outside Docker,
    then pushes updates to Maybe API.
    """
    from .daily_sync import sync_holding_prices, sync_exchange_rates

    c = _client(api_key, url)
    
    price_results = sync_holding_prices(c, dry_run=dry_run)
    rate_results = sync_exchange_rates(c, dry_run=dry_run)
    
    c.close()

    if as_json:
        output = {"prices": price_results, "rates": rate_results}
        click.echo(json.dumps(output, indent=2, default=str))
    else:
        if dry_run:
            click.echo("=== DRY RUN ===")
        
        click.echo("=== 持仓价格同步 ===")
        if price_results["updated"]:
            for u in price_results["updated"]:
                old = f"${u['old_price']:.2f}" if u["old_price"] else "N/A"
                click.echo(f"  ✅ {u['ticker']}: {old} → ${u['new_price']:.2f}")
        if price_results["skipped"]:
            for s in price_results["skipped"]:
                click.echo(f"  ⏭️  {s.get('ticker', s.get('reason', '?'))}: {s.get('reason', 'skipped')}")
        if price_results["errors"]:
            for e in price_results["errors"]:
                click.echo(f"  ❌ {e.get('ticker', '?')}: {e.get('error', 'unknown')}")
        if not price_results["updated"] and not price_results["skipped"] and not price_results["errors"]:
            click.echo("  (no holdings)")

        click.echo()
        click.echo("=== 汇率同步 ===")
        if rate_results["updated"]:
            for u in rate_results["updated"]:
                click.echo(f"  ✅ {u['pair']}: {u['rate']}")
        if rate_results["skipped"]:
            for s in rate_results["skipped"]:
                click.echo(f"  ⏭️  {s.get('pair', '?')}: {s.get('reason', 'skipped')}")
        if rate_results["errors"]:
            for e in rate_results["errors"]:
                click.echo(f"  ❌ {e.get('pair', '?')}: {e.get('error', 'unknown')}")


# ── portfolio ─────────────────────────────────────────────────────────────

@main.group("portfolio")
def portfolio_group():
    """Investment allocation analysis vs a target policy (asset-class based)."""
    pass


@portfolio_group.command("analyze")
@_api_key_opt
@_url_opt
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
@click.option("--policy", "policy_path", default=None, help="Path to policy.yaml")
def portfolio_analyze(api_key, url, as_json, policy_path):
    """Current allocation vs target + drift + single-security concentration.

    数据来源：账户/持仓/总资产 → Maybe；汇率 → Maybe exchange rates；
    目标配置 → ~/.config/maybe-finance/portfolio/policy.yaml。仅客观计算，非投资建议。
    """
    from . import portfolio as pf
    pol = pf.load_policy(policy_path)
    c = _client(api_key, url)
    try:
        bs = c.balance_sheet()
        accs = c.accounts()
        hs = c.holdings()
        rates = c.exchange_rates().get("exchange_rates", [])
    finally:
        c.close()

    snap = {
        "currency": bs.get("currency"),
        "total_assets": bs.get("assets", {}).get("current"),
        "accounts": accs.get("accounts", []),
        "holdings": hs.get("holdings", []),
    }
    result = pf.analyze(snap, rates, pol)

    if as_json:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    base = result["base_currency"]
    click.echo(f"=== 资产配置分析（基准币 {base}）===")
    click.echo(f"总资产(自算): {_fmt_num(result['total_assets'])} {base}")
    rec = result.get("reconciliation")
    if rec:
        click.echo(f"  vs Maybe total_assets {_fmt_num(rec['maybe_total_assets'])} (差 {rec['diff_pct']}%)")
    click.echo()
    click.echo(f"{'类别':<10}{'实际':>9}{'目标':>8}{'漂移':>9}  状态")
    for a in result["allocation"]:
        click.echo(f"{a['class']:<10}{a['actual_pct']:>8.1f}%{a['target_pct']:>7.0f}%{a['drift_pct']:>+8.1f}%  {a['status']}")
    if result["rebalance"]:
        click.echo("\n再平衡提示（仅供参考，非投资建议）:")
        for r in result["rebalance"]:
            click.echo(f"  {r['class']}: {r['action']} ~{_fmt_num(r['amount'])} {r['currency']}")
    breaches = [x for x in result["concentration"] if x["breach"]]
    if breaches:
        click.echo(f"\n⚠️ 单一证券超限 (>{breaches[0]['limit_pct']:.0f}%):")
        for x in breaches:
            click.echo(f"  {x['ticker']}: {x['pct']}%")
    elif result["concentration"]:
        top = result["concentration"][0]
        click.echo(f"\n单一证券集中度 OK（最高 {top['ticker']} {top['pct']}% ≤ {top['limit_pct']:.0f}%）")
    for w in result["warnings"]:
        click.echo(f"⚠️ {w}", err=True)


@portfolio_group.command("policy")
@click.option("--policy", "policy_path", default=None, help="Path to policy.yaml")
def portfolio_policy(policy_path):
    """Show the policy file location and contents (creates from template on first run)."""
    from . import portfolio as pf
    pf.load_policy(policy_path)  # ensure created from template
    path = Path(policy_path) if policy_path else pf.POLICY_PATH
    click.echo(f"Policy file: {path}\n")
    click.echo(path.read_text(encoding="utf-8"))


# ── audit ───────────────────────────────────────────────────────────────

@main.command("audit")
@click.option("--limit", "-n", default=20, type=int, help="Show last N entries (default 20)")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON lines")
def audit(limit, as_json):
    """Show the write audit log (every reconcile/transaction/holding write).

    Append-only log at ~/.config/maybe-finance/audit/writes.jsonl
    """
    if not AUDIT_PATH.exists():
        click.echo(f"No audit log yet ({AUDIT_PATH}).")
        return

    lines = AUDIT_PATH.read_text(encoding="utf-8").splitlines()
    recent = lines[-limit:]

    if as_json:
        click.echo("\n".join(recent))
        return

    click.echo(f"Last {len(recent)} write(s) — {AUDIT_PATH}\n")
    for line in recent:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        status = r.get("status", "?")
        mark = "✅" if status == "ok" else "❌"
        d = r.get("details", {})
        summary = ", ".join(f"{k}={v}" for k, v in d.items() if v is not None)
        click.echo(f"{mark} {r.get('ts', '')}  {r.get('command', '')}")
        if summary:
            click.echo(f"     {summary}")


if __name__ == "__main__":
    main()
