---
name: yfinance
description: "Market data queries: stock quotes, historical prices, exchange rates, index performance. Use for investment analysis and market monitoring."
metadata:
  {
    "openclaw":
      {
        "emoji": "📈",
        "requires": { "bins": ["yf"], "env": [] },
      },
  }
---

# YFinance Market Data

Fetch real-time and historical market data for investment analysis.

## When to Use

- User asks about stock prices, quotes, or performance
- User wants historical price data for securities
- User asks about exchange rates (USD/CNY, etc.)
- User wants to check index performance (S&P 500, Hang Seng, etc.)
- User asks for detailed company info (P/E ratio, market cap, dividends)
- Monitoring market movements for portfolio analysis

## Commands

### Get Current Quotes

```bash
# Single ticker
yf quote AAPL

# Multiple tickers
yf quote AAPL MSFT GOOGL

# With specific period
yf quote AAPL --period 5d
```

### Historical Data

```bash
# 1 year monthly data
yf history AAPL --period 1y --interval 1mo

# 3 months daily data
yf history AAPL --period 3mo --interval 1d

# Recent 5 days hourly
yf history AAPL --period 5d --interval 1h
```

### Detailed Info

```bash
yf info AAPL
```

Returns: sector, industry, market cap, P/E ratio, dividend yield, 52-week range, etc.

### Exchange Rates

```bash
# USD to CNY
yf fx USDCNY

# Multiple pairs
yf fx USDCNY EURUSD GBPJPY
```

### Index Performance

```bash
# S&P 500
yf performance ^GSPC --period 1mo

# Hang Seng
yf performance ^HSI --period 3mo

# Shanghai Composite
yf performance 000001.SS --period 1y
```

## Common Tickers

**US Indices:**
- `^GSPC` - S&P 500
- `^DJI` - Dow Jones
- `^IXIC` - NASDAQ

**China/HK Indices:**
- `000001.SS` - Shanghai Composite
- `399001.SZ` - Shenzhen Component
- `^HSI` - Hang Seng

**Major Stocks:**
- `AAPL` - Apple
- `MSFT` - Microsoft
- `GOOGL` - Alphabet
- `TSLA` - Tesla
- `9988.HK` - Alibaba (HK)
- `BABA` - Alibaba (US)

**ETFs:**
- `SPY` - S&P 500 ETF
- `QQQ` - NASDAQ 100 ETF
- `VTI` - Total Stock Market ETF

## Example Workflows

### Check Portfolio Performance vs Benchmark

```bash
# Get index performance
yf performance ^GSPC --period 1mo

# Then compare with user's portfolio returns
maybe holdings
```

### Monitor Exchange Rates for Multi-Currency Portfolio

```bash
# Check major FX pairs
yf fx USDCNY USDJPY EURUSD
```

### Research a Stock Before Adding to Portfolio

```bash
# Get basic info
yf info AAPL

# Check recent performance
yf history AAPL --period 3mo --interval 1wk

# Compare with index
yf performance ^GSPC --period 3mo
```

## Output Format

All commands output structured text tables for easy parsing:

- **quote**: Ticker, price, change, change %
- **history**: Date, OHLC, Volume
- **info**: Key metrics (market cap, P/E, etc.)
- **fx**: Pair, rate, change, change %
- **performance**: Start, end, change, high, low

## Notes

- Data source: Yahoo Finance (free, no API key needed)
- Real-time quotes have 15-minute delay for some exchanges
- Historical data available for 20+ years for major stocks
- Exchange rates update daily
- Use `--period` and `--interval` to control data granularity
