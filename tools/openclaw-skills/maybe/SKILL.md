---
name: maybe
description: "Maybe Finance data queries: family net worth, account balances, portfolio holdings, allocation analysis, policy drift checks, income/expense reports."
homepage: https://github.com/maybe-finance/maybe
metadata:
  {
    "openclaw":
      {
        "emoji": "📊",
        "requires": { "bins": ["maybe"], "env": ["MAYBE_API_KEY"] },
        "install":
          [
            {
              "id": "pip-maybe-cli",
              "kind": "pip",
              "package": "maybe-cli",
              "source": "tools/maybe-cli",
              "bins": ["maybe"],
              "label": "Install maybe-cli (pip)",
            },
          ],
      },
  }
---

# Maybe Finance

Query family financial data from Maybe Finance. Read-only operations: snapshot, balance sheet, holdings, allocation analysis, policy drift detection, income/expense reports.

## When to Use

Use when:

- User asks about net worth, assets, liabilities
- User asks "how is my portfolio doing" or "what's my allocation"
- User asks about account balances or financial overview
- User asks "is my portfolio healthy" or "check my allocation"
- Scheduled policy drift check (via cron or standing order)
- User asks about income, expenses, or savings rate
- User asks about exchange rates or currency exposure

## When NOT to Use

Do not use when:

- User wants to UPDATE balances → use `maybe-reconcile` skill instead
- User wants to record a transaction → use `maybe-reconcile` skill instead
- User asks about stock prices or market news → use `yfinance` or web search
- User wants to create/edit/delete accounts → use Maybe web UI
- User asks for tax advice → out of scope, recommend a professional
- User asks for specific buy/sell recommendations → out of scope, we do allocation not stock picking

## Requirements

```bash
# Install maybe-cli
cd /path/to/maybe/tools/maybe-cli && pip install -e .

# Set API key (from Maybe Settings → API Keys)
export MAYBE_API_KEY="your-api-key"

# Optional: custom URL (defaults to http://localhost:3000)
export MAYBE_URL="http://localhost:3000"
```

Verify:

```bash
maybe accounts
maybe snapshot
```

## Hard Rules

- **Never recommend specific stocks or securities.** We analyze allocation, not pick stocks.
- **Never expose the API key** in responses or logs.
- **Always use `--json` flag** when processing data programmatically.
- **Report numbers in the family's base currency** (first entry in balance sheet).
- **If Maybe is unreachable**, report the error clearly — do not fabricate data.
- **Policy check results must be actionable.** If no drift, say "healthy" in one line. Don't pad.

## Command Reference

### Overview

```bash
maybe snapshot --json                    # Full financial overview
maybe balance-sheet --json               # Net worth + asset/liability breakdown
maybe accounts --json                    # All accounts with balances
```

### Portfolio

```bash
maybe holdings --json                    # Current holdings across accounts
maybe holdings --account-id <uuid>       # Holdings for one account
maybe trades --json                      # Trade history
maybe securities --json                  # Security metadata
maybe securities --search "VOO"          # Search by ticker/name
```

### Analysis

```bash
maybe income-statement --json            # Income/expense by category
maybe income-statement --start-date 2025-01-01 --end-date 2025-12-31
maybe exchange-rates --from USD --to CNY # Specific currency pair
maybe exchange-rates --json              # All recent rates
```

### Historical

```bash
maybe accounts --json | jq '.accounts[].id'   # Get account IDs first
# Then:
maybe balance-history --account-id <uuid> --interval monthly
```

### Holdings Management (Manual)

```bash
# Add a holding to an investment account
maybe holding add --account "长桥R" --ticker AAPL --qty 100 --price 150
maybe holding add --account "日本投资" --ticker 7203.T --qty 200
# If --price omitted, auto-fetched from Yahoo Finance

# Update a holding (change qty or price)
maybe holding update --account "长桥R" --ticker AAPL --qty 120
maybe holding update --account "长桥R" --ticker AAPL --price 160

# Delete a manual holding
maybe holding delete --account "长桥R" --ticker AAPL

# Sync all holding prices from Yahoo Finance
maybe holding sync
```

### Exchange Rate Management

```bash
# Set exchange rate (auto-fetched from Yahoo Finance if --rate omitted)
maybe holding rate --from USD --to CNY
maybe holding rate --from USD --to CNY --rate 7.24
maybe holding rate --from USD --to AUD --rate 1.55
```

## Workflows

### Quick Financial Check

User: "How are my finances?"

```bash
# 1. Get the full picture
maybe snapshot --json
```

Then summarize:
- Net worth and trend
- Asset allocation breakdown
- Any concentration risks
- Cash runway estimate (if income data available)

### Policy Drift Check

For scheduled checks or when user asks "is my portfolio healthy":

```bash
# 1. Get current allocation
maybe balance-sheet --json

# 2. Get holdings detail
maybe holdings --json

# 3. Run policy check (if script available)
python3 /path/to/tools/openclaw-skills/maybe/scripts/maybe_check.py --json
```

Read `family_policy.yaml` for target allocation. Compare current vs target.

**Report shape:**

```
Status: HEALTHY / ACTION_NEEDED

[if ACTION_NEEDED]
⚠ cash: 92% (target 15%, drift 77%)
⚠ equity: 1.3% (target 45%, drift 44%)

Recommendation: New cash flows should favor equity allocation
to gradually rebalance toward targets.
```

**If healthy:** one line only — "Portfolio within target allocation. No action needed."

### Monthly Report

User: "Give me a monthly summary"

```bash
# 1. Balance sheet snapshot
maybe balance-sheet --json

# 2. Income statement for the month
maybe income-statement --start-date $(date -v-1m +%Y-%m-01) --json

# 3. Holdings overview
maybe holdings --json
```

Compose a brief report:
- Net worth change vs last month
- Savings rate
- Top expense categories
- Portfolio status

### Setting Up Investment Holdings

When user wants to record specific stock/fund positions in an investment account:

**Step 1 — Show current state:**
```bash
maybe holdings --account-id <uuid> --json
maybe accounts --json
```

**Step 2 — Add holdings from user input:**
```bash
maybe holding add --account "长桥R" --ticker AAPL --qty 100 --price 150
maybe holding add --account "长桥R" --ticker BABA --qty 50 --price 80
```

**Step 3 — Verify and report:**
```bash
maybe holdings --json
```

Present the portfolio composition:
```
✅ Portfolio updated for 长桥R:
  AAPL:  100 shares × $150.00 = $15,000 (14.3%)
  BABA:  50 shares × $80.00  = $4,000  (3.8%)
  Cash:  $86,000              (81.9%)
  Total: $105,000
```

### Syncing Prices

When user asks to update stock prices:
```bash
maybe holding sync    # Fetches latest from Yahoo Finance
```

### Setting Exchange Rates

When user mentions exchange rates:
```bash
maybe holding rate --from USD --to CNY    # Auto-fetch
maybe holding rate --from USD --to JPY    # Auto-fetch
```

## Error Handling

| Error | Cause | Action |
|---|---|---|
| Connection refused | Maybe not running | "Maybe is not running. Start with: `docker compose up -d`" |
| 401 Unauthorized | Invalid API key | "API key invalid. Generate a new one in Maybe → Settings → API Keys" |
| Empty results | No data yet | "No holdings found. Add trades in Maybe first, or use `maybe-reconcile` to update balances." |
| Timeout | Maybe overloaded | Retry once after 5 seconds. If still failing, report the issue. |

## Data Model Quick Reference

```
Family
├── Accounts (depository, investment, property, loan, credit_card, crypto, vehicle, other)
│   ├── Balances (daily snapshots)
│   ├── Holdings (securities positions)
│   └── Entries (transactions, trades, valuations)
├── Net Worth = Assets - Liabilities
├── Categories (for transaction classification)
└── Exchange Rates (for multi-currency conversion)
```

Account types map to asset classes:
- `depository`, `credit_card` → cash
- `investment` → equity
- `property` → real_estate
- `crypto` → alternative
- `loan` → liability
