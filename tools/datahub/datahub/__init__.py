"""
DataHub - 统一数据源管理模块

设计理念：
1. 插件式数据源 - 每种数据源实现统一接口
2. 配置驱动 - 通过YAML配置数据源
3. 自动验证 - 每个数据源自带验证逻辑
4. 缓存机制 - 避免重复请求
5. 错误处理 - 单个数据源失败不影响整体
"""

__version__ = '1.0.0'

# 延迟导入，避免导入时加载重型依赖
def __getattr__(name):
    if name == 'BaseDataSource':
        from .core.base_source import BaseDataSource
        return BaseDataSource
    elif name == 'DataSourceResult':
        from .core.base_source import DataSourceResult
        return DataSourceResult
    elif name == 'SourceRegistry':
        from .core.source_registry import SourceRegistry
        return SourceRegistry
    elif name == 'RSSSource':
        from .sources.rss_source import RSSSource
        return RSSSource
    elif name == 'YFinanceSource':
        from .sources.yfinance_source import YFinanceSource
        return YFinanceSource
    elif name == 'NewsAPISource':
        from .sources.newsapi_source import NewsAPISource
        return NewsAPISource
    elif name == 'HistoryStore':
        from .core.history_store import HistoryStore
        return HistoryStore
    elif name == 'get_config_path':
        from .config import get_config_path
        return get_config_path
    elif name == 'get_cache_dir':
        from .config import get_cache_dir
        return get_cache_dir
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'BaseDataSource',
    'DataSourceResult',
    'SourceRegistry',
    'RSSSource',
    'YFinanceSource',
    'NewsAPISource',
    'HistoryStore',
    'get_config_path',
    'get_cache_dir',
]
