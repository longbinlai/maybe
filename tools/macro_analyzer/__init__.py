"""
宏观经济分析模块

提供以下分析功能：
1. 经济周期判断（复苏/扩张/滞胀/衰退）
2. 利率差分析（换汇决策支持）
3. 资产相对吸引力评估
4. 持仓匹配度分析
"""

from .economic_cycle import (
    EconomicCycleAnalyzer,
    EconomicCycle,
    EconomicIndicator,
    CycleAnalysis
)
from .interest_rate import (
    InterestRateAnalyzer,
    Currency,
    InterestRateInfo,
    RateDifferentialAnalysis
)
from .asset_attractiveness import (
    AssetAttractivenessAnalyzer,
    AssetClass,
    AssetAttractiveness,
    MarketCondition
)
from .portfolio_alignment import (
    PortfolioAlignmentAnalyzer,
    Holding,
    AlignmentAnalysis
)
from .analyzer import MacroAnalyzer, analyze_macro

__version__ = "1.0.0"
__all__ = [
    # 主分析器
    "MacroAnalyzer",
    "analyze_macro",
    # 经济周期
    "EconomicCycleAnalyzer",
    "EconomicCycle",
    "EconomicIndicator",
    "CycleAnalysis",
    # 利率差
    "InterestRateAnalyzer",
    "Currency",
    "InterestRateInfo",
    "RateDifferentialAnalysis",
    # 资产吸引力
    "AssetAttractivenessAnalyzer",
    "AssetClass",
    "AssetAttractiveness",
    "MarketCondition",
    # 持仓匹配度
    "PortfolioAlignmentAnalyzer",
    "Holding",
    "AlignmentAnalysis",
]
