"""
Yahoo Finance 数据源实现

通过 yfinance 获取股票、汇率、商品价格等数据
"""

from typing import List
from datetime import datetime, timedelta
import yfinance as yf

from ..core.base_source import BaseDataSource, DataSourceResult, DataItem


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
        """获取价格数据"""
        items = []
        
        for ticker_symbol in self.tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period=self.period, interval=self.interval)
                
                if hist.empty:
                    continue
                
                # 获取最新价格
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest
                
                price = latest['Close']
                prev_price = prev['Close']
                change = price - prev_price
                change_pct = (change / prev_price * 100) if prev_price != 0 else 0
                
                # 创建数据项
                title = f"{ticker_symbol}: ${price:.2f} ({change_pct:+.2f}%)"
                content = f"""
收盘价: ${price:.2f}
涨跌: ${change:+.2f} ({change_pct:+.2f}%)
开盘: ${latest['Open']:.2f}
最高: ${latest['High']:.2f}
最低: ${latest['Low']:.2f}
成交量: {latest['Volume']:,.0f}
"""
                
                item_id = DataItem.generate_id(self.name, ticker_symbol, str(latest.name))
                
                items.append(DataItem(
                    id=item_id,
                    source=self.name,
                    category=self.category,
                    title=title,
                    content=content,
                    url=f"https://finance.yahoo.com/quote/{ticker_symbol}",
                    published=latest.name.to_pydatetime(),
                    metadata={
                        'ticker': ticker_symbol,
                        'price': float(price),
                        'change': float(change),
                        'change_pct': float(change_pct),
                        'volume': int(latest['Volume']),
                    }
                ))
            
            except Exception as e:
                print(f"⚠️  获取 {ticker_symbol} 失败: {str(e)}")
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
        """获取新闻数据"""
        items = []
        
        for ticker_symbol in self.tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                news = ticker.news
                
                for article in news[:10]:  # 每个ticker最多10条新闻
                    title = article.get('title', '').strip()
                    if not title:
                        continue
                    
                    link = article.get('link', '')
                    publisher = article.get('publisher', 'Unknown')
                    
                    # 解析发布时间
                    pub_time = article.get('providerPublishTime')
                    if pub_time:
                        published = datetime.fromtimestamp(pub_time)
                    else:
                        published = datetime.now()
                    
                    # 创建数据项
                    item_id = DataItem.generate_id(self.name, link, title)
                    
                    items.append(DataItem(
                        id=item_id,
                        source=self.name,
                        category=self.category,
                        title=f"[{ticker_symbol}] {title}",
                        content=f"来源: {publisher}",
                        url=link,
                        published=published,
                        metadata={
                            'ticker': ticker_symbol,
                            'publisher': publisher,
                        }
                    ))
            
            except Exception as e:
                print(f"⚠️  获取 {ticker_symbol} 新闻失败: {str(e)}")
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
    
    def _fetch_info(self) -> DataSourceResult:
        """获取详细信息"""
        items = []
        
        for ticker_symbol in self.tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info
                
                # 提取关键信息
                name = info.get('shortName', ticker_symbol)
                price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                market_cap = info.get('marketCap', 0)
                pe_ratio = info.get('trailingPE', 0)
                dividend_yield = info.get('dividendYield', 0)
                
                # 格式化内容
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
                print(f"⚠️  获取 {ticker_symbol} 信息失败: {str(e)}")
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
