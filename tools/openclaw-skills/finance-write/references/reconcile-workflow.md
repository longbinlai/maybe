# Reconciliation Workflow

## Overview

Users periodically check bank apps and update balances. This is NOT transaction recording — it's reporting the current state of an account.

## Flow

### Step 1 — Show current state

```bash
maybe accounts --json
```

Present real balances to user, then ask: "Which accounts changed?"

### Step 2 — Parse user input (dry run)

User provides: `<账户名> <金额>` (separators: `,`, `，`, `;`, newline)

Show preview:
```
Changes detected:
  ✅ 储蓄账户A    ¥50,000 → ¥55,000  (↑ ¥5,000)
  ⚠️  储蓄账户           → ambiguous: 储蓄账户A or 储蓄账户B?
  ✅ 海外储蓄账户    AU$80,000 → AU$75,000  (↓ AU$5,000)
```

### Step 3 — Confirm and execute

```bash
maybe reconcile --account "储蓄账户A" --balance 55000
maybe reconcile --account "海外储蓄账户" --balance 75000
```

Report:
```
✅ Reconciled 2 accounts:
  储蓄账户A    ¥50,000 → ¥55,000  (↑ ¥5,000)
  海外储蓄账户    AU$80,000 → AU$75,000  (↓ AU$5,000)
```

## Account Name Matching

Priority: exact match → substring match → prefix match.
If ambiguous, list candidates and ask user to clarify.

## Python Script (batch mode)

```bash
SCRIPT="{baseDir}/../maybe-reconcile/scripts/maybe_reconcile.py"

python3 $SCRIPT --list                                    # Show current balances
python3 $SCRIPT --parse "<账户名> <金额>，<账户名> <金额>"  # Dry run
python3 $SCRIPT "<账户名> <金额>，<账户名> <金额>"          # Execute
python3 $SCRIPT --json "<user input>"                      # JSON output
```

## Scheduled Reminder

When cron triggers monthly reminder:
1. Run `maybe accounts` to get real current balances
2. Present them to user
3. Ask: "Ready to update? Just tell me which accounts changed."
