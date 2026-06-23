"""
Yahoo Finance 数据源实现

通过 yfinance 获取股票、汇率、商品价格等数据

限速策略：
- _fetch_prices: 使用 yf.download() 批量获取（1 个 HTTP 请求代替 N 个）
- _fetch_news / _fetch_info: 逐 ticker 请求，加延迟 + 限速重试
"""

from typing import List
from datetime import datetime, timedelta
import sys
import time
import yfinance as yf

from ..core.base_source import BaseDataSource, DataSourceResult, DataItem

# 每次请求之间的最小间隔（秒），避免触发 Yahoo 限速
_REQUEST_DELAY = 1.0
_MAX_RETRIES = 2


def _log(msg: str):
    """进度信息输出到 stderr（不污染 stdout）"""
    print(msg, file=sys.stderr)


def _retry_on_rate_limit(func, max_retries=_MAX_RETRIES):
    """遇到 Too Many Requests 时指数退避重试"""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries and "Too Many Requests" in str(e):
                wait = (2 ** attempt) * 3
                _log(f"⏳ 限速等待 {wait}s...")
                time.sleep(wait)
                continue
            raise


class YFinanceSource(BaseDataSource):
    """Yahoo Finance 数据源"""

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.tickers = config.get('tickers', [])
        self.data_type = config.get('data_type', 'price')  # price, news, info
        self.period = config.get('period', '5d')  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        self.interval = config.get('interval', '1d')  # 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo

    def fetch(self) -> DataSourceResult:
        """获取 Yahoo Finance 数据"""
        try:
            if self.data_type == 'price':
                return self._fetch_prices()
            elif self.data_type == 'news':
                return self._fetch_news()
            elif self.data_type == 'info':
                return self._fetch_info()
            else:
                return DataSourceResult(
                    source_name=self.name,
                    source_type='yfinance',
                    category=self.category,
                    status='failed',
                    error=f'未知数据类型: {self.data_type}'
                )

        except Exception as e:
            return DataSourceResult(
                source_name=self.name,
                source_type='yfinance',
                category=self.category,
                status='failed',
                error=str(e)
            )

    def _fetch_prices(self) -> DataSourceResult:
        """批量获取价格数据（1 个 HTTP 请求获取所有 ticker）"""
        if not self.tickers:
            return DataSourceResult(
                source_name=self.name,
                source_type='yfinance',
                category=self.category,
                status='degraded',
                error='No tickers configured'
            )

        items = []

        # 用 yf.download() 一次性批量获取所有 ticker 的历史数据
        # auto_adjust=True 返回调整后价格，progress=False 不打印进度条
        df = _retry_on_rate_limit(
            lambda: yf.download(
                self.tickers,
                period=self.period,
                interval=self.interval,
                group_by='ticker',
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        )

        if df is None or df.empty:
            return DataSourceResult(
                source_name=self.name,
                source_type='yfinance',
                category=self.category,
                status='degraded',
                error='yf.download returned empty data'
            )

        is_multi = isinstance(df.columns, __import__('pandas').MultiIndex)

        for ticker_symbol in self.tickers:
            try:
                # 提取单个 ticker 的 OHLCV 数据
                if is_multi and ticker_symbol in df.columns.get_level_values(0):
                    ticker_df = df[ticker_symbol].dropna(how='all')
                elif not is_multi:
                    ticker_df = df.dropna(how='all')
                else:
                    continue

                if ticker_df.empty or len(ticker_df) < 1:
                    continue

                latest = ticker_df.iloc[-1]
                prev = ticker_df.iloc[-2] if len(ticker_df) > 1 else latest

                price = latest['Close']
                prev_price = prev['Close']

                # 跳过 NaN 值（某些 ticker 如 000001.SS 可能返回 NaN）
                import math
                if price is None or (isinstance(price, float) and math.isnan(price)):
                    _log(f"⚠️  {ticker_symbol}: 价格为 NaN，跳过")
                    continue

                change = price - prev_price
                change_pct = (change / prev_price * 100) if prev_price != 0 else 0

                title = f"{ticker_symbol}: ${price:.2f} ({change_pct:+.2f}%)"
                content = f"""
收盘价: ${price:.2f}
涨跌: ${change:+.2f} ({change_pct:+.2f}%)
开盘: ${latest['Open']:.2f}
最高: ${latest['High']:.2f}
最低: ${latest['Low']:.2f}
成交量: {latest['Volume']:,.0f}
"""

                # 提取日期
                idx = ticker_df.index[-1]
                try:
                    pub_date = idx.to_pydatetime()
                except Exception:
                    pub_date = datetime.now()

                item_id = DataItem.generate_id(self.name, ticker_symbol, str(idx))

                items.append(DataItem(
                    id=item_id,
                    source=self.name,
                    category=self.category,
                    title=title,
                    content=content,
                    url=f"https://finance.yahoo.com/quote/{ticker_symbol}",
                    published=pub_date,
                    metadata={
                        'ticker': ticker_symbol,
                        'price': float(price),
                        'change': float(change),
                        'change_pct': float(change_pct),
                        'volume': int(latest['Volume']),
                    }
                ))

            except Exception as e:
                _log(f"⚠️  解析 {ticker_symbol} 数据失败: {str(e)}")
                continue

        # 验证数据质量
        validation = self.validate(items)

        # 确定状态
        if validation.is_valid:
            status = 'success'
        elif validation.score >= 50:
            status = 'degraded'
        else:
            status = 'failed'

        return DataSourceResult(
            source_name=self.name,
            source_type='yfinance',
            category=self.category,
            status=status,
            items=items,
            validation=validation
        )

    def _fetch_news(self) -> DataSourceResult:
        """获取新闻数据（逐 ticker，带延迟和限速重试）"""
        items = []

        for i, ticker_symbol in enumerate(self.tickers):
            # ticker 之间加延迟
            if i > 0:
                time.sleep(_REQUEST_DELAY)

            try:
                news = _retry_on_rate_limit(lambda s=ticker_symbol: yf.Ticker(s).news)

                for article in (news or [])[:10]:  # 每个 ticker 最多 10 条
                    # yfinance API 格式变更：标题等内容嵌套在 content 下
                    content_obj = article.get('content', article)

                    title = content_obj.get('title', '').strip()
                    if not title:
                        continue

                    # URL: 优先 canonicalUrl，其次 clickThroughUrl
                    canonical = content_obj.get('canonicalUrl', {})
                    click_url = content_obj.get('clickThroughUrl', {})
                    link = (canonical or {}).get('url', '') or (click_url or {}).get('url', '')

                    # 发布者
                    provider = content_obj.get('provider', {})
                    publisher = provider.get('displayName', 'Unknown')

                    # 发布时间: 优先 pubDate (ISO 8601)，其次 providerPublishTime (Unix timestamp)
                    pub_date_str = content_obj.get('pubDate')
                    if pub_date_str:
                        try:
                            published = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                            published = published.replace(tzinfo=None)
                        except ValueError:
                            published = datetime.now()
                    else:
                        pub_time = article.get('providerPublishTime')
                        published = datetime.fromtimestamp(pub_time) if pub_time else datetime.now()

                    # 摘要
                    summary = content_obj.get('summary', '') or content_obj.get('description', '')

                    item_id = DataItem.generate_id(self.name, link or title, title)

                    items.append(DataItem(
                        id=item_id,
                        source=self.name,
                        category=self.category,
                        title=f"[{ticker_symbol}] {title}",
                        content=f"来源: {publisher}" + (f"\n摘要: {summary}" if summary else ""),
                        url=link,
                        published=published,
                        metadata={
                            'ticker': ticker_symbol,
                            'publisher': publisher,
                        }
                    ))

            except Exception as e:
                _log(f"⚠️  获取 {ticker_symbol} 新闻失败: {str(e)}")
                continue

        validation = self.validate(items)

        if validation.is_valid:
            status = 'success'
        elif validation.score >= 50:
            status = 'degraded'
        else:
            status = 'failed'

        return DataSourceResult(
            source_name=self.name,
            source_type='yfinance',
            category=self.category,
            status=status,
            items=items,
            validation=validation
        )

    def _fetch_info(self) -> DataSourceResult:
        """获取详细信息（逐 ticker，带延迟和限速重试）"""
        items = []

        for i, ticker_symbol in enumerate(self.tickers):
            if i > 0:
                time.sleep(_REQUEST_DELAY)

            try:
                info = _retry_on_rate_limit(lambda s=ticker_symbol: yf.Ticker(s).info)

                name = info.get('shortName', ticker_symbol)
                price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                market_cap = info.get('marketCap', 0)
                pe_ratio = info.get('trailingPE', 0)
                dividend_yield = info.get('dividendYield', 0)

                title = f"{name} ({ticker_symbol})"
                content = f"""
当前价格: ${price:.2f}
市值: ${market_cap/1e9:.2f}B
市盈率: {pe_ratio:.2f}
股息率: {dividend_yield*100:.2f}%
"""

                item_id = DataItem.generate_id(self.name, ticker_symbol, 'info')

                items.append(DataItem(
                    id=item_id,
                    source=self.name,
                    category=self.category,
                    title=title,
                    content=content,
                    url=f"https://finance.yahoo.com/quote/{ticker_symbol}",
                    published=datetime.now(),
                    metadata={
                        'ticker': ticker_symbol,
                        'price': price,
                        'market_cap': market_cap,
                        'pe_ratio': pe_ratio,
                        'dividend_yield': dividend_yield,
                    }
                ))

            except Exception as e:
                _log(f"⚠️  获取 {ticker_symbol} 信息失败: {str(e)}")
                continue

        validation = self.validate(items)

        if validation.is_valid:
            status = 'success'
        elif validation.score >= 50:
            status = 'degraded'
        else:
            status = 'failed'

        return DataSourceResult(
            source_name=self.name,
            source_type='yfinance',
            category=self.category,
            status=status,
            items=items,
            validation=validation
        )
