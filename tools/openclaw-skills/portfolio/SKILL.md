---
name: portfolio
description: "投资组合配置管理：按资产类别分析实际配置 vs 目标、漂移、单一证券集中度红线。用户问'我的配置/仓位合理吗''要不要再平衡''集中度''偏离目标多少'时触发。"
metadata:
  {
    "openclaw":
      {
        "emoji": "📊",
        "requires": { "bins": ["maybe"], "env": ["MAYBE_API_KEY"] },
      },
  }
---

# Portfolio（投资组合配置管理）

按**资产类别**分析家庭投资组合：实际配置 vs 目标配置、漂移、单一证券集中度。
**只做客观计算，不提供投资建议。**

## 数据来源（佐证 — 回答时必须说明数据出处）

| 数据 | 来源 |
|------|------|
| 账户余额 / 持仓 / 总资产 / 净资产 | Maybe Finance（`maybe snapshot`、`maybe balance-sheet`） |
| 汇率（多币种换算到基准币 USD） | Maybe Finance 汇率（`maybe exchange-rates`，底层 Synth/yfinance） |
| 目标配置、单一证券上限、漂移阈值 | `~/.config/maybe-finance/portfolio/policy.yaml`（用户维护） |

> 凡引用数字，必须说明它来自上表哪一行；`policy.yaml` 里的目标是用户自己设的，不是模型臆测。

## 命令

```bash
# 配置分析：实际 vs 目标、漂移、再平衡提示、单一证券集中度
maybe portfolio analyze
maybe portfolio analyze --json     # 结构化输出，供告警/程序处理

# 查看/定位政策文件（首次运行自动从模板生成）
maybe portfolio policy
```

## 分类逻辑（重要 — 解释结果时要讲清楚）

资产类别不在 Maybe 数据里，由 `policy.yaml` 决定，**以账户为主**：

1. 账户名精确匹配 `account_classes`（最高优先级）——用于"余额型理财/固收"账户
2. 否则按账户类型 `account_type_classes` 兜底：`depository→cash`、`investment→equity`、`crypto→commodity`
3. 都没命中 → `other`（未分类）
4. 负债账户（贷款等，`classification=liability`）**不计入**资产配置
5. 单一证券集中度用**持仓**（holdings）计算，与账户级配置分开

若 `other` 占比偏高，说明有账户没映射——提示用户在 `policy.yaml` 的 `account_classes` 里补全，**不要替用户猜**类别。

## 回答规则（与全局一致）

- 报告里每个百分比都说清来自 Maybe 持仓/账户 + 哪个汇率换算。
- "总资产(自算)"会和 Maybe `total_assets` 对账；若差异 >2% 必须如实指出，不要掩盖。
- 漂移/再平衡只陈述**客观偏离**（实际 vs 用户设定的目标），措辞为"偏离目标 X 个百分点"，**不**说"应该买/卖"——那是用户决策。
- 数据缺失（如某币种无汇率、某账户未分类）必须明说"这部分未纳入/未知"，不要假装完整。

## 何时不用

- 想看具体某账户余额 / 某只股票现价 → 用 `finance-read` / `yfinance`
- 想记录买卖或调仓 → 用 `finance-write`（买卖时带 `--reason` 记录理由）
- 想要投资建议 / 选股 → 本 skill 不提供；分析框架见 `buffett`

## 首次使用

`maybe portfolio analyze` 第一次会在 `~/.config/maybe-finance/portfolio/policy.yaml`
生成保守型模板。用户需要把里面的**目标比例**和**账户→类别映射**改成自己的真实情况，
分析才有意义。改之前的结果只反映模板默认值，要向用户说明这一点。
