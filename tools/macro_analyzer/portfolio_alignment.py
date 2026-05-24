"""
持仓匹配度分析器

分析当前持仓与宏观经济环境的匹配程度，提供调仓建议。

主要功能：
1. 计算持仓与推荐配置的偏差
2. 识别过度配置和低配置的资产
3. 生成调仓建议
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from economic_cycle import EconomicCycle, CycleAnalysis
from asset_attractiveness import AssetClass, AssetAttractiveness


@dataclass
class Holding:
    """持仓信息"""
    asset_class: AssetClass
    ticker: str
    name: str
    value: float  # 持仓价值
    weight: float = 0.0  # 持仓权重 (%)，可以在添加后计算


@dataclass
class AlignmentAnalysis:
    """匹配度分析结果"""
    alignment_score: float  # 0-100，100 表示完美匹配
    deviations: Dict[AssetClass, float]  # 每个资产的偏差 (%)
    over_weighted: List[AssetClass]  # 过度配置的资产
    under_weighted: List[AssetClass]  # 低配置的资产
    recommendations: List[str]
    reasoning: str


class PortfolioAlignmentAnalyzer:
    """持仓匹配度分析器"""

    # 推荐的资产配置比例（基于经济周期）
    RECOMMENDED_ALLOCATION = {
        EconomicCycle.RECOVERY: {
            AssetClass.STOCKS: 50,
            AssetClass.REAL_ESTATE: 20,
            AssetClass.COMMODITIES: 15,
            AssetClass.BONDS: 10,
            AssetClass.CASH: 5,
            AssetClass.GOLD: 0,
        },
        EconomicCycle.EXPANSION: {
            AssetClass.COMMODITIES: 35,
            AssetClass.REAL_ESTATE: 25,
            AssetClass.STOCKS: 25,
            AssetClass.GOLD: 10,
            AssetClass.BONDS: 5,
            AssetClass.CASH: 0,
        },
        EconomicCycle.STAGFLATION: {
            AssetClass.CASH: 35,
            AssetClass.GOLD: 30,
            AssetClass.COMMODITIES: 20,
            AssetClass.BONDS: 10,
            AssetClass.STOCKS: 5,
            AssetClass.REAL_ESTATE: 0,
        },
        EconomicCycle.RECESSION: {
            AssetClass.BONDS: 40,
            AssetClass.CASH: 30,
            AssetClass.GOLD: 20,
            AssetClass.STOCKS: 10,
            AssetClass.COMMODITIES: 0,
            AssetClass.REAL_ESTATE: 0,
        },
    }

    # 偏差容忍度（%）
    TOLERANCE = 10  # 允许 ±10% 的偏差

    def __init__(self):
        self.holdings: List[Holding] = []

    def set_holdings(self, holdings: List[Holding]):
        """设置持仓信息"""
        self.holdings = holdings

    def add_holding(
        self,
        asset_class: AssetClass,
        ticker: str,
        name: str,
        value: float,
    ):
        """添加单个持仓"""
        # 计算权重
        total_value = sum(h.value for h in self.holdings) + value
        weight = (value / total_value) * 100 if total_value > 0 else 0

        # 更新所有持仓的权重
        for holding in self.holdings:
            holding.weight = (holding.value / total_value) * 100 if total_value > 0 else 0

        self.holdings.append(Holding(asset_class, ticker, name, value, weight))

    def analyze(self, cycle_analysis: CycleAnalysis) -> AlignmentAnalysis:
        """分析持仓匹配度"""
        current_allocation = self._calculate_current_allocation()
        recommended_allocation = self.RECOMMENDED_ALLOCATION.get(
            cycle_analysis.cycle, {}
        )

        # 计算偏差
        deviations = {}
        for asset_class in AssetClass:
            current = current_allocation.get(asset_class, 0)
            recommended = recommended_allocation.get(asset_class, 0)
            deviations[asset_class] = current - recommended

        # 识别过度配置和低配置
        over_weighted = [
            asset for asset, dev in deviations.items()
            if dev > self.TOLERANCE
        ]
        under_weighted = [
            asset for asset, dev in deviations.items()
            if dev < -self.TOLERANCE
        ]

        # 计算匹配度分数
        alignment_score = self._calculate_alignment_score(deviations)

        # 生成建议
        recommendations = self._generate_recommendations(
            deviations, over_weighted, under_weighted
        )

        # 生成说明
        reasoning = self._generate_reasoning(
            cycle_analysis, alignment_score, deviations
        )

        return AlignmentAnalysis(
            alignment_score=alignment_score,
            deviations=deviations,
            over_weighted=over_weighted,
            under_weighted=under_weighted,
            recommendations=recommendations,
            reasoning=reasoning,
        )

    def _calculate_current_allocation(self) -> Dict[AssetClass, float]:
        """计算当前资产配置"""
        total_value = sum(h.value for h in self.holdings)
        if total_value == 0:
            return {asset: 0 for asset in AssetClass}

        allocation = {}
        for asset_class in AssetClass:
            asset_value = sum(
                h.value for h in self.holdings
                if h.asset_class == asset_class
            )
            allocation[asset_class] = (asset_value / total_value) * 100

        return allocation

    def _calculate_alignment_score(
        self,
        deviations: Dict[AssetClass, float]
    ) -> float:
        """计算匹配度分数"""
        # 计算平均绝对偏差
        total_deviation = sum(abs(dev) for dev in deviations.values())
        avg_deviation = total_deviation / len(deviations)

        # 转换为分数（偏差越小，分数越高）
        # 0% 偏差 = 100 分，50% 偏差 = 0 分
        score = max(0, 100 - (avg_deviation * 2))

        return score

    def _generate_recommendations(
        self,
        deviations: Dict[AssetClass, float],
        over_weighted: List[AssetClass],
        under_weighted: List[AssetClass],
    ) -> List[str]:
        """生成调仓建议"""
        recommendations = []

        if not over_weighted and not under_weighted:
            recommendations.append("✓ 当前持仓与推荐配置匹配良好，无需调整")
            return recommendations

        # 过度配置的建议
        for asset in over_weighted:
            deviation = deviations[asset]
            recommendations.append(
                f"⚠️ {asset.value.upper()} 过度配置 {deviation:+.1f}%，建议减持"
            )

        # 低配置的建议
        for asset in under_weighted:
            deviation = deviations[asset]
            recommendations.append(
                f"📈 {asset.value.upper()} 低配置 {deviation:+.1f}%，建议增持"
            )

        # 生成具体操作建议
        if over_weighted and under_weighted:
            recommendations.append(
                f"💡 建议将资金从 {', '.join(a.value for a in over_weighted)} "
                f"转移到 {', '.join(a.value for a in under_weighted)}"
            )

        return recommendations

    def _generate_reasoning(
        self,
        cycle_analysis: CycleAnalysis,
        alignment_score: float,
        deviations: Dict[AssetClass, float],
    ) -> str:
        """生成分析说明"""
        cycle_names = {
            EconomicCycle.RECOVERY: "复苏期",
            EconomicCycle.EXPANSION: "扩张期",
            EconomicCycle.STAGFLATION: "滞胀期",
            EconomicCycle.RECESSION: "衰退期",
        }

        lines = [
            f"当前经济周期: {cycle_names.get(cycle_analysis.cycle, '未知')}",
            f"匹配度评分: {alignment_score:.0f}/100",
        ]

        if alignment_score >= 80:
            lines.append("✓ 持仓配置与当前经济周期高度匹配")
        elif alignment_score >= 60:
            lines.append("⚠️ 持仓配置基本匹配，但有优化空间")
        elif alignment_score >= 40:
            lines.append("⚠️ 持仓配置存在较大偏差，建议调整")
        else:
            lines.append("❌ 持仓配置与当前经济周期严重不匹配，强烈建议调整")

        return " | ".join(lines)

    def format_analysis(self, analysis: AlignmentAnalysis) -> str:
        """格式化分析结果"""
        lines = [
            "=== 持仓匹配度分析 ===\n",
            f"匹配度评分: {analysis.alignment_score:.0f}/100\n",
            f"说明: {analysis.reasoning}\n",
            "\n配置偏差:",
        ]

        for asset_class, deviation in analysis.deviations.items():
            if abs(deviation) > 1:  # 只显示偏差 > 1% 的
                emoji = "🔴" if deviation > self.TOLERANCE else ("🟢" if deviation < -self.TOLERANCE else "⚪")
                lines.append(f"  {emoji} {asset_class.value.upper()}: {deviation:+.1f}%")

        if analysis.recommendations:
            lines.append("\n调仓建议:")
            for rec in analysis.recommendations:
                lines.append(f"  {rec}")

        return "\n".join(lines)
