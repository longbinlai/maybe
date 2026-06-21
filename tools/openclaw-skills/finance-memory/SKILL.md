---
name: finance-memory
description: "Manage investment decision memories: record reasoning and lessons, generate weekly/monthly portfolio reviews."
metadata:
  {
    "openclaw":
      {
        "emoji": "🧠",
        "requires": { "bins": ["maybe", "memory"], "env": ["MAYBE_API_KEY"] },
        "install":
          [
            {
              "id": "pip-mem0-memory",
              "kind": "pip",
              "package": "mem0-memory",
              "source": "tools/mem0-memory",
              "bins": ["memory"],
              "label": "Install mem0-memory CLI (pip)",
            },
          ],
      },
  }
---

# Finance Memory

Manage investment decision memories using Mem0. Stores subjective wisdom that Maybe Finance cannot capture: decision reasoning, lessons learned, market views, investment style, and family goals.

## Hard Rules

- **NEVER store objective financial data in Mem0.** Balances, holdings, prices, net worth — all belong in Maybe Finance.
- **NEVER trust Mem0 for current financial data.** Always query Maybe for real-time numbers.
- **Mem0 = WHY and HOW, Maybe = WHAT and HOW MUCH.**

## When NOT to Use

- User wants to query current balances or holdings → use `finance-read`
- User wants to record a transaction or update balance → use `finance-write`
- User asks about stock prices → use `yfinance`

## Memory Categories

| Category | What to Store |
|----------|--------------|
| `investment_decision` | WHY we bought/sold, market context, expected outcome, confidence level |
| `lesson_learned` | What worked, what didn't, actionable takeaways |
| `market_view` | Opinions on markets, sectors, trends |
| `investment_style` | Risk tolerance, preferences, behavioral patterns |
| `family_goal` | Long-term objectives and milestones |
| `weekly_review` | Weekly portfolio review and analysis |
| `monthly_review` | Monthly deep analysis and strategy adjustment |

For category details and deprecated categories, see `{baseDir}/references/memory-categories.md`.

## Commands

```bash
# Add memory
memory add -c <category> --content "<text>" -m key=value

# Search memories
memory search -q "<query>" [-c <category>] [-n <limit>]

# List memories
memory list [-c <category>]

# Delete memory
memory delete <memory_id>

# Statistics
memory stats
```

## Workflows

### Record Investment Decision

When user describes a buy/sell decision, capture the reasoning:

```bash
memory add \
  -c investment_decision \
  --content "<why: reasoning, market context, expected outcome, confidence>" \
  -m security=<TICKER> \
  -m direction=<buy|sell> \
  -m confidence=<1-10>
```

Then also record the transaction via `finance-write` skill (the actual buy/sell in Maybe).

### Weekly Review (Sunday 20:00)

1. Query Maybe: `maybe snapshot --json` + `maybe trades --json`
2. Query Mem0: `memory list -c investment_decision`
3. Analyze: which decisions are working, extract lessons
4. Write to Mem0: `memory add -c weekly_review --content "..."`

For review templates, see `{baseDir}/references/weekly-review-template.md`.

### Monthly Review (1st of month 20:00)

1. Query all weekly reviews: `memory list -c weekly_review`
2. Query Maybe for monthly performance
3. Analyze patterns, decision success rate, style observations
4. Write to Mem0: `memory add -c monthly_review --content "..."`

For review templates, see `{baseDir}/references/monthly-review-template.md`.
