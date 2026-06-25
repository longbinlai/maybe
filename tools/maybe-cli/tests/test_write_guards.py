"""Tests for finance-write safety guards in maybe-cli.

覆盖两类正确性防护，全部用 mock client，不需要运行 Maybe 服务：
  1. add-transaction 跨币种必须显式确认（--yes）
  2. add-transaction / reconcile 同一天的 Valuation 与 Transaction 冲突防护

运行: PYTHONPATH=tools/maybe-cli ~/pyenv/maybe/bin/python -m pytest \
        tools/maybe-cli/tests/test_write_guards.py -q
"""

import pytest
from click.testing import CliRunner

import maybe_cli.cli as climod
from maybe_cli.cli import main


class FakeClient:
    """最小化的 MaybeClient 替身，记录写操作是否被调用。"""

    def __init__(self, accounts, valuations=None, transactions=None):
        self._accounts = accounts
        self._valuations = valuations or []
        self._transactions = transactions or []
        self.created_transactions = []
        self.reconciled = []
        self.closed = False

    # --- reads ---
    def accounts(self):
        return {"accounts": self._accounts}

    def valuations(self, account_id):
        return {"valuations": self._valuations}

    def transactions(self, account_id=None, start_date=None, end_date=None):
        # 仅返回落在 [start_date, end_date] 的交易（这里日期是精确匹配）
        rows = [t for t in self._transactions
                if (start_date is None or t["date"] >= start_date)
                and (end_date is None or t["date"] <= end_date)]
        return {"transactions": rows}

    def categories(self):
        return {"categories": []}

    def tags(self):
        return {"tags": []}

    # --- writes (record only) ---
    def create_transaction(self, **kwargs):
        self.created_transactions.append(kwargs)
        return {"id": "txn-1", **kwargs}

    def reconcile(self, account_id, balance, date=None):
        self.reconciled.append({"account_id": account_id, "balance": balance, "date": date})
        return {"id": "val-1", "balance": balance}

    def close(self):
        self.closed = True


def _install(monkeypatch, fake):
    monkeypatch.setattr(climod, "_client", lambda *a, **k: fake)


ACCT_CNY = {
    "id": "acc-cny", "name": "CashCNY", "currency": "CNY",
    "balance": "1000", "balance_formatted": "¥1,000", "account_type": "depository",
}


# ── 跨币种确认 ───────────────────────────────────────────────────────────────

def test_cross_currency_blocked_without_yes(monkeypatch):
    fake = FakeClient([ACCT_CNY])
    _install(monkeypatch, fake)
    runner = CliRunner()
    result = runner.invoke(main, [
        "add-transaction", "--json", "-a", "CashCNY", "-d", "2026-06-25",
        "-m", "100", "-n", "USD interest", "--currency", "USD",
    ])
    assert result.exit_code == 1
    assert "currency_mismatch" in result.output
    assert fake.created_transactions == []  # 绝不静默写入


def test_cross_currency_allowed_with_yes(monkeypatch):
    fake = FakeClient([ACCT_CNY])
    _install(monkeypatch, fake)
    runner = CliRunner()
    result = runner.invoke(main, [
        "add-transaction", "--json", "-a", "CashCNY", "-d", "2026-06-25",
        "-m", "100", "-n", "USD interest", "--currency", "USD", "--yes",
    ])
    assert result.exit_code == 0
    assert len(fake.created_transactions) == 1
    assert fake.created_transactions[0]["currency"] == "USD"


def test_same_currency_no_prompt(monkeypatch):
    fake = FakeClient([ACCT_CNY])
    _install(monkeypatch, fake)
    runner = CliRunner()
    result = runner.invoke(main, [
        "add-transaction", "--json", "-a", "CashCNY", "-d", "2026-06-25",
        "-m", "100", "-n", "interest", "--currency", "CNY",
    ])
    assert result.exit_code == 0
    assert len(fake.created_transactions) == 1


# ── 同日 Valuation/Transaction 冲突 ─────────────────────────────────────────

def test_add_transaction_blocked_when_valuation_same_date(monkeypatch):
    fake = FakeClient([ACCT_CNY], valuations=[{"id": "v1", "date": "2026-06-25"}])
    _install(monkeypatch, fake)
    runner = CliRunner()
    result = runner.invoke(main, [
        "add-transaction", "--json", "-a", "CashCNY", "-d", "2026-06-25",
        "-m", "100", "-n", "interest",
    ])
    assert result.exit_code == 1
    assert "valuation_transaction_same_date" in result.output
    assert fake.created_transactions == []


def test_add_transaction_ok_when_valuation_other_date(monkeypatch):
    fake = FakeClient([ACCT_CNY], valuations=[{"id": "v1", "date": "2026-06-20"}])
    _install(monkeypatch, fake)
    runner = CliRunner()
    result = runner.invoke(main, [
        "add-transaction", "--json", "-a", "CashCNY", "-d", "2026-06-25",
        "-m", "100", "-n", "interest",
    ])
    assert result.exit_code == 0
    assert len(fake.created_transactions) == 1


def test_reconcile_blocked_when_transaction_same_date(monkeypatch):
    fake = FakeClient([ACCT_CNY], transactions=[{"id": "t1", "date": "2026-06-25"}])
    _install(monkeypatch, fake)
    runner = CliRunner()
    result = runner.invoke(main, [
        "reconcile", "--json", "--account", "CashCNY",
        "--balance", "1200", "--date", "2026-06-25",
    ])
    assert result.exit_code == 1
    assert "valuation_transaction_same_date" in result.output
    assert fake.reconciled == []


def test_reconcile_ok_when_no_same_date_transaction(monkeypatch):
    fake = FakeClient([ACCT_CNY], transactions=[{"id": "t1", "date": "2026-06-20"}])
    _install(monkeypatch, fake)
    runner = CliRunner()
    result = runner.invoke(main, [
        "reconcile", "--json", "--account", "CashCNY",
        "--balance", "1200", "--date", "2026-06-25",
    ])
    assert result.exit_code == 0
    assert len(fake.reconciled) == 1


def test_reconcile_same_date_allowed_with_yes(monkeypatch):
    fake = FakeClient([ACCT_CNY], transactions=[{"id": "t1", "date": "2026-06-25"}])
    _install(monkeypatch, fake)
    runner = CliRunner()
    result = runner.invoke(main, [
        "reconcile", "--json", "--account", "CashCNY",
        "--balance", "1200", "--date", "2026-06-25", "--yes",
    ])
    assert result.exit_code == 0
    assert len(fake.reconciled) == 1
