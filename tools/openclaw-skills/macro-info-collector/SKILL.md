---
name: macro-info-collector
description: "Collect and summarize macroeconomic information: central bank policies, economic indicators, forex, commodities, market sentiment."
---

# 宏观经济信息收集器

收集和整理宏观经济信息，生成清晰的摘要报告。

## 功能

- 收集央行、经济指标、外汇、大宗商品、市场情绪等数据
- 自动翻译英文标题中的常见财经词汇
- 生成格式化的宏观经济摘要
- 输出到 stdout（由 OpenClaw delivery 机制发送到飞书）

## 调用方式

```bash
# 生成摘要（人类可读格式）— 用于 cron job / 飞书发送
~/pyenv/maybe/bin/python3 ~/Documents/git/maybe/tools/openclaw-skills/macro-info-collector/scripts/collect_macro_info.py --summary --quiet

# 输出 JSON（程序处理格式）
~/pyenv/maybe/bin/python3 ~/Documents/git/maybe/tools/openclaw-skills/macro-info-collector/scripts/collect_macro_info.py --quiet

# 仅获取 YFinance 数据（跳过 RSS，速度更快）
~/pyenv/maybe/bin/python3 ~/Documents/git/maybe/tools/openclaw-skills/macro-info-collector/scripts/collect_macro_info.py --summary --quiet --yfinance-only

# 不使用缓存（强制刷新）
~/pyenv/maybe/bin/python3 ~/Documents/git/maybe/tools/openclaw-skills/macro-info-collector/scripts/collect_macro_info.py --summary --quiet --no-cache
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `--summary` | 生成人类可读的摘要报告 |
| `--no-cache` | 不使用缓存，强制从数据源获取 |
| `--timeout <N>` | 单个数据源超时时间（秒），默认 30 |
| `--concurrency <N>` | RSS/NewsAPI 并发数，默认 4 |
| `--yfinance-only` | 只获取 YFinance 数据 |
| `--no-yfinance` | 跳过 YFinance，只获取 RSS/NewsAPI |

## 输出格式示例

```
宏观经济摘要 (2026-06-21)

央行政策
美联储: 维持利率 5.25-5.50% 不变，预计今年降息 1 次
ECB: 降息 25 基点至 3.75%
日本央行: 维持利率 0-0.1%

经济指标
美国 GDP: 2.3% (Q1 2026)
美国 CPI: 3.1% (2026-05)

外汇市场
USD/CNY: 7.25 (-0.2%)
USD/JPY: 161.28 (+0.5%)

大宗商品
黄金: $2,350/oz (+1.2%)
原油: $78.5/bbl (-2.3%)

市场情绪
VIX: 14.2 (低波动)
S&P 500: 5,450 (+0.8%)
```

## 使用场景

- 用户问"最近宏观经济怎么样"
- 每日早报定时任务
- 用户需要了解市场动态

## 数据源

数据源配置在 datahub 包内（`datahub/config/sources.yaml`），包括：
- 央行：美联储、ECB、日本央行
- 经济指标：BEA (GDP)、BLS (就业/CPI)
- 外汇：ForexLive、Yahoo Finance
- 大宗商品：OilPrice、Yahoo Finance
- 新闻：财新、南华早报、NewsAPI

## 依赖

- datahub (Python 包，已安装到 ~/pyenv/maybe)
- Ollama 本地模型 (gemma4:12b，用于新闻标题翻译，`think: false` 模式)
- Python 3.14 (~/pyenv/maybe/bin/python3)

## 输出说明

- **stdout**: 仅输出格式化报告（由 OpenClaw delivery 机制发送到飞书）
- **stderr**: 所有进度信息（不会发送到飞书）
- `--quiet` 参数会完全静默进度信息（推荐 cron job 使用）
