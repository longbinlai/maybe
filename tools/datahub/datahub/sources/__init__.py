"""
DataHub Sources 模块

使用延迟导入避免不必要的依赖加载
"""

__all__ = [
    'RSSSource',
    'YFinanceSource',
    'NewsAPISource',
]

def __getattr__(name):
    """延迟导入数据源类"""
    if name == 'RSSSource':
        from .rss_source import RSSSource
        return RSSSource
    elif name == 'YFinanceSource':
        from .yfinance_source import YFinanceSource
        return YFinanceSource
    elif name == 'NewsAPISource':
        from .newsapi_source import NewsAPISource
        return NewsAPISource
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
