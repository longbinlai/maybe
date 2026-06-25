"""Tests for mem0-memory client and migrator."""

import os
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ── 配置加载测试 ─────────────────────────────────────────────────────────

class TestConfigLoading:
    """测试 YAML 配置加载和环境变量替换。"""

    def test_config_loading(self, tmp_path):
        """验证 YAML 配置正确加载。"""
        config = {
            "mem0": {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {"host": "localhost", "port": 6333},
                },
            },
            "categories": ["investment_decision", "market_event"],
        }
        config_file = tmp_path / "mem0.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")

        from mem0_memory.client import _process_config
        with open(config_file, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)

        processed = _process_config(loaded)
        assert processed["mem0"]["vector_store"]["provider"] == "qdrant"
        assert processed["mem0"]["vector_store"]["config"]["port"] == 6333
        assert processed["categories"] == ["investment_decision", "market_event"]

    def test_env_var_substitution(self):
        """验证 ${VAR} 模式被正确替换。"""
        from mem0_memory.client import _substitute_env_vars

        # 测试简单替换
        os.environ["TEST_VAR_123"] = "hello"
        assert _substitute_env_vars("${TEST_VAR_123}") == "hello"
        del os.environ["TEST_VAR_123"]

        # 测试默认值
        result = _substitute_env_vars("${NONEXISTENT_VAR_XYZ:-default_value}")
        assert result == "default_value"

        # 测试未设置且无默认值
        result = _substitute_env_vars("${NONEXISTENT_VAR_XYZ}")
        assert result == ""

        # 测试混合文本
        os.environ["TEST_PORT"] = "8080"
        result = _substitute_env_vars("http://localhost:${TEST_PORT}/api")
        assert result == "http://localhost:8080/api"
        del os.environ["TEST_PORT"]

    def test_env_var_substitution_with_default(self):
        """验证 ${VAR:-default} 的完整行为。"""
        from mem0_memory.client import _substitute_env_vars

        # 设置了环境变量时忽略默认值
        os.environ["MY_API_KEY"] = "sk-123"
        assert _substitute_env_vars("${MY_API_KEY:-fallback}") == "sk-123"
        del os.environ["MY_API_KEY"]

        # 未设置时使用默认值（空字符串也有效）
        assert _substitute_env_vars("${MY_API_KEY:-}") == ""
        assert _substitute_env_vars("${MY_API_KEY:-no-key}") == "no-key"

    def test_process_config_recursive(self):
        """验证嵌套结构中的环境变量被递归替换。"""
        from mem0_memory.client import _process_config

        os.environ["NESTED_TEST_HOST"] = "myhost"
        config = {
            "level1": {
                "level2": {
                    "host": "${NESTED_TEST_HOST}",
                    "items": ["${NESTED_TEST_HOST}", "static"],
                },
            },
        }
        processed = _process_config(config)
        assert processed["level1"]["level2"]["host"] == "myhost"
        assert processed["level1"]["level2"]["items"] == ["myhost", "static"]
        del os.environ["NESTED_TEST_HOST"]


# ── Mem0 客户端测试（mock）────────────────────────────────────────────────

class TestMem0Client:
    """测试 Mem0Client 方法，使用 mock 避免连接真实服务。"""

    @patch("mem0_memory.client.Memory")
    def test_add_memory(self, mock_memory_cls, tmp_path):
        """测试添加记忆。"""
        # 配置 mock
        mock_instance = MagicMock()
        mock_memory_cls.from_config.return_value = mock_instance
        mock_instance.add.return_value = {
            "results": [{"id": "mem-001", "status": "created"}],
        }

        # 创建配置文件
        config = {
            "mem0": {
                "vector_store": {"provider": "qdrant", "config": {"host": "localhost", "port": 6333}},
                "llm": {"provider": "openai", "config": {"model": "gpt-4o-mini", "api_key": "sk-test"}},
                "embedder": {"provider": "openai", "config": {"model": "text-embedding-3-small", "api_key": "sk-test"}},
            },
            "categories": ["investment_decision"],
        }
        config_file = tmp_path / "mem0.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")

        from mem0_memory.client import Mem0Client
        client = Mem0Client(config_path=str(config_file))

        result = client.add(
            content="买入腾讯 100 股",
            category="investment_decision",
            metadata={"ticker": "0700.HK"},
        )

        # 验证调用 (add uses user_id, search/get_all use filters)
        mock_instance.add.assert_called_once()
        call_args = mock_instance.add.call_args
        assert call_args[0][0] == "买入腾讯 100 股"
        assert call_args[1]["user_id"] == "family"
        assert call_args[1]["metadata"]["category"] == "investment_decision"
        assert call_args[1]["metadata"]["ticker"] == "0700.HK"
        assert "created_at" in call_args[1]["metadata"]

        assert result["results"][0]["id"] == "mem-001"

    @patch("mem0_memory.client.Memory")
    def test_search_memory(self, mock_memory_cls, tmp_path):
        """测试搜索记忆。"""
        mock_instance = MagicMock()
        mock_memory_cls.from_config.return_value = mock_instance
        mock_instance.search.return_value = [
            {
                "id": "mem-001",
                "score": 0.95,
                "memory": "买入腾讯 100 股",
                "metadata": {"category": "investment_decision", "date": "2026-05-25"},
            },
        ]

        config = {
            "mem0": {
                "vector_store": {"provider": "qdrant", "config": {"host": "localhost", "port": 6333}},
                "llm": {"provider": "openai", "config": {"model": "gpt-4o-mini", "api_key": "sk-test"}},
                "embedder": {"provider": "openai", "config": {"model": "text-embedding-3-small", "api_key": "sk-test"}},
            },
            "categories": ["investment_decision"],
        }
        config_file = tmp_path / "mem0.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")

        from mem0_memory.client import Mem0Client
        client = Mem0Client(config_path=str(config_file))

        results = client.search(query="腾讯", category="investment_decision", limit=5)

        mock_instance.search.assert_called_once_with(
            "腾讯",
            top_k=5,
            filters={"user_id": "family", "category": "investment_decision"},
        )
        assert len(results) == 1
        assert results[0]["score"] == 0.95
        assert "腾讯" in results[0]["memory"]

    @patch("mem0_memory.client.Memory")
    def test_get_all(self, mock_memory_cls, tmp_path):
        """测试获取所有记忆。"""
        mock_instance = MagicMock()
        mock_memory_cls.from_config.return_value = mock_instance
        mock_instance.get_all.return_value = [
            {"id": "mem-001", "metadata": {"category": "investment_decision"}},
            {"id": "mem-002", "metadata": {"category": "market_event"}},
        ]

        config = {
            "mem0": {
                "vector_store": {"provider": "qdrant", "config": {"host": "localhost", "port": 6333}},
                "llm": {"provider": "openai", "config": {"model": "gpt-4o-mini", "api_key": "sk-test"}},
                "embedder": {"provider": "openai", "config": {"model": "text-embedding-3-small", "api_key": "sk-test"}},
            },
            "categories": [],
        }
        config_file = tmp_path / "mem0.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")

        from mem0_memory.client import Mem0Client
        client = Mem0Client(config_path=str(config_file))

        # 无过滤
        results = client.get_all()
        assert len(results) == 2

        # 按分类过滤
        results = client.get_all(category="investment_decision")
        mock_instance.get_all.assert_called_with(
            filters={"user_id": "family", "category": "investment_decision"},
            top_k=1000,
        )

    @patch("mem0_memory.client.Memory")
    def test_delete_memory(self, mock_memory_cls, tmp_path):
        """测试删除记忆。"""
        mock_instance = MagicMock()
        mock_memory_cls.from_config.return_value = mock_instance

        config = {
            "mem0": {
                "vector_store": {"provider": "qdrant", "config": {"host": "localhost", "port": 6333}},
                "llm": {"provider": "openai", "config": {"model": "gpt-4o-mini", "api_key": "sk-test"}},
                "embedder": {"provider": "openai", "config": {"model": "text-embedding-3-small", "api_key": "sk-test"}},
            },
            "categories": [],
        }
        config_file = tmp_path / "mem0.yaml"
        config_file.write_text(yaml.dump(config), encoding="utf-8")

        from mem0_memory.client import Mem0Client
        client = Mem0Client(config_path=str(config_file))

        assert client.delete("mem-001") is True
        mock_instance.delete.assert_called_once_with("mem-001")

        # 测试删除失败
        mock_instance.delete.side_effect = Exception("not found")
        assert client.delete("mem-999") is False


# ── 迁移测试 ─────────────────────────────────────────────────────────────

class TestMigration:
    """测试 Markdown → Mem0 迁移功能。"""

    def _create_sample_files(self, tmp_path: Path):
        """创建示例 Markdown 记忆文件。"""
        # 每日决策文件
        daily = tmp_path / "2026-05-25.md"
        daily.write_text(textwrap.dedent("""\
            # 2026-05-25 记忆

            ### 2026-05-25: 买入腾讯
            - **行动**: buy
            - **账户**: 券商账户A
            - **证券**: 0700.HK
            - **数量**: 100
            - **价格**: $380
            - **理由**: AI业务增长强劲
            - **预期结果**: +15% in 90d
            - **信心指数**: 7
            - **状态**: active

            ### 2026-05-25 14:30: 美联储利率决议
            - **类别**: 货币政策
            - **市场**: US
            - **关键数据**: 加息25bp
            - **情绪**: 鹰派
            - **摘要**: 美联储如预期加息，鲍威尔表态偏鹰
        """), encoding="utf-8")

        # 周度回顾文件
        weekly = tmp_path / "2026-05-25-weekly.md"
        weekly.write_text(textwrap.dedent("""\
            # 2026-05-25 周度回顾

            ## 本周决策总结
            - 买入腾讯 100 股
            - 观察美联储动向

            ## 市场概况
            恒生指数本周上涨 2.3%，科技股表现强劲。
        """), encoding="utf-8")

        # 月度回顾文件
        monthly = tmp_path / "2026-05-monthly.md"
        monthly.write_text(textwrap.dedent("""\
            # 2026年5月 月度分析

            ## 投资组合表现
            本月整体收益 +3.5%，跑赢基准。

            ## 策略调整建议
            建议增加科技股配置比例。
        """), encoding="utf-8")

    def test_parse_all(self, tmp_path):
        """测试解析所有 Markdown 文件。"""
        self._create_sample_files(tmp_path)

        from mem0_memory.migrator import MarkdownMigrator
        migrator = MarkdownMigrator(str(tmp_path))
        entries = migrator.parse_all()

        # 应该有：2 条每日记录 + 1 条周度回顾 + 1 条月度回顾 = 4 条
        assert len(entries) == 4

        # 验证分类（market_event 已废弃，现映射到 market_view）
        categories = [e.category for e in entries]
        assert "investment_decision" in categories
        assert "market_view" in categories
        assert "market_event" not in categories
        assert "weekly_review" in categories
        assert "monthly_review" in categories

        # 验证决策条目包含关键字段
        decision = next(e for e in entries if e.category == "investment_decision")
        assert "0700.HK" in decision.metadata.get("security", "")
        assert decision.metadata.get("action") == "buy"

    def test_migrate_dry_run(self, tmp_path):
        """测试 dry-run 模式不会实际调用 Mem0。"""
        self._create_sample_files(tmp_path)

        from mem0_memory.migrator import MarkdownMigrator
        migrator = MarkdownMigrator(str(tmp_path))

        mock_client = MagicMock()
        stats = migrator.migrate(mock_client, dry_run=True)

        # dry-run 不应调用 add
        mock_client.add.assert_not_called()

        # 验证统计信息
        assert stats["total_entries"] == 4
        assert stats["total_files"] == 3
        assert "migrated" not in stats or stats.get("migrated") == 0

    def test_migrate_dry_run_with_real_call(self, tmp_path):
        """测试非 dry-run 模式会调用 Mem0 client.add()。"""
        self._create_sample_files(tmp_path)

        from mem0_memory.migrator import MarkdownMigrator
        migrator = MarkdownMigrator(str(tmp_path))

        mock_client = MagicMock()
        mock_client.add.return_value = {"results": [{"id": "mem-001"}]}

        stats = migrator.migrate(mock_client, dry_run=False)

        assert stats["migrated"] == 4
        assert stats["skipped"] == 0
        assert mock_client.add.call_count == 4

    def test_classify_entry(self, tmp_path):
        """测试条目分类逻辑。"""
        self._create_sample_files(tmp_path)

        from mem0_memory.migrator import MarkdownMigrator
        migrator = MarkdownMigrator(str(tmp_path))
        entries = migrator.parse_all()

        # 决策应被分类为 investment_decision
        decisions = [e for e in entries if e.category == "investment_decision"]
        assert len(decisions) >= 1
        assert any("腾讯" in e.title for e in decisions)

        # 美联储事件不再分类为已废弃的 market_event，而是有效的 market_view
        events = [e for e in entries if e.category == "market_view"]
        assert len(events) >= 1
        assert any("美联储" in e.title for e in events)
        # 确保不会产出已废弃分类
        assert all(e.category != "market_event" for e in entries)

    def test_empty_directory(self, tmp_path):
        """测试空目录不报错。"""
        from mem0_memory.migrator import MarkdownMigrator
        migrator = MarkdownMigrator(str(tmp_path))
        entries = migrator.parse_all()
        assert entries == []

    def test_skip_memory_index(self, tmp_path):
        """测试 MEMORY.md 索引文件被跳过。"""
        index_file = tmp_path / "MEMORY.md"
        index_file.write_text("# Memory Index\n- [Entry 1](entry.md)\n", encoding="utf-8")

        from mem0_memory.migrator import MarkdownMigrator
        migrator = MarkdownMigrator(str(tmp_path))
        entries = migrator.parse_all()
        assert entries == []
