# Auto-Tag Rules

## Available Tags

Query via `maybe tags --json`. Current tags:
利息, 工资, 房贷, 投资, 日常消费, 转账, 保险, 医疗, 教育, 旅行, 固定支出, 分红, 手续费

## Matching Rules

| Transaction Name Contains | Tag | Confidence |
|--------------------------|-----|------------|
| 利息, interest | 利息 | 95% |
| 工资, salary, 薪水, payroll | 工资 | 95% |
| 房贷, mortgage, 月供 | 房贷 | 90% |
| 基金赎回, 卖出, 股票卖, 减仓 | 投资 | 90% |
| 基金申购, 买入, 加仓 | 投资 | 90% |
| 分红, dividend | 分红 | 90% |
| 转账, transfer, 转入, 转出 | 转账 | 85% |
| 超市, 购物, 餐饮, 外卖 | 日常消费 | 80% |
| 保险, insurance, 保费 | 保险 | 85% |
| 医院, 药店, 体检, medical | 医疗 | 80% |
| 学费, 培训, education | 教育 | 80% |
| 机票, 酒店, 旅行, travel | 旅行 | 80% |
| 房租, 水电, 物业, 订阅, 会员 | 固定支出 | 80% |
| 手续费, fee, 佣金 | 手续费 | 80% |

## Confidence Thresholds

- **≥ 90%**: Auto-apply tag, show in confirmation
- **70-89%**: Auto-apply tag, show reasoning
- **< 70%**: Skip tagging, explain why

## Nature Detection

| Keywords | Nature |
|----------|--------|
| 收到, 收入, 利息, 工资, 分红, 到账 | income |
| 支付, 买了, 消费, 支出, 还款 | expense |

Default: ask user if unclear.
