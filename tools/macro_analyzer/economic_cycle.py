"""
经济周期分析器

基于美林时钟模型，判断当前经济周期阶段：
- 复苏期 (Recovery): GDP↑ 通胀低 → 增持股票
- 扩张期 (Expansion): GDP↑ 通胀↑ → 增持商品/房产
- 滞胀期 (Stagflation): GDP↓ 通胀↑ → 增持现金/黄金
- 衰退期 (Recession): GDP↓ 通胀↓ → 增持债券
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class EconomicCycle(Enum):
    """经济周期阶段"""
    RECOVERY = "recovery"  # 复苏期
    EXPANSION = "expansion"  # 扩张期
    STAGFLATION = "stagflation"  # 滞胀期
    RECESSION = "recession"  # 衰退期


@dataclass
class EconomicIndicator:
    """经济指标"""
    gdp_growth: Optional[float] = None  # GDP 增长率 (%)
    inflation: Optional[float] = None  # 通胀率 (%)
    unemployment: Optional[float] = None  # 失业率 (%)
    interest_rate: Optional[float] = None  # 基准利率 (%)


@dataclass
class CycleAnalysis:
    """周期分析结果"""
    cycle: EconomicCycle
    confidence: float  # 0-100
    indicators: EconomicIndicator
    reasoning: str
    recommended_assets: List[str]


class EconomicCycleAnalyzer:
    """经济周期分析器"""

    def __init__(self):
        self.indicators = EconomicIndicator()

    def set_indicators(
        self,
        gdp_growth: Optional[float] = None,
        inflation: Optional[float] = None,
        unemployment: Optional[float] = None,
        interest_rate: Optional[float] = None,
    ):
        """设置经济指标"""
        if gdp_growth is not None:
            self.indicators.gdp_growth = gdp_growth
        if inflation is not None:
            self.indicators.inflation = inflation
        if unemployment is not None:
            self.indicators.unemployment = unemployment
        if interest_rate is not None:
            self.indicators.interest_rate = interest_rate

    def analyze(self) -> CycleAnalysis:
        """分析当前经济周期"""
        gdp = self.indicators.gdp_growth
        inflation = self.indicators.inflation
        unemployment = self.indicators.unemployment

        # 如果没有足够的指标，返回默认值
        if gdp is None or inflation is None:
            return CycleAnalysis(
                cycle=EconomicCycle.EXPANSION,
                confidence=0,
                indicators=self.indicators,
                reasoning="数据不足，无法判断",
                recommended_assets=["stocks", "bonds", "cash"]
            )

        # 基于 GDP 和通胀判断周期
        cycle, confidence, reasoning = self._determine_cycle(gdp, inflation, unemployment)

        # 根据周期推荐资产
        recommended_assets = self._get_recommended_assets(cycle)

        return CycleAnalysis(
            cycle=cycle,
            confidence=confidence,
            indicators=self.indicators,
            reasoning=reasoning,
            recommended_assets=recommended_assets
        )

    def _determine_cycle(
        self,
        gdp: float,
        inflation: float,
        unemployment: Optional[float]
    ) -> tuple[EconomicCycle, float, str]:
        """判断经济周期"""
        # GDP 增长阈值
        gdp_threshold = 1.0  # 1% 作为增长/衰退的分界

        # 通胀阈值
        inflation_low = 2.0  # 低通胀
        inflation_high = 4.0  # 高通胀

        # 判断逻辑
        if gdp > gdp_threshold:
            if inflation < inflation_low:
                cycle = EconomicCycle.RECOVERY
                confidence = 80
                reasoning = f"GDP 增长 {gdp:.1f}%（>{gdp_threshold}%），通胀 {inflation:.1f}%（<{inflation_low}%），处于复苏期"
            elif inflation > inflation_high:
                cycle = EconomicCycle.EXPANSION
                confidence = 75
                reasoning = f"GDP 增长 {gdp:.1f}%（>{gdp_threshold}%），通胀 {inflation:.1f}%（>{inflation_high}%），处于扩张期"
            else:
                # 通胀在中间，根据失业率判断
                if unemployment and unemployment > 5.0:
                    cycle = EconomicCycle.RECOVERY
                    confidence = 65
                    reasoning = f"GDP 增长 {gdp:.1f}%，通胀 {inflation:.1f}%，失业率较高 {unemployment:.1f}%，偏向复苏期"
                else:
                    cycle = EconomicCycle.EXPANSION
                    confidence = 70
                    reasoning = f"GDP 增长 {gdp:.1f}%，通胀 {inflation:.1f}%，处于扩张期"
        else:
            if inflation > inflation_high:
                cycle = EconomicCycle.STAGFLATION
                confidence = 85
                reasoning = f"GDP 增长 {gdp:.1f}%（<{gdp_threshold}%），通胀 {inflation:.1f}%（>{inflation_high}%），处于滞胀期"
            else:
                cycle = EconomicCycle.RECESSION
                confidence = 80
                reasoning = f"GDP 增长 {gdp:.1f}%（<{gdp_threshold}%），通胀 {inflation:.1f}%（<{inflation_high}%），处于衰退期"

        # 根据失业率调整置信度
        if unemployment is not None:
            if cycle in [EconomicCycle.RECOVERY, EconomicCycle.EXPANSION] and unemployment > 6.0:
                confidence -= 10
                reasoning += f"（失业率 {unemployment:.1f}% 较高，降低置信度）"
            elif cycle in [EconomicCycle.STAGFLATION, EconomicCycle.RECESSION] and unemployment < 4.0:
                confidence -= 10
                reasoning += f"（失业率 {unemployment:.1f}% 较低，降低置信度）"

        return cycle, confidence, reasoning

    def _get_recommended_assets(self, cycle: EconomicCycle) -> List[str]:
        """根据周期推荐资产"""
        recommendations = {
            EconomicCycle.RECOVERY: ["stocks", "real_estate", "commodities"],
            EconomicCycle.EXPANSION: ["commodities", "real_estate", "stocks"],
            EconomicCycle.STAGFLATION: ["cash", "gold", "bonds"],
            EconomicCycle.RECESSION: ["bonds", "cash", "gold"],
        }
        return recommendations.get(cycle, ["stocks", "bonds", "cash"])

    def get_cycle_description(self, cycle: EconomicCycle) -> str:
        """获取周期描述"""
        descriptions = {
            EconomicCycle.RECOVERY: "复苏期：经济增长，通胀低，股票表现最佳",
            EconomicCycle.EXPANSION: "扩张期：经济增长，通胀上升，商品/房产表现最佳",
            EconomicCycle.STAGFLATION: "滞胀期：经济衰退，通胀高企，现金/黄金表现最佳",
            EconomicCycle.RECESSION: "衰退期：经济衰退，通胀下降，债券表现最佳",
        }
        return descriptions.get(cycle, "未知周期")
