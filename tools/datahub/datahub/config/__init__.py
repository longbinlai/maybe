"""
DataHub 配置模块

提供配置文件路径解析和默认缓存目录。
"""

from pathlib import Path
import importlib.resources as _resources


def get_config_path(filename: str = "sources.yaml") -> Path:
    """获取包内配置文件的路径

    使用 importlib.resources 定位打包在 datahub 内的配置文件，
    无论包以 editable 还是 site-packages 方式安装都能正确找到。
    """
    ref = _resources.files("datahub.config").joinpath(filename)
    return Path(str(ref))


def get_cache_dir() -> Path:
    """获取缓存目录（~/.datahub/cache），确保目录已创建"""
    cache_dir = Path.home() / ".datahub" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
