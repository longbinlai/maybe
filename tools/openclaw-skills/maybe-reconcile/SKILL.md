---
name: maybe-reconcile
description: "Update Maybe Finance account balances via natural language or CLI. Supports single account, batch, and interactive reconciliation."
homepage: https://github.com/maybe-finance/maybe
metadata:
  {
    "openclaw":
      {
        "emoji": "✏️",
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

# Maybe Reconcile

Update account balances in Maybe Finance. The user does NOT track every transaction — they periodically check their bank apps and update balances. This skill makes that fast and natural.

## When to Use

Use when:

- User says "update my balances" or "reconcile"
- User provides new balance numbers (e.g., "commbank 13500")
- User says "check my bank and update" or "monthly update"
- User forwards a bank statement or screenshot with balance info
- Scheduled monthly reconciliation reminder

## When NOT to Use

Do not use when:

- User asks to READ balances or check finances → use `maybe` skill instead
- User asks about portfolio allocation or net worth → use `maybe` skill
- User wants to record individual transactions (lunch, gas, etc.) → not the Maybe workflow
- User wants to create/delete accounts → use Maybe web UI
- User asks about stock trades → use Maybe web UI for trade entry

## Requirements

Same as `maybe` skill — `maybe-cli` installed and `MAYBE_API_KEY` set.

Additionally, the Python reconciliation script:

```bash
# Located at:
/path/to/maybe/tools/openclaw-skills/maybe-reconcile/scripts/maybe_reconcile.py
```

## Hard Rules

- **Always show current balances first** before accepting updates. User needs to see what they're changing from.
- **Always dry-run before executing.** Parse the input, show what would change, ask for confirmation, then execute.
- **Never update without confirmation.** Even if the input is unambiguous.
- **Fuzzy match account names.** "招行" should match "招商银行", "commbank" should match "commbank". If ambiguous, list candidates and ask.
- **Report delta for each change.** Show old → new and the difference (↑/↓).
- **Skip unchanged accounts silently.** If user says "commbank 14000" and it's already 14000, skip it.
- **If Maybe is unreachable**, report the error. Do not retry silently.

## Command Reference

### CLI (maybe-cli)

```bash
# Single account update (fuzzy name match)
maybe reconcile --account commbank --balance 13500
maybe reconcile --account 招商 --balance 9200 --date 2026-05-20

# Interactive batch (prompts for each account)
maybe reconcile-all

# Read-only
maybe accounts                              # List all accounts
maybe categories                             # List categories
maybe tags                                   # List tags
```

### Python Script (natural language)

```bash
SCRIPT="/path/to/tools/openclaw-skills/maybe-reconcile/scripts/maybe_reconcile.py"

# Show current balances
python3 $SCRIPT --list

# Parse only (dry run, no write)
python3 $SCRIPT --parse "commbank 13500，招行 9200，房贷 3820000"

# Execute (writes to Maybe)
python3 $SCRIPT "commbank 13500，招行 9200，房贷 3820000"

# JSON output (for programmatic processing)
python3 $SCRIPT --json "commbank 13500，招行 9200"
```

### Input Format

Natural language separators: `,`, `，`, `;`, newline, "and"

```
"commbank 13500"                          # single
"commbank 13500，招行 9200"                 # Chinese comma
"commbank 13500, 好多钱 9800000, 房贷 3820000"  # multiple
"commbank 13,500"                         # commas in numbers OK
```

Account name matching priority:
1. Exact match (case-insensitive)
2. Substring match ("招商" matches "招商银行" and "招商信用卡" → ambiguous, ask user)
3. Prefix match

## Workflows

### Monthly Reconciliation (Primary Flow)

This is the main use case. Runs once a month.

**Step 1 — Show current state:**

```bash
python3 $SCRIPT --list
```

Present to user:
```
📊 Current balances (last updated: 2026-04-23):

  commbank         AU$13,500
  好多钱银行         $9,780,000
  工商银行           $48,000
  房贷              ¥3,820,000
  招商信用卡          ¥9,200
  招商银行           ¥9,200
  日本投资           ¥5,000,000
  良语久园           ¥5,000,000
  长桥R             $105,000

Which accounts changed?
```

**Step 2 — Parse user input (dry run):**

User: "commbank 14000，招行 9200，房贷 3810000"

```bash
python3 $SCRIPT --parse "commbank 14000，招行 9200，房贷 3810000"
```

Present to user:
```
Changes detected:

  ✅ commbank    AU$13,500 → AU$14,000  (↑ AU$500)
  ⚠️  招行        → ambiguous: 招商银行 or 招商信用卡?
  ✅ 房贷        ¥3,820,000 → ¥3,810,000  (↓ ¥10,000)

Please clarify "招行" — did you mean 招商银行 or 招商信用卡?
```

**Step 3 — Resolve ambiguity, confirm, execute:**

User: "招商银行"

```bash
python3 $SCRIPT --json "commbank 14000，招商银行 9200，房贷 3810000"
```

Present result:
```
✅ Reconciled 3 accounts:
  commbank    AU$13,500 → AU$14,000  (↑ AU$500)
  招商银行     ¥9,200 → ¥9,200  (no change, skipped)
  房贷        ¥3,820,000 → ¥3,810,000  (↓ ¥10,000)

Net worth: $10,145,320
```

### Quick Single Update

User: "commbank 现在 14500"

```bash
maybe reconcile --account commbank --balance 14500
```

```
✅ commbank: AU$14,000 → AU$14,500 (↑ AU$500)
```

### Scheduled Reminder

When cron triggers monthly reminder:

```
📊 Monthly reconciliation reminder.
Your last update was 30 days ago (2026-04-23).

Current balances:
[list from maybe accounts]

Ready to update? Just tell me which accounts changed.
```

## Ambiguity Resolution

When a name matches multiple accounts:

| Input | Matches | Action |
|---|---|---|
| "招商" | 招商银行, 招商信用卡 | Ask: "Which one? 招商银行 (¥9,200) or 招商信用卡 (¥9,200)?" |
| "投资" | 日本投资, 长桥R | Ask: "Which one? 日本投资 (¥5M) or 长桥R ($105K)?" |
| "银行" | 好多钱银行, 工商银行, 招商银行 | List all, ask user to be specific |

When a name matches nothing:

```
⚠️ No account matching "HSBC". Available accounts:
  commbank, 好多钱银行, 工商银行, 房贷, 招商信用卡, 招商银行, 日本投资, 良语久园, 长桥R
```

## Error Handling

| Error | Cause | Action |
|---|---|---|
| "No account matching X" | Name not found | List available accounts, ask user to retry |
| Connection refused | Maybe not running | "Maybe is not running. Start: `docker compose up -d`" |
| 401 Unauthorized | Invalid API key | "API key invalid. Regenerate in Maybe → Settings → API Keys" |
| Same-date valuation | Already reconciled today | "Already updated today. Use a different date with `--date YYYY-MM-DD`" |
| Parse failure | Can't extract amount | "Couldn't understand 'XXX'. Format: `<account name> <number>`" |

## Data Flow

```
User (IM/terminal)
    │
    ├── "commbank 14000，招行 9200"
    │
    ▼
maybe_reconcile.py --parse    ← dry run, shows preview
    │
    ├── fuzzy match → Maybe accounts API
    ├── calculate deltas
    │
    ▼
Confirm with user
    │
    ▼
maybe_reconcile.py            ← execute, writes valuations
    │
    ├── POST /api/v1/accounts/:id/valuations
    ├── Maybe recalculates balance history
    │
    ▼
Report results + new net worth
```
