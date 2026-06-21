#!/usr/bin/env python3
"""yf - Yahoo Finance CLI wrapper for OpenClaw skill."""

import sys
import click
import yfinance as yf
from datetime import datetime


@click.group()
def cli():
    """Yahoo Finance market data CLI."""
    pass


@cli.command()
@click.argument("tickers", nargs=-1, required=True)
@click.option("--period", default="5d", help="Data period (1d,5d,1mo,3mo,6mo,1y,2y,5y,max)")
def quote(tickers, period):
    """Get current quotes for tickers."""
    for symbol in tickers:
        try:
            t = yf.Ticker(symbol)
            h = t.history(period=period)
            if h.empty:
                click.echo(f"{symbol}: no data")
                continue
            latest = h.iloc[-1]
            prev = h.iloc[-2] if len(h) > 1 else latest
            price = latest["Close"]
            change = price - prev["Close"]
            pct = (change / prev["Close"] * 100) if prev["Close"] else 0
            click.echo(f"{symbol:<12s} {price:>12.2f}  {change:>+8.2f} ({pct:>+.2f}%)")
        except Exception as e:
            click.echo(f"{symbol}: error - {e}")


@cli.command()
@click.argument("ticker")
@click.option("--period", default="1y", help="Data period")
@click.option("--interval", default="1mo", help="Data interval (1h,1d,1wk,1mo)")
def history(ticker, period, interval):
    """Get historical OHLC data."""
    t = yf.Ticker(ticker)
    h = t.history(period=period, interval=interval)
    if h.empty:
        click.echo(f"No data for {ticker}")
        return
    click.echo(f"{'Date':<12s} {'Open':>10s} {'High':>10s} {'Low':>10s} {'Close':>10s} {'Volume':>12s}")
    click.echo("-" * 68)
    for idx, row in h.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        click.echo(
            f"{date_str:<12s} {row['Open']:>10.2f} {row['High']:>10.2f} "
            f"{row['Low']:>10.2f} {row['Close']:>10.2f} {int(row['Volume']):>12,d}"
        )


@cli.command()
@click.argument("ticker")
def info(ticker):
    """Get detailed company/asset info."""
    t = yf.Ticker(ticker)
    i = t.info
    fields = [
        ("Name", "longName", "shortName"),
        ("Sector", "sector",),
        ("Industry", "industry",),
        ("Market Cap", "marketCap",),
        ("P/E Ratio", "trailingPE",),
        ("Forward P/E", "forwardPE",),
        ("Dividend Yield", "dividendYield",),
        ("52W High", "fiftyTwoWeekHigh",),
        ("52W Low", "fiftyTwoWeekLow",),
        ("Avg Volume", "averageVolume",),
        ("Beta", "beta",),
    ]
    for field_def in fields:
        label = field_def[0]
        for key in field_def[1:]:
            val = i.get(key)
            if val is not None:
                if "Cap" in label or "Volume" in label:
                    if val >= 1e12:
                        val = f"${val/1e12:.2f}T"
                    elif val >= 1e9:
                        val = f"${val/1e9:.2f}B"
                    elif val >= 1e6:
                        val = f"${val/1e6:.2f}M"
                    else:
                        val = f"{val:,.0f}"
                elif "Yield" in label:
                    val = f"{val*100:.2f}%"
                elif isinstance(val, float):
                    val = f"{val:.2f}"
                click.echo(f"  {label:<16s} {val}")
                break


@cli.command()
@click.argument("pairs", nargs=-1, required=True)
def fx(pairs):
    """Get exchange rates (e.g. USDCNY EURUSD)."""
    for pair in pairs:
        try:
            symbol = f"{pair}=X" if "=" not in pair else pair
            t = yf.Ticker(symbol)
            h = t.history(period="5d")
            if h.empty:
                click.echo(f"{pair}: no data")
                continue
            latest = h.iloc[-1]
            prev = h.iloc[-2] if len(h) > 1 else latest
            rate = latest["Close"]
            change = rate - prev["Close"]
            pct = (change / prev["Close"] * 100) if prev["Close"] else 0
            click.echo(f"{pair:<10s} {rate:>10.4f}  {change:>+8.4f} ({pct:>+.2f}%)")
        except Exception as e:
            click.echo(f"{pair}: error - {e}")


@cli.command()
@click.argument("ticker")
@click.option("--period", default="1mo", help="Period (1mo,3mo,6mo,1y)")
def performance(ticker, period):
    """Get performance metrics for a ticker."""
    t = yf.Ticker(ticker)
    h = t.history(period=period)
    if h.empty:
        click.echo(f"No data for {ticker}")
        return
    start = h.iloc[0]["Close"]
    end = h.iloc[-1]["Close"]
    change = end - start
    pct = (change / start * 100) if start else 0
    high = h["High"].max()
    low = h["Low"].min()
    click.echo(f"  Ticker:   {ticker}")
    click.echo(f"  Period:   {period}")
    click.echo(f"  Start:    {start:.2f}")
    click.echo(f"  End:      {end:.2f}")
    click.echo(f"  Change:   {change:+.2f} ({pct:+.2f}%)")
    click.echo(f"  High:     {high:.2f}")
    click.echo(f"  Low:      {low:.2f}")


if __name__ == "__main__":
    cli()
