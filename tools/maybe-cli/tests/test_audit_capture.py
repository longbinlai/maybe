"""Tests for write-path audit log, --dry-run, and decision capture (Mem0).

全部用 mock client + monkeypatch，不需要 Maybe / Mem0 服务。
运行: PYTHONPATH=tools/maybe-cli ~/pyenv/maybe/bin/python -m pytest \
        tools/maybe-cli/tests/test_audit_capture.py -q
"""

import json

from click.testing import CliRunner

import maybe_cli.cli as climod
from maybe_cli.cli import main


class FakeClient:
    def __init__(self, accounts, holdings=None):
        self._accounts = accounts
        self._holdings = holdings or []
        self.created_transactions = []
        self.created_holdings = []
        self.reconciled = []
        self.closed = False

    def accounts(self):
        return {"accounts": self._accounts}

    def valuations(self, account_id):
        return {"valuations": []}

    def transactions(self, account_id=None, start_date=None, end_date=None):
        return {"transactions": []}

    def categories(self):
        return {"categories": []}

    def tags(self):
        return {"tags": []}

    def holdings(self, account_id=None):
        return {"holdings": self._holdings}

    def create_transaction(self, **kw):
        self.created_transactions.append(kw)
        return {"id": "txn-1"}

    def create_holding(self, **kw):
        self.created_holdings.append(kw)
        return {"action": "bought", "holding": {}, "account": {}}

    def reconcile(self, account_id, balance, date=None):
        self.reconciled.append({"balance": balance, "date": date})
        return {"id": "val-1"}

    def close(self):
        self.closed = True


ACCT = {"id": "a1", "name": "CashCNY", "currency": "CNY",
        "balance": "1000", "balance_formatted": "¥1,000", "account_type": "depository"}
BROKER = {"id": "b1", "name": "Brokerage", "currency": "USD",
          "balance": "5000", "balance_formatted": "$5,000", "account_type": "investment"}


def _install(monkeypatch, fake):
    monkeypatch.setattr(climod, "_client", lambda *a, **k: fake)


# ── --dry-run ────────────────────────────────────────────────────────────

def test_dry_run_add_transaction_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(climod, "AUDIT_PATH", tmp_path / "writes.jsonl")
    fake = FakeClient([ACCT])
    _install(monkeypatch, fake)
    res = CliRunner().invoke(main, [
        "add-transaction", "--json", "-a", "CashCNY", "-d", "2026-06-25",
        "-m", "100", "-n", "interest", "--currency", "CNY", "--dry-run",
    ])
    assert res.exit_code == 0
    assert '"dry_run": true' in res.output
    assert fake.created_transactions == []
    assert not (tmp_path / "writes.jsonl").exists()  # dry-run does not audit


def test_dry_run_reconcile_writes_nothing(monkeypatch):
    fake = FakeClient([ACCT])
    _install(monkeypatch, fake)
    res = CliRunner().invoke(main, [
        "reconcile", "--json", "--account", "CashCNY", "--balance", "1200", "--dry-run",
    ])
    assert res.exit_code == 0
    assert fake.reconciled == []


# ── audit log ────────────────────────────────────────────────────────────

def test_audit_written_on_successful_transaction(monkeypatch, tmp_path):
    audit_file = tmp_path / "writes.jsonl"
    monkeypatch.setattr(climod, "AUDIT_PATH", audit_file)
    fake = FakeClient([ACCT])
    _install(monkeypatch, fake)
    res = CliRunner().invoke(main, [
        "add-transaction", "--json", "-a", "CashCNY", "-d", "2026-06-25",
        "-m", "100", "-n", "interest", "--currency", "CNY",
    ])
    assert res.exit_code == 0
    assert audit_file.exists()
    rec = json.loads(audit_file.read_text().splitlines()[-1])
    assert rec["command"] == "add-transaction"
    assert rec["status"] == "ok"
    assert rec["account"] == "CashCNY"


def test_audit_written_on_reconcile(monkeypatch, tmp_path):
    audit_file = tmp_path / "writes.jsonl"
    monkeypatch.setattr(climod, "AUDIT_PATH", audit_file)
    fake = FakeClient([ACCT])
    _install(monkeypatch, fake)
    res = CliRunner().invoke(main, [
        "reconcile", "--json", "--account", "CashCNY", "--balance", "1200",
    ])
    assert res.exit_code == 0
    rec = json.loads(audit_file.read_text().splitlines()[-1])
    assert rec["command"] == "reconcile"
    assert rec["details"]["new_balance"] == 1200


def test_maybe_audit_command_reads_log(monkeypatch, tmp_path):
    audit_file = tmp_path / "writes.jsonl"
    audit_file.write_text(
        json.dumps({"ts": "2026-06-25T10:00:00", "command": "reconcile",
                    "status": "ok", "details": {"account": "CashCNY"}}) + "\n")
    monkeypatch.setattr(climod, "AUDIT_PATH", audit_file)
    res = CliRunner().invoke(main, ["audit", "--json"])
    assert res.exit_code == 0
    assert "reconcile" in res.output


# ── decision capture wiring ──────────────────────────────────────────────

def test_holding_add_captures_decision_with_reason(monkeypatch, tmp_path):
    monkeypatch.setattr(climod, "AUDIT_PATH", tmp_path / "writes.jsonl")
    calls = []
    monkeypatch.setattr(climod, "_capture_decision",
                        lambda reason, confidence, **kw: calls.append((reason, confidence, kw)))
    fake = FakeClient([BROKER])
    _install(monkeypatch, fake)
    res = CliRunner().invoke(main, [
        "holding", "add", "--account", "Brokerage", "--ticker", "AAPL",
        "--qty", "10", "--price", "150", "--json",
        "--reason", "AI tailwind, long-term hold", "--confidence", "7",
    ])
    assert res.exit_code == 0
    assert len(calls) == 1
    reason, confidence, kw = calls[0]
    assert reason == "AI tailwind, long-term hold"
    assert confidence == 7
    assert kw["action"] == "buy"
    assert kw["ticker"] == "AAPL"


def test_capture_decision_noop_without_reason(monkeypatch):
    # 没有 reason 时绝不调用 subprocess（不连 Mem0）
    import subprocess
    def _boom(*a, **k):
        raise AssertionError("subprocess must not run when reason is empty")
    monkeypatch.setattr(subprocess, "run", _boom)
    climod._capture_decision(None, None, action="buy")  # should be a no-op
