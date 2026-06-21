---
name: finance-write
description: "Record financial events: update account balances, create transactions with auto-tagging, manage investment holdings."
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

# Finance Write

Record financial events in Maybe Finance. Supports three operation types: balance reconciliation, transaction creation (with auto-tagging), and investment holding management.

## Hard Rules

- **ALWAYS query real data first** via `maybe accounts` before any write operation.
- **ALWAYS dry-run and confirm** before executing. Never write without user confirmation.
- **NEVER fabricate data.** All numbers must come from user input or CLI output.
- **Fuzzy match account names.** If ambiguous, list candidates and ask user to clarify.

## When NOT to Use

- User wants to READ balances or financial overview → use `finance-read`
- User asks about investment decision reasoning or lessons learned → use `finance-memory`
- User asks about stock prices or market news → use `yfinance`

## Intent Classification

Before acting, classify the user message into one of three types:

| Keywords | Type | Action |
|----------|------|--------|
| "余额是/现在是/对账/更新余额" | Balance Reconciliation | `maybe reconcile` |
| "买了/卖了/赎回/收到/利息/工资/转账/记录一笔" | Transaction Event | `maybe add-transaction` + auto-tag |
| "加仓/减仓/建仓/清仓/持仓" | Holding Management | `maybe holding add/update/delete` |

If ambiguous, ask: "你是想记录一笔交易，还是更新账户余额？"

## Balance Reconciliation

```bash
maybe reconcile --account <account_name> --balance <amount>
maybe reconcile --account <account_name> --balance <amount> --date YYYY-MM-DD
```

Flow: show current balance → parse input → dry-run (show delta) → confirm → execute.

For detailed reconciliation workflow, see `{baseDir}/references/reconcile-workflow.md`.

## Transaction Recording (with Auto-Tag)

```bash
maybe add-transaction \
  -a "<account_name>" \
  -d "<date>" \
  -m <amount> \
  -n "<name>" \
  --tag "<tag1>" \
  --nature <income|expense>
```

Flow:
1. Parse user input: account, amount, name, date, nature
2. Query available tags: `maybe tags --json`
3. Auto-match tag based on transaction name (see `{baseDir}/references/auto-tag-rules.md`)
4. Execute `maybe add-transaction` with matched tags
5. Confirm result

**Transfers between accounts** (e.g., fund redemption): create TWO transactions — expense from source + income to destination.

For detailed transaction and auto-tag workflow, see `{baseDir}/references/transaction-workflow.md`.

## Holding Management

```bash
maybe holding add --account "<account_name>" --ticker <TICKER> --qty <N> [--price <price>]
maybe holding update --account "<account_name>" --ticker <TICKER> --qty <N>
maybe holding delete --account "<account_name>" --ticker <TICKER>
maybe holding sync                # Fetch latest prices from Yahoo Finance
maybe holding rate --from USD --to CNY  # Set/fetch exchange rate
```

If `--price` is omitted, auto-fetched from Yahoo Finance.

**⚠️ Important: Do NOT manually update account balance after holding changes.**

The Maybe API automatically triggers `sync_later` after any holding operation (add/update/delete). This recalculates all historical balance records based on the new holdings. If you also call `maybe reconcile` or manually update the account balance, you'll cause double-counting or conflicts.

**Correct workflow:**
1. Execute holding operation (`maybe holding add/update/delete`)
2. API updates `Account.balance` and `cash_balance` automatically
3. API triggers `sync_later` to recalculate historical `Balance` records
4. Done. No further action needed.

**Incorrect workflow (DO NOT do this):**
1. ~~Execute holding operation~~
2. ~~Manually calculate new balance~~
3. ~~Call `maybe reconcile` to update balance~~ ❌ This will cause conflicts!

## Error Handling

| Error | Action |
|-------|--------|
| Account not found | List available accounts, ask user to retry |
| Maybe unreachable | Report: "Maybe is not running. Start: `docker compose up -d`" |
| 401 Unauthorized | Report: "API key invalid. Regenerate in Maybe → Settings → API Keys" |
| Same-date valuation | Report: "Already updated today. Use `--date YYYY-MM-DD` for a different date" |
