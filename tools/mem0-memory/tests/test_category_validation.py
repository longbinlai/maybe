"""Tests for memory category whitelist validation.

纯单元测试，不需要 Qdrant/Ollama 等外部服务——校验逻辑在连接服务之前执行。
运行: PYTHONPATH=tools/mem0-memory ~/pyenv/maybe/bin/python -m pytest \
        tools/mem0-memory/tests/test_category_validation.py -q
"""

import pytest
from click.testing import CliRunner

from mem0_memory.client import (
    ACTIVE_CATEGORIES,
    DEPRECATED_CATEGORIES,
    validate_category,
)
from mem0_memory.cli import cli


# ── validate_category() 纯函数 ───────────────────────────────────────────────

@pytest.mark.parametrize("cat", ACTIVE_CATEGORIES)
def test_all_active_categories_accepted(cat):
    assert validate_category(cat) == cat


def test_whitespace_is_stripped():
    assert validate_category("  investment_decision  ") == "investment_decision"


@pytest.mark.parametrize("cat", list(DEPRECATED_CATEGORIES))
def test_deprecated_categories_rejected(cat):
    with pytest.raises(ValueError) as exc:
        validate_category(cat)
    # 错误信息应说明已废弃并给出迁移提示
    assert "deprecated" in str(exc.value).lower()


def test_deprecated_message_points_to_replacement():
    # allocation_strategy 应提示改用 investment_style
    with pytest.raises(ValueError) as exc:
        validate_category("allocation_strategy")
    assert "investment_style" in str(exc.value)


def test_unknown_category_rejected():
    with pytest.raises(ValueError) as exc:
        validate_category("totally_made_up")
    assert "Unknown category" in str(exc.value)


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_empty_category_rejected(bad):
    with pytest.raises(ValueError):
        validate_category(bad)


def test_active_and_deprecated_do_not_overlap():
    assert set(ACTIVE_CATEGORIES).isdisjoint(DEPRECATED_CATEGORIES)


# ── CLI `add` 拒绝路径（不连服务即可拒绝） ───────────────────────────────────

def test_cli_add_rejects_deprecated_without_touching_services():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["add", "-c", "market_event", "--content", "美联储加息 25bp"],
    )
    assert result.exit_code == 1
    assert "deprecated" in result.output.lower()


def test_cli_add_rejects_unknown_category():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["add", "-c", "typo_category", "--content", "x"],
    )
    assert result.exit_code == 1
    assert "Unknown category" in result.output
