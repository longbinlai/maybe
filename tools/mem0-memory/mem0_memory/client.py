"""Mem0 client wrapper with config loading and env var substitution."""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    # Python 3.9+
    from importlib.resources import files
except ImportError:
    # Python 3.8 fallback
    from importlib_resources import files  # type: ignore

import yaml

try:
    from mem0 import Memory
except ImportError:
    Memory = None  # type: ignore[assignment,misc]


def _get_config_path() -> Path:
    """Get the path to mem0.yaml config file.

    Priority:
    1. ~/.config/maybe-finance/mem0/mem0.yaml (user config, persistent)
    2. Bundled config/mem0.yaml (default template, copied on first run)
    """
    user_config = Path.home() / ".config" / "maybe-finance" / "mem0" / "mem0.yaml"
    if user_config.exists():
        return user_config

    # Try to find the config file in the package
    try:
        config_file = files("mem0_memory").joinpath("config", "mem0.yaml")
        package_path = Path(str(config_file))
    except (TypeError, AttributeError):
        package_path = Path(__file__).parent / "config" / "mem0.yaml"

    # First run: copy from package to user config dir
    if package_path.exists():
        user_config.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(package_path, user_config)
        return user_config

    return package_path


def _substitute_env_vars(value: str) -> str:
    """Substitute ${VAR} and ${VAR:-default} patterns in a string.

    支持两种格式：
    - ${VAR}: 直接用环境变量替换，未设置时为空字符串
    - ${VAR:-default}: 用环境变量替换，未设置时使用 default 值
    """
    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        default_val = match.group(3) if match.group(3) is not None else ""
        return os.environ.get(var_name, default_val)

    # 匹配 ${VAR} 或 ${VAR:-default}
    pattern = r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}"
    return re.sub(pattern, _replace, value)


def _process_config(obj):
    """Recursively process env var substitution in config values."""
    if isinstance(obj, str):
        return _substitute_env_vars(obj)
    elif isinstance(obj, dict):
        return {k: _process_config(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_process_config(item) for item in obj]
    return obj


def _patch_ollama_think_off():
    """Monkey-patch Mem0's OllamaLLM to disable thinking mode.

    gemma4:12b and similar models have a "thinking" mode that consumes
    tokens before generating actual content. Mem0 doesn't pass think=False,
    so we patch it here.
    """
    try:
        from mem0.llms.ollama import OllamaLLM
        original_generate = OllamaLLM.generate_response

        def patched_generate(self, messages, response_format=None, tools=None, tool_choice="auto", **kwargs):
            # Call original but intercept the chat call to add think=False
            original_client_chat = None
            if hasattr(self, 'client'):
                original_client_chat = self.client.chat
                def patched_chat(**params):
                    params['think'] = False  # top-level param, not in options
                    return original_client_chat(**params)
                self.client.chat = patched_chat
            try:
                return original_generate(self, messages, response_format, tools, tool_choice, **kwargs)
            finally:
                if original_client_chat and hasattr(self, 'client'):
                    self.client.chat = original_client_chat

        OllamaLLM.generate_response = patched_generate
    except (ImportError, AttributeError):
        pass


# Apply patch on import
_patch_ollama_think_off()


class Mem0Client:
    """Wraps mem0.Memory with config loading and convenience methods.

    所有记忆以 user_id="family" 分组，适用于家庭理财场景。
    """

    DEFAULT_USER_ID = "family"

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the Mem0 client.

        Args:
            config_path: Path to mem0.yaml. If None, uses the bundled config/mem0.yaml.
        """
        if config_path is None:
            config_path = _get_config_path()
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        # 递归替换环境变量
        self._config = _process_config(raw_config)

        # 提取 mem0 配置部分
        mem0_config = self._config.get("mem0", {})

        # 过滤掉空的 openai_base_url（兼容不使用自定义 base 的场景）
        for section in ("llm", "embedder"):
            cfg = mem0_config.get(section, {}).get("config", {})
            if not cfg.get("openai_base_url"):
                cfg.pop("openai_base_url", None)

        # 初始化 mem0.Memory
        if Memory is None:
            raise ImportError(
                "mem0ai is not installed. Run: pip install mem0ai"
            )
        try:
            self._memory = Memory.from_config(mem0_config)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Mem0: {e}")

        # Patch OllamaLLM 实例：禁用 thinking 模式
        # gemma4:12b 等模型的 thinking 会消耗所有 token，导致返回空内容
        llm = getattr(self._memory, 'llm', None)
        if llm and hasattr(llm, 'client') and hasattr(llm.client, 'chat'):
            _orig_chat = llm.client.chat

            def _patched_chat(**params):
                # 强制 think=False（gemma4/lfm2.5 等模型的 thinking 会消耗 token）
                params['think'] = False
                # gemma4:12b 在 format=json + 复杂 prompt 下会卡住，
                # 移除 format=json 让模型自由输出，再从文本中提取 JSON
                params.pop('format', None)
                r = _orig_chat(**params)
                # 如果返回的不是纯 JSON，尝试提取 JSON 部分
                msg = r.message if hasattr(r, 'message') else r.get('message', {})
                content = msg.get('content', '')
                if content and not content.strip().startswith('{'):
                    import re, json as _json
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        try:
                            parsed = _json.loads(match.group())
                            msg['content'] = _json.dumps(parsed)
                        except _json.JSONDecodeError:
                            pass
                return r

            llm.client.chat = _patched_chat

        # 从配置加载分类列表
        self.categories = self._config.get("categories", [])

    def add(self, content: str, category: str, metadata: Optional[dict] = None) -> dict:
        """Add a memory to the store.

        Args:
            content: The memory content (natural language).
            category: Memory category (e.g. investment_decision, market_event).
            metadata: Optional extra metadata fields.

        Returns:
            The Mem0 response dict with memory id and status.
        """
        meta = {
            "category": category,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            meta.update(metadata)

        result = self._memory.add(
            content,
            user_id=self.DEFAULT_USER_ID,
            metadata=meta,
        )
        return result

    def search(self, query: str, category: Optional[str] = None, limit: int = 10) -> list:
        """Search memories semantically.

        Args:
            query: Natural language search query.
            category: Optional category filter.
            limit: Maximum number of results.

        Returns:
            List of matching memory dicts with score, content, and metadata.
        """
        filters = {"user_id": self.DEFAULT_USER_ID}
        if category:
            filters["category"] = category

        results = self._memory.search(
            query,
            top_k=limit,
            filters=filters,
        )
        # Mem0 v2.0.7+ returns {"results": [...]} dict
        if isinstance(results, dict):
            return results.get("results", [])
        return results if results else []

    def get_all(self, category: Optional[str] = None, limit: int = 1000) -> list:
        """Get all memories, optionally filtered by category.

        Args:
            category: Optional category filter.
            limit: Maximum number of results (default 1000, Mem0 default is 20).

        Returns:
            List of memory dicts.
        """
        filters = {"user_id": self.DEFAULT_USER_ID}
        if category:
            filters["category"] = category

        results = self._memory.get_all(
            filters=filters,
            top_k=limit,
        )
        # Mem0 v2.0.7+ returns {"results": [...]} dict
        if isinstance(results, dict):
            return results.get("results", [])
        return results if results else []

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: The memory ID to delete.

        Returns:
            True if deleted successfully, False otherwise.
        """
        try:
            self._memory.delete(memory_id)
            return True
        except Exception:
            return False

    def update(self, memory_id: str, content: str) -> dict:
        """Update a memory's content.

        Args:
            memory_id: The memory ID to update.
            content: New content for the memory.

        Returns:
            The Mem0 response dict.
        """
        result = self._memory.update(memory_id, content)
        return result
