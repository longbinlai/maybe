"""Tests for `memory review` (weekly/monthly review generator).

全部用 monkeypatch，不需要 Maybe / Qdrant / Ollama。
运行: PYTHONPATH=tools/mem0-memory ~/pyenv/maybe/bin/python -m pytest \
        tools/mem0-memory/tests/test_review.py -q
"""

from click.testing import CliRunner

import mem0_memory.cli as climod
from mem0_memory.cli import cli, _period_bounds
from datetime import date


class FakeMem0:
    def __init__(self):
        self.added = []

    def add(self, content, category, metadata=None):
        self.added.append({"content": content, "category": category, "metadata": metadata})
        return {"results": [{"id": "mem-1"}]}


def _fake_maybe_json(maybe_bin, args):
    if args and args[0] == "trades":
        return {"trades": [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}]}
    if args and args[0] == "snapshot":
        return {"net_worth": 1234567.0, "net_worth_formatted": "$1,234,567"}
    return None


def _patch_maybe(monkeypatch):
    monkeypatch.setattr(climod, "_find_maybe", lambda: "/fake/bin/maybe")
    monkeypatch.setattr(climod, "_run_maybe_json", _fake_maybe_json)


# ── period bounds ────────────────────────────────────────────────────────

def test_period_bounds_weekly_starts_monday():
    start, end, period = _period_bounds(False, date(2026, 6, 25))  # Thursday
    assert start == date(2026, 6, 22)  # Monday
    assert end == date(2026, 6, 25)
    assert period.startswith("2026-W")


def test_period_bounds_monthly_starts_first():
    start, end, period = _period_bounds(True, date(2026, 6, 25))
    assert start == date(2026, 6, 1)
    assert period == "2026-06"


# ── dry-run does not write ───────────────────────────────────────────────

def test_review_dry_run_no_write(monkeypatch):
    _patch_maybe(monkeypatch)
    monkeypatch.setattr(climod, "_get_client",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not connect")))
    res = CliRunner().invoke(cli, ["review", "--weekly", "--dry-run"])
    assert res.exit_code == 0
    assert "DRY RUN" in res.output
    assert "weekly_review" in res.output
    assert "交易笔数：3" in res.output


# ── real write path ──────────────────────────────────────────────────────

def test_review_weekly_writes_memory(monkeypatch):
    _patch_maybe(monkeypatch)
    fake = FakeMem0()
    monkeypatch.setattr(climod, "_get_client", lambda *a, **k: fake)
    res = CliRunner().invoke(cli, ["review", "--weekly"])
    assert res.exit_code == 0
    assert len(fake.added) == 1
    rec = fake.added[0]
    assert rec["category"] == "weekly_review"
    assert "period" in rec["metadata"]
    assert rec["metadata"]["trades_count"] == 3


def test_review_monthly_category(monkeypatch):
    _patch_maybe(monkeypatch)
    fake = FakeMem0()
    monkeypatch.setattr(climod, "_get_client", lambda *a, **k: fake)
    res = CliRunner().invoke(cli, ["review", "--monthly"])
    assert res.exit_code == 0
    assert fake.added[0]["category"] == "monthly_review"


# ── graceful degrade + validation ────────────────────────────────────────

def test_review_degrades_when_maybe_missing(monkeypatch):
    monkeypatch.setattr(climod, "_find_maybe", lambda: None)
    res = CliRunner().invoke(cli, ["review", "--weekly", "--dry-run"])
    assert res.exit_code == 0
    assert "not found" in res.output.lower()
    assert "交易笔数：0" in res.output


def test_review_weekly_monthly_mutually_exclusive(monkeypatch):
    _patch_maybe(monkeypatch)
    res = CliRunner().invoke(cli, ["review", "--weekly", "--monthly"])
    assert res.exit_code == 1
    assert "mutually exclusive" in res.output
