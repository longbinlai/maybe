"""
资产相对吸引力评估器

基于经济周期和市场状况，评估不同资产类别的相对吸引力。

资产类别：
- stocks: 股票
- bonds: 债券
- cash: 现金
- commodities: 大宗商品
- real_estate: 房地产
- gold: 黄金
"""

from dataclasses import dataclass
from typing import Dict, List
from enum import Enum
from .economic_cycle import EconomicCycle


class AssetClass(Enum):
    """资产类别"""
    STOCKS = "stocks"
    BONDS = "bonds"
    CASH = "cash"
    COMMODITIES = "commodities"
    REAL_ESTATE = "real_estate"
    GOLD = "gold"


@dataclass
class AssetAttractiveness:
    """资产吸引力评分"""
    asset_class: AssetClass
    score: float  # 0-100
    reasoning: str
    trend: str  # "up", "down", "stable"


@dataclass
class MarketCondition:
    """市场状况"""
    stock_market_trend: str = "stable"  # "up", "down", "stable"
    bond_yield_trend: str = "stable"
    commodity_trend: str = "stable"
    real_estate_trend: str = "stable"
    inflation_expectation: str = "stable"


class AssetAttractivenessAnalyzer:
    """资产吸引力分析器"""

    # 经济周期对应的资产偏好权重
    CYCLE_WEIGHTS = {
        EconomicCycle.RECOVERY: {
            AssetClass.STOCKS: 90,
            AssetClass.REAL_ESTATE: 70,
            AssetClass.COMMODITIES: 60,
            AssetClass.BONDS: 40,
            AssetClass.CASH: 30,
            AssetClass.GOLD: 20,
        },
        EconomicCycle.EXPANSION: {
            AssetClass.COMMODITIES: 90,
            AssetClass.REAL_ESTATE: 85,
            AssetClass.STOCKS: 75,
            AssetClass.GOLD: 50,
            AssetClass.BONDS: 30,
            AssetClass.CASH: 20,
        },
        EconomicCycle.STAGFLATION: {
            AssetClass.CASH: 85,
            AssetClass.GOLD: 90,
            AssetClass.COMMODITIES: 70,
            AssetClass.BONDS: 40,
            AssetClass.STOCKS: 30,
            AssetClass.REAL_ESTATE: 35,
        },
        EconomicCycle.RECESSION: {
            AssetClass.BONDS: 90,
            AssetClass.CASH: 80,
            AssetClass.GOLD: 70,
            AssetClass.STOCKS: 40,
            AssetClass.COMMODITIES: 30,
            AssetClass.REAL_ESTATE: 35,
        },
    }

    def __init__(self):
        self.market_condition = MarketCondition()

    def set_market_condition(
        self,
        stock_market_trend: str = "stable",
        bond_yield_trend: str = "stable",
        commodity_trend: str = "stable",
        real_estate_trend: str = "stable",
        inflation_expectation: str = "stable",
    ):
        """设置市场状况"""
        self.market_condition = MarketCondition(
            stock_market_trend=stock_market_trend,
            bond_yield_trend=bond_yield_trend,
            commodity_trend=commodity_trend,
            real_estate_trend=real_estate_trend,
            inflation_expectation=inflation_expectation,
        )

    def analyze(self, economic_cycle: EconomicCycle) -> List[AssetAttractiveness]:
        """分析资产吸引力"""
        base_scores = self.CYCLE_WEIGHTS.get(economic_cycle, {})
        adjustments = self._calculate_market_adjustments()

        attractiveness_list = []

        for asset_class in AssetClass:
            base_score = base_scores.get(asset_class, 50)
            adjustment = adjustments.get(asset_class, 0)
            final_score = max(0, min(100, base_score + adjustment))

            reasoning = self._generate_reasoning(asset_class, economic_cycle, adjustment)
            trend = self._determine_trend(asset_class)

            attractiveness = AssetAttractiveness(
                asset_class=asset_class,
                score=final_score,
                reasoning=reasoning,
                trend=trend,
            )
            attractiveness_list.append(attractiveness)

        # 按分数排序（从高到低）
        attractiveness_list.sort(key=lambda x: x.score, reverse=True)

        return attractiveness_list

    def _calculate_market_adjustments(self) -> Dict[AssetClass, float]:
        """根据市场状况计算调整"""
        adjustments = {asset: 0 for asset in AssetClass}

        # 股票市场趋势
        if self.market_condition.stock_market_trend == "up":
            adjustments[AssetClass.STOCKS] += 10
            adjustments[AssetClass.BONDS] -= 5
        elif self.market_condition.stock_market_trend == "down":
            adjustments[AssetClass.STOCKS] -= 10
            adjustments[AssetClass.BONDS] += 5

        # 债券收益率趋势
        if self.market_condition.bond_yield_trend == "up":
            adjustments[AssetClass.BONDS] -= 5  # 收益率上升，债券价格下跌
            adjustments[AssetClass.CASH] += 5
        elif self.market_condition.bond_yield_trend == "down":
            adjustments[AssetClass.BONDS] += 5
            adjustments[AssetClass.CASH] -= 5

        # 大宗商品趋势
        if self.market_condition.commodity_trend == "up":
            adjustments[AssetClass.COMMODITIES] += 10
            adjustments[AssetClass.GOLD] += 5
        elif self.market_condition.commodity_trend == "down":
            adjustments[AssetClass.COMMODITIES] -= 10
            adjustments[AssetClass.GOLD] -= 5

        # 房地产趋势
        if self.market_condition.real_estate_trend == "up":
            adjustments[AssetClass.REAL_ESTATE] += 10
        elif self.market_condition.real_estate_trend == "down":
            adjustments[AssetClass.REAL_ESTATE] -= 10

        # 通胀预期
        if self.market_condition.inflation_expectation == "up":
            adjustments[AssetClass.GOLD] += 10
            adjustments[AssetClass.COMMODITIES] += 5
            adjustments[AssetClass.CASH] -= 10
            adjustments[AssetClass.BONDS] -= 5
        elif self.market_condition.inflation_expectation == "down":
            adjustments[AssetClass.GOLD] -= 5
            adjustments[AssetClass.BONDS] += 5

        return adjustments

    def _generate_reasoning(
        self,
        asset_class: AssetClass,
        cycle: EconomicCycle,
        adjustment: float
    ) -> str:
        """生成资产推荐理由"""
        cycle_names = {
            EconomicCycle.RECOVERY: "复苏期",
            EconomicCycle.EXPANSION: "扩张期",
            EconomicCycle.STAGFLATION: "滞胀期",
            EconomicCycle.RECESSION: "衰退期",
        }

        base_reasoning = f"当前处于{cycle_names.get(cycle, '未知')}周期"

        adjustment_text = ""
        if adjustment > 5:
            adjustment_text = "，市场状况利好"
        elif adjustment < -5:
            adjustment_text = "，市场状况不利"

        return base_reasoning + adjustment_text

    def _determine_trend(self, asset_class: AssetClass) -> str:
        """判断资产趋势"""
        trend_map = {
            AssetClass.STOCKS: self.market_condition.stock_market_trend,
            AssetClass.BONDS: self.market_condition.bond_yield_trend,
            AssetClass.COMMODITIES: self.market_condition.commodity_trend,
            AssetClass.REAL_ESTATE: self.market_condition.real_estate_trend,
        }
        return trend_map.get(asset_class, "stable")

    def get_top_recommendations(
        self,
        economic_cycle: EconomicCycle,
        top_n: int = 3
    ) -> List[AssetAttractiveness]:
        """获取前 N 个推荐资产"""
        all_assets = self.analyze(economic_cycle)
        return all_assets[:top_n]

    def format_ranking(self, attractiveness_list: List[AssetAttractiveness]) -> str:
        """格式化排名结果"""
        lines = ["=== 资产吸引力排名 ===\n"]

        for i, asset in enumerate(attractiveness_list, 1):
            trend_emoji = {
                "up": "📈",
                "down": "📉",
                "stable": "➡️",
            }.get(asset.trend, "➡️")

            lines.append(
                f"{i}. {asset.asset_class.value.upper()}: "
                f"{asset.score:.0f}分 {trend_emoji}"
            )
            lines.append(f"   {asset.reasoning}\n")

        return "\n".join(lines)
