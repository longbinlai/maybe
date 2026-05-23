# maybe-cli

Command-line interface for Maybe Finance — query family financial data for AI agents and humans.

## Install

```bash
cd tools/maybe-cli
pip install -e .
```

## Setup

```bash
export MAYBE_API_KEY="your-api-key"
export MAYBE_URL="http://localhost:3000"  # default
```

Generate an API key in Maybe: Settings → API Keys

## Commands

| Command | Description |
|---|---|
| `maybe snapshot` | Full financial overview (net worth + accounts + holdings) |
| `maybe balance-sheet` | Net worth, assets, liabilities with breakdown |
| `maybe accounts` | List all accounts |
| `maybe holdings` | Investment holdings across all accounts |
| `maybe trades` | Buy/sell trade history |
| `maybe securities` | Security metadata and prices |
| `maybe income-statement` | Income/expense summary by category |
| `maybe exchange-rates` | Currency exchange rates |

All commands accept `--json` for structured JSON output (ideal for AI agents).

## Examples

```bash
# Human-readable snapshot
maybe snapshot

# JSON for AI processing
maybe snapshot --json

# Balance sheet with date range
maybe balance-sheet --start-date 2024-01-01

# Holdings for a specific account
maybe holdings --account-id <uuid>

# Exchange rates
maybe exchange-rates --from USD --to CNY
```

## OpenClaw Integration

See `tools/openclaw-skills/maybe/` for the OpenClaw skill that uses this CLI.
