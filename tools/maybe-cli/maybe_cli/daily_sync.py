#!/usr/bin/env python3
"""
Daily price and exchange rate sync.
Fetches prices from Yahoo Finance outside Docker, then pushes to Maybe API.
"""

import os
import sys
import json
import yfinance as yf

from .client import MaybeClient


def sync_holding_prices(client: MaybeClient, dry_run: bool = False) -> dict:
    """Sync holding prices from Yahoo Finance."""
    results = {"updated": [], "skipped": [], "errors": []}

    holdings = client.holdings().get("holdings", [])
    if not holdings:
        results["skipped"].append({"reason": "no holdings"})
        return results

    # Get unique tickers
    seen_tickers = set()
    for h in holdings:
        ticker = h.get("security", {}).get("ticker", "")
        if ticker and ticker not in seen_tickers:
            seen_tickers.add(ticker)

    for ticker in sorted(seen_tickers):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if hist.empty:
                results["skipped"].append({"ticker": ticker, "reason": "no data"})
                continue

            new_price = float(hist["Close"].iloc[-1])
            old_price = None

            # Find current holding for this ticker
            for h in holdings:
                if h.get("security", {}).get("ticker") == ticker:
                    old_price = h.get("price")
                    holding_id = h.get("id")

                    if dry_run:
                        results["updated"].append({
                            "ticker": ticker,
                            "old_price": old_price,
                            "new_price": round(new_price, 2),
                            "dry_run": True,
                        })
                    else:
                        client.update_holding(
                            holding_id=holding_id,
                            price=round(new_price, 2),
                        )
                        results["updated"].append({
                            "ticker": ticker,
                            "old_price": old_price,
                            "new_price": round(new_price, 2),
                        })
                    break

        except Exception as e:
            results["errors"].append({"ticker": ticker, "error": str(e)})

    return results


def sync_exchange_rates(client: MaybeClient, dry_run: bool = False) -> dict:
    """Sync exchange rates from Yahoo Finance."""
    results = {"updated": [], "skipped": [], "errors": []}

    pairs = [
        ("USD", "CNY"),
        ("USD", "AUD"),
    ]

    for from_c, to_c in pairs:
        try:
            ticker = f"{from_c}{to_c}=X"
            data = yf.Ticker(ticker)
            hist = data.history(period="5d")
            if hist.empty:
                results["skipped"].append({"pair": f"{from_c}/{to_c}", "reason": "no data"})
                continue

            rate = float(hist["Close"].iloc[-1])

            if dry_run:
                results["updated"].append({
                    "pair": f"{from_c}/{to_c}",
                    "rate": round(rate, 4),
                    "dry_run": True,
                })
            else:
                client.create_exchange_rate(
                    from_currency=from_c,
                    to_currency=to_c,
                    rate=round(rate, 4),
                )
                results["updated"].append({
                    "pair": f"{from_c}/{to_c}",
                    "rate": round(rate, 4),
                })

        except Exception as e:
            results["errors"].append({"pair": f"{from_c}/{to_c}", "error": str(e)})

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Daily price and exchange rate sync")
    parser.add_argument("--api-key", help="Maybe API key (or set MAYBE_API_KEY)")
    parser.add_argument("--url", help="Maybe API URL (or set MAYBE_URL)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("MAYBE_API_KEY")
    api_url = args.url or os.environ.get("MAYBE_URL", "http://localhost:3000")

    if not api_key:
        print("Error: MAYBE_API_KEY not set. Export it or pass --api-key.", file=sys.stderr)
        sys.exit(1)

    client = MaybeClient(base_url=api_url, api_key=api_key)

    # Sync holdings
    price_results = sync_holding_prices(client, dry_run=args.dry_run)

    # Sync exchange rates
    rate_results = sync_exchange_rates(client, dry_run=args.dry_run)

    if args.json:
        output = {"prices": price_results, "rates": rate_results}
        print(json.dumps(output, indent=2))
    else:
        print("=== 持仓价格同步 ===")
        if price_results["updated"]:
            for u in price_results["updated"]:
                old = f"${u['old_price']:.2f}" if u["old_price"] else "N/A"
                print(f"  ✅ {u['ticker']}: {old} → ${u['new_price']:.2f}")
        if price_results["skipped"]:
            for s in price_results["skipped"]:
                print(f"  ⏭️  {s.get('ticker', s.get('reason', '?'))}: {s.get('reason', 'skipped')}")
        if price_results["errors"]:
            for e in price_results["errors"]:
                print(f"  ❌ {e.get('ticker', '?')}: {e.get('error', 'unknown')}")
        if not price_results["updated"] and not price_results["skipped"] and not price_results["errors"]:
            print("  (no holdings)")

        print()
        print("=== 汇率同步 ===")
        if rate_results["updated"]:
            for u in rate_results["updated"]:
                print(f"  ✅ {u['pair']}: {u['rate']}")
        if rate_results["skipped"]:
            for s in rate_results["skipped"]:
                print(f"  ⏭️  {s.get('pair', '?')}: {s.get('reason', 'skipped')}")
        if rate_results["errors"]:
            for e in rate_results["errors"]:
                print(f"  ❌ {e.get('pair', '?')}: {e.get('error', 'unknown')}")


if __name__ == "__main__":
    main()
