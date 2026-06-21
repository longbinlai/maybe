---
name: finance-read
description: "Query family financial data: net worth, account balances, holdings, allocation, income/expenses. Read-only, never modifies data."
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

# Finance Read

Query family financial data from Maybe Finance. Read-only — this skill never modifies data.

## Hard Rules

- **NEVER fabricate financial data.** All numbers must come from `maybe` CLI output.
- **NEVER trust Mem0 for current balances or prices.** Mem0 stores historical context, not real-time data.
- **Always use `--json`** for programmatic processing.
- **Report in family's base currency** (first entry in balance sheet).
- **If Maybe is unreachable**, report the error. Do not guess.

## When NOT to Use

- User wants to UPDATE balances or record transactions → use `finance-write`
- User asks about investment decision reasoning or lessons → use `finance-memory`
- User asks about stock prices or market news → use `yfinance`
- User asks about macroeconomic trends → use `macro-info-collector`

## Commands

### Overview

```bash
maybe snapshot --json
maybe balance-sheet --json
maybe accounts --json
```

### Portfolio

```bash
maybe holdings --json
maybe holdings --account-id <uuid> --json
maybe trades --json
maybe securities --json
```

### Analysis

```bash
maybe income-statement --json
maybe income-statement --start-date 2026-01-01 --end-date 2026-06-30 --json
maybe exchange-rates --from USD --to CNY
maybe exchange-rates --json
```

### Holdings (Read-only)

```bash
maybe holdings --json              # All holdings
maybe holdings --account-id <uuid> # One account's holdings
```

## Workflows

### Quick Financial Check

1. Run `maybe snapshot --json`
2. Summarize: net worth, allocation breakdown, any concentration risks

### Policy Drift Check

1. Run `maybe balance-sheet --json` + `maybe holdings --json`
2. Compare current allocation against `{baseDir}/references/family_policy.yaml`
3. Report: HEALTHY (one line) or ACTION_NEEDED (list drifts with actionable suggestions)

### Monthly Report

1. `maybe balance-sheet --json`
2. `maybe income-statement --start-date <month-start> --json`
3. `maybe holdings --json`
4. Compose: net worth change, savings rate, top expenses, portfolio status

For detailed workflow examples, see `{baseDir}/references/workflows.md`.
