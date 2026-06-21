# Finance Read — Detailed Workflows

## Quick Financial Check

User: "我们家现在有多少钱" / "How are my finances?"

```bash
maybe snapshot --json
```

Summarize:
- Net worth and trend (vs last check if available in Mem0)
- Asset allocation breakdown
- Any concentration risks (single holding > 15%)
- Cash runway estimate

## Policy Drift Check

For scheduled checks or "is my portfolio healthy":

```bash
maybe balance-sheet --json
maybe holdings --json
```

Compare current allocation against `family_policy.yaml`:

**If HEALTHY:** one line — "Portfolio within target allocation. No action needed."

**If ACTION_NEEDED:**
```
⚠️ equity: 52% (target 45%, drift +7%)
⚠️ cash: 8% (target 15%, drift -7%)

Recommendation: Next contributions should favor cash deposits to restore balance.
```

## Monthly Report

```bash
maybe balance-sheet --json
maybe income-statement --start-date $(date -v-1m +%Y-%m-01) --json
maybe holdings --json
```

Compose:
- Net worth change vs last month
- Savings rate
- Top expense categories
- Portfolio status vs policy

## Historical Comparison

Combine Maybe (current) with Mem0 (baseline):

```bash
maybe snapshot --json          # Current data from Maybe
memory search -q "净资产 baseline"  # Historical context from Mem0
```

Report format: "当前净资产 $1,480,000，相比上次记录的 $1,457,274 增长了 +1.6%"

## Data Model Quick Reference

```
Family
├── Accounts (depository, investment, property, loan, credit_card, crypto)
│   ├── Balances (daily snapshots)
│   ├── Holdings (securities positions)
│   └── Entries (transactions, trades, valuations)
├── Net Worth = Assets - Liabilities
├── Categories (for transaction classification)
└── Exchange Rates (for multi-currency conversion)
```

Account types → asset classes:
- `depository`, `credit_card` → cash
- `investment` → equity
- `property` → real_estate
- `crypto` → alternative
- `loan` → liability
