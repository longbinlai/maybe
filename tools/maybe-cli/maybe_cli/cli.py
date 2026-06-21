"""maybe-cli: command-line interface for Maybe Finance."""
import json
import os
import sys

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
def reconcile(api_key, url, as_json, account_name, balance, date):
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

    old_balance = _float(match["balance"])
    delta = balance - old_balance

    if not as_json:
        click.echo(f"Account:  {match['name']} ({match['account_type']})")
        click.echo(f"Old:      {match['balance_formatted']}")
        click.echo(f"New:      {_fmt_num(balance)} {match['currency']}")
        direction = "↑" if delta >= 0 else "↓"
        click.echo(f"Change:   {direction} {_fmt_num(abs(delta))}")
        click.echo()

    result = c.reconcile(match["id"], balance, date=date)
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
@click.option("--currency", help="Currency (defaults to family currency)")
@click.option("--category", help="Category name (fuzzy match)")
@click.option("--merchant", help="Merchant name (fuzzy match)")
@click.option("--tag", "tags", multiple=True, help="Tag name(s) (can specify multiple)")
@click.option("--nature", type=click.Choice(["income", "expense", "inflow", "outflow"]),
              help="Transaction nature (income/expense)")
def add_transaction(api_key, url, as_json, account, date, amount, name,
                   description, notes, currency, category, merchant, tags, nature):
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
        if as_json:
            _output({"error": str(e)}, True)
        else:
            click.echo(f"❌ Failed to create transaction: {e}", err=True)
        sys.exit(1)
    finally:
        c.close()


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
def holding_add(api_key, url, account_name, ticker, qty, price, avg_cost, date, as_json):
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

    try:
        result = c.create_holding(
            account_id=match["id"], ticker=ticker, qty=qty,
            price=price, avg_cost=avg_cost, date=date
        )
        c.close()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        c.close()
        raise SystemExit(1)

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
def holding_update(api_key, url, account_name, ticker, qty, price, as_json):
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

    try:
        result = c.update_holding(
            holding_id=target["id"], qty=qty, price=price
        )
        c.close()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        c.close()
        raise SystemExit(1)

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
def holding_sell(api_key, url, account_name, ticker, qty, price, as_json):
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

    if qty is None:
        # Sell all → delete
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
            c.close()
        except Exception as e:
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


if __name__ == "__main__":
    main()
