"""
DataHub 配置模块

提供配置文件路径解析和默认缓存目录。
配置文件优先从 ~/.config/maybe-finance/datahub/ 读取（用户自定义），
如果不存在则回退到包内默认模板。
"""

from pathlib import Path
import importlib.resources as _resources
import shutil


# 用户配置目录（持久化，安装不会覆盖）
_USER_CONFIG_DIR = Path.home() / ".config" / "maybe-finance" / "datahub"


def get_config_path(filename: str = "sources.yaml") -> Path:
    """获取配置文件路径

    优先级：
    1. ~/.config/maybe-finance/datahub/<filename> （用户自定义，持久化）
    2. 包内 datahub/config/<filename> （默认模板）

    首次运行时自动从包内模板复制到用户配置目录。
    """
    user_path = _USER_CONFIG_DIR / filename
    if user_path.exists():
        return user_path

    # 回退到包内默认
    ref = _resources.files("datahub.config").joinpath(filename)
    package_path = Path(str(ref))

    # 首次运行：从包内复制到用户配置目录
    if package_path.exists():
        _USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package_path, user_path)
        return user_path

    return package_path


def get_cache_dir() -> Path:
    """获取缓存目录（~/.datahub/cache），确保目录已创建"""
    cache_dir = Path.home() / ".datahub" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
