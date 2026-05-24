# 宏观经济分析模块 (macro_analyzer)

基于宏观经济指标提供资产配置建议和持仓匹配度分析。

## 功能特性

### 1. 经济周期判断
基于美林时钟模型，判断当前经济周期阶段：
- **复苏期 (Recovery)**: GDP↑ 通胀低 → 增持股票
- **扩张期 (Expansion)**: GDP↑ 通胀↑ → 增持商品/房产
- **滞胀期 (Stagflation)**: GDP↓ 通胀↑ → 增持现金/黄金
- **衰退期 (Recession)**: GDP↓ 通胀↓ → 增持债券

### 2. 利率差分析
分析不同国家/地区的利率差异，为换汇决策提供依据：
- 计算利率差（Interest Rate Differential）
- 评估换汇收益（考虑汇率变动）
- 提供换汇建议（推荐/不推荐/强烈不推荐）

### 3. 资产相对吸引力评估
基于经济周期和市场状况，评估不同资产类别的相对吸引力：
- 股票 (stocks)
- 债券 (bonds)
- 现金 (cash)
- 大宗商品 (commodities)
- 房地产 (real_estate)
- 黄金 (gold)

### 4. 持仓匹配度分析
分析当前持仓与宏观经济环境的匹配程度：
- 计算持仓与推荐配置的偏差
- 识别过度配置和低配置的资产
- 生成调仓建议

## 安装

```bash
cd ~/Documents/git/maybe/tools
# 模块已经在项目中，无需额外安装
```

## 快速开始

### 基本使用

```python
from macro_analyzer import MacroAnalyzer

# 创建分析器
analyzer = MacroAnalyzer()

# 执行分析
report = analyzer.analyze(
    gdp_growth=2.5,  # GDP 增长 2.5%
    inflation=3.2,  # 通胀 3.2%
    unemployment=4.1,  # 失业率 4.1%
    interest_rate=5.5,  # 基准利率 5.5%
    stock_market_trend="up",  # 股市趋势
)

# 格式化输出
print(analyzer.format_report(report))
```

### 带持仓分析

```python
from macro_analyzer import MacroAnalyzer
from macro_analyzer.portfolio_alignment import Holding
from macro_analyzer.asset_attractiveness import AssetClass

analyzer = MacroAnalyzer()

# 定义持仓
holdings = [
    Holding(AssetClass.STOCKS, "AAPL", "苹果股票", 50000),
    Holding(AssetClass.BONDS, "TLT", "长期国债", 20000),
    Holding(AssetClass.CASH, "CASH", "现金", 15000),
]

# 执行分析
report = analyzer.analyze(
    gdp_growth=2.5,
    inflation=3.2,
    unemployment=4.1,
    holdings=holdings,
)

# 查看匹配度
print(f"匹配度评分: {report['portfolio_alignment']['alignment_score']}")
print("调仓建议:")
for rec in report['portfolio_alignment']['recommendations']:
    print(f"  {rec}")
```

### 运行示例

```bash
cd ~/Documents/git/maybe/tools/macro_analyzer
python3 example.py
```

## 模块结构

```
macro_analyzer/
├── __init__.py              # 模块入口
├── analyzer.py              # 综合分析器
├── economic_cycle.py        # 经济周期分析
├── interest_rate.py         # 利率差分析
├── asset_attractiveness.py  # 资产吸引力评估
├── portfolio_alignment.py   # 持仓匹配度分析
├── example.py               # 使用示例
└── README.md                # 本文档
```

## 核心类

### MacroAnalyzer
综合分析器，整合所有分析功能。

**方法:**
- `analyze()`: 执行完整分析
- `format_report()`: 格式化报告

### EconomicCycleAnalyzer
经济周期分析器。

**方法:**
- `set_indicators()`: 设置经济指标
- `analyze()`: 分析经济周期

### InterestRateAnalyzer
利率差分析器。

**方法:**
- `update_rate()`: 更新利率数据
- `analyze()`: 分析换汇收益
- `get_all_rate_differentials()`: 获取所有利率差

### AssetAttractivenessAnalyzer
资产吸引力评估器。

**方法:**
- `set_market_condition()`: 设置市场状况
- `analyze()`: 评估资产吸引力
- `get_top_recommendations()`: 获取推荐资产

### PortfolioAlignmentAnalyzer
持仓匹配度分析器。

**方法:**
- `set_holdings()`: 设置持仓
- `add_holding()`: 添加单个持仓
- `analyze()`: 分析匹配度

## 数据来源

### 经济指标
- **GDP 增长率**: 从 Maybe Finance API 或外部数据源获取
- **通胀率 (CPI)**: 从 BLS (美国劳工统计局) 获取
- **失业率**: 从 BLS 获取
- **基准利率**: 从各国央行获取

### 利率数据
内置默认利率数据（需要定期更新）：
- USD: 5.50% (Federal Reserve)
- CNY: 3.45% (中国人民银行)
- JPY: 0.10% (日本央行)
- EUR: 4.50% (欧洲央行)
- GBP: 5.25% (英国央行)
- AUD: 4.35% (澳大利亚央行)

### 市场状况
需要手动设置或从 DataHub 模块获取：
- 股票市场趋势
- 债券收益率趋势
- 大宗商品趋势
- 房地产趋势
- 通胀预期

## 与 DataHub 集成

```python
from datahub import SourceRegistry
from macro_analyzer import MacroAnalyzer

# 从 DataHub 获取数据
registry = SourceRegistry(config_path="path/to/sources.yaml")
results = registry.fetch_all()

# 提取经济指标（需要自定义解析逻辑）
gdp_growth = extract_gdp_growth(results)
inflation = extract_inflation(results)
# ...

# 执行分析
analyzer = MacroAnalyzer()
report = analyzer.analyze(
    gdp_growth=gdp_growth,
    inflation=inflation,
    # ...
)
```

## 与 Maybe Finance 集成

```python
from maybe_api import MaybeAPI
from macro_analyzer import MacroAnalyzer
from macro_analyzer.portfolio_alignment import Holding
from macro_analyzer.asset_attractiveness import AssetClass

# 从 Maybe 获取持仓
maybe = MaybeAPI()
accounts = maybe.get_accounts()

# 转换持仓格式
holdings = []
for account in accounts:
    if account['type'] == 'investment':
        asset_class = AssetClass.STOCKS
    elif account['type'] == 'bond':
        asset_class = AssetClass.BONDS
    # ... 其他映射

    holdings.append(Holding(
        asset_class=asset_class,
        ticker=account['ticker'],
        name=account['name'],
        value=account['value'],
    ))

# 执行分析
analyzer = MacroAnalyzer()
report = analyzer.analyze(holdings=holdings, ...)
```

## 输出示例

```
============================================================
宏观经济综合分析报告
============================================================

【1. 经济周期分析】
当前周期: EXPANSION
置信度: 75%
分析: GDP 增长 2.5%（>1.0%），通胀 3.2%（>2.0%），处于扩张期
推荐资产: commodities, real_estate, stocks

【2. 利率差分析（换汇建议）】
  USD → CNY: 利率差 -2.05%, 不建议换汇 (medium风险)
  USD → JPY: 利率差 -5.40%, 强烈不建议换汇 (high风险)
  USD → EUR: 利率差 -1.00%, 不建议换汇 (medium风险)

【3. 资产吸引力排名】
  1. COMMODITIES: 90分 📈
  2. REAL_ESTATE: 85分 📈
  3. STOCKS: 75分 📈

【4. 持仓匹配度分析】
匹配度评分: 65/100
分析: 当前经济周期: 扩张期 | 匹配度评分: 65/100 | ⚠️ 持仓配置基本匹配，但有优化空间
过度配置: STOCKS
低配置: COMMODITIES, REAL_ESTATE

调仓建议:
  ⚠️ STOCKS 过度配置 +25.0%，建议减持
  📈 COMMODITIES 低配置 -35.0%，建议增持
  📈 REAL_ESTATE 低配置 -25.0%，建议增持
  💡 建议将资金从 stocks 转移到 commodities, real_estate

============================================================
```

## 注意事项

1. **数据时效性**: 经济指标和利率数据需要定期更新
2. **模型局限性**: 美林时钟模型是简化模型，实际市场更复杂
3. **汇率风险**: 利率差分析未考虑汇率波动风险
4. **个性化建议**: 本模块提供通用建议，具体操作需结合个人情况

## 开发计划

- [x] 经济周期判断
- [x] 利率差分析
- [x] 资产吸引力评估
- [x] 持仓匹配度分析
- [ ] 与 DataHub 自动集成
- [ ] 与 Maybe Finance 自动集成
- [ ] 历史记录和趋势分析
- [ ] 多场景对比分析

## 许可证

MIT License
