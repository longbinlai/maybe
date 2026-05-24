#!/usr/bin/env python3
"""
宏观经济信息收集器

收集、整理、展示宏观经济信息，不提供投资建议。
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add datahub to path
DATAHUB_PATH = Path(__file__).parent.parent.parent.parent / "datahub"
sys.path.insert(0, str(DATAHUB_PATH))

from datahub import SourceRegistry


class MacroInfoCollector:
    """宏观经济信息收集器"""
    
    def __init__(self):
        config_path = DATAHUB_PATH / "config" / "sources.yaml"
        self.registry = SourceRegistry(config_path)
        self.data = {}
        self.summary = {}
    
    def collect_all(self, use_cache: bool = True) -> Dict:
        """收集所有数据"""
        print("🔄 收集宏观经济数据...")
        
        results = self.registry.fetch_all(use_cache=use_cache)
        
        # 整理数据
        self.data = {
            "rates": self._extract_rates(results),
            "fx": self._extract_fx(results),
            "commodities": self._extract_commodities(results),
            "indicators": self._extract_indicators(results),
            "news": self._extract_news(results),
            "indices": self._extract_indices(results),
        }
        
        # 生成摘要
        self.summary = self._generate_summary()
        
        return self.data
    
    def _extract_rates(self, results: Dict) -> Dict:
        """提取利率数据"""
        rates = {
            "fed_funds_rate": None,
            "treasury_10y": None,
            "ecb_rate": None,
            "boj_rate": None,
        }

        import re
        
        # 从新闻中提取央行利率信息
        for source_name, result in results.items():
            # Accept both success and degraded status
            if result.status not in ["success", "degraded"] or not result.items:
                continue

            # 美联储
            if "federal_reserve" in source_name:
                # 查找利率数字
                for item in result.items[:10]:
                    content = (item.content or "").lower()
                    if "rate" in content or "percent" in content or "basis point" in content:
                        # 查找常见的利率格式
                        # 例如: "5.25 percent", "5.25%", "5.25 to 5.50 percent"
                        matches = re.findall(r'(\d+\.\d+)\s*(?:to\s+\d+\.\d+\s+)?(?:percent|%)', item.content)
                        if matches:
                            rates["fed_funds_rate"] = float(matches[0])
                            break

            # ECB
            if "ecb" in source_name:
                for item in result.items[:10]:
                    content = (item.content or "").lower()
                    if "rate" in content or "percent" in content:
                        matches = re.findall(r'(\d+\.\d+)\s*(?:percent|%)', item.content)
                        if matches:
                            rates["ecb_rate"] = float(matches[0])
                            break

            # 日本央行
            if "boj" in source_name:
                for item in result.items[:10]:
                    content = (item.content or "").lower()
                    if "rate" in content or "percent" in content:
                        matches = re.findall(r'(-?\d+\.\d+)\s*(?:percent|%)', item.content)
                        if matches:
                            rates["boj_rate"] = float(matches[0])
                            break

        # 从 YFinance 获取国债收益率
        if "yfinance_rates" in results:
            yf_result = results["yfinance_rates"]
            if yf_result.status in ["success", "degraded"] and yf_result.items:
                for item in yf_result.items:
                    ticker = item.metadata.get("ticker", "")
                    if ticker == "^TNX":  # 10年期国债
                        rates["treasury_10y"] = item.metadata.get("price")

        return rates
    
    def _extract_fx(self, results: Dict) -> Dict:
        """提取汇率数据"""
        fx = {
            "USDCNY": None,
            "USDJPY": None,
            "USDAUD": None,
            "EURUSD": None,
        }

        if "yfinance_fx" in results:
            yf_result = results["yfinance_fx"]
            # Accept both success and degraded status
            if yf_result.status in ["success", "degraded"] and yf_result.items:
                for item in yf_result.items:
                    ticker = item.metadata.get("ticker", "")
                    price = item.metadata.get("price")

                    if ticker == "CNY=X":
                        fx["USDCNY"] = price
                    elif ticker == "JPY=X":
                        fx["USDJPY"] = price
                    elif ticker == "AUD=X":
                        fx["USDAUD"] = price
                    elif ticker == "EURUSD=X":
                        fx["EURUSD"] = price

        return fx

    def _extract_commodities(self, results: Dict) -> Dict:
        """提取大宗商品数据"""
        commodities = {
            "gold": None,
            "oil": None,
            "copper": None,
        }

        if "yfinance_gold" in results:
            yf_result = results["yfinance_gold"]
            # Accept both success and degraded status
            if yf_result.status in ["success", "degraded"] and yf_result.items:
                commodities["gold"] = yf_result.items[0].metadata.get("price")

        if "yfinance_oil" in results:
            yf_result = results["yfinance_oil"]
            # Accept both success and degraded status
            if yf_result.status in ["success", "degraded"] and yf_result.items:
                commodities["oil"] = yf_result.items[0].metadata.get("price")

        return commodities
    
    def _extract_indicators(self, results: Dict) -> Dict:
        """提取经济指标"""
        indicators = {
            "gdp_growth": None,
            "cpi": None,
            "unemployment": None,
            "pmi": None,
        }
        
        # 从新闻中提取
        for source_name, result in results.items():
            if result.status != "success":
                continue
            
            # GDP
            if "bea" in source_name or "gdp" in source_name.lower():
                for item in result.items[:3]:
                    if "gdp" in item.content.lower():
                        import re
                        matches = re.findall(r'GDP.*?(\d+\.?\d*)\s*%', item.content, re.IGNORECASE)
                        if matches:
                            indicators["gdp_growth"] = float(matches[0])
                            break
            
            # CPI
            if "bls" in source_name or "cpi" in source_name.lower():
                for item in result.items[:3]:
                    if "cpi" in item.content.lower():
                        import re
                        matches = re.findall(r'CPI.*?(\d+\.?\d*)\s*%', item.content, re.IGNORECASE)
                        if matches:
                            indicators["cpi"] = float(matches[0])
                            break
            
            # 失业率
            if "bls" in source_name or "unemployment" in source_name.lower():
                for item in result.items[:3]:
                    if "unemployment" in item.content.lower():
                        import re
                        matches = re.findall(r'unemployment.*?(\d+\.?\d*)\s*%', item.content, re.IGNORECASE)
                        if matches:
                            indicators["unemployment"] = float(matches[0])
                            break
        
        return indicators
    
    def _extract_news(self, results: Dict) -> List[Dict]:
        """提取重要新闻"""
        news = []

        # 从新闻源中提取
        news_sources = [
            "federal_reserve",
            "ecb",
            "boj",
            "scmp",
            "forexlive",
            "oilprice",
        ]

        for source_name in news_sources:
            if source_name in results:
                result = results[source_name]
                # Accept both success and degraded status
                if result.status in ["success", "degraded"] and result.items:
                    for item in result.items[:2]:  # 每个源取前2条
                        pub_date = item.published if hasattr(item, 'published') else datetime.now()
                        news.append({
                            "source": source_name,
                            "title": item.title,
                            "date": pub_date.strftime("%m/%d"),
                        })

        return news[:10]  # 最多10条
    
    def _extract_indices(self, results: Dict) -> Dict:
        """提取股指数据"""
        indices = {
            "SP500": None,
            "DJI": None,
            "NASDAQ": None,
            "Shanghai": None,
        }

        if "yfinance_indices" in results:
            yf_result = results["yfinance_indices"]
            # Accept both success and degraded status
            if yf_result.status in ["success", "degraded"] and yf_result.items:
                for item in yf_result.items:
                    ticker = item.metadata.get("ticker", "")
                    price = item.metadata.get("price")
                    change_pct = item.metadata.get("change_pct")

                    if ticker == "^GSPC":
                        indices["SP500"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "^DJI":
                        indices["DJI"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "^IXIC":
                        indices["NASDAQ"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "000001.SS":
                        indices["Shanghai"] = {"price": price, "change_pct": change_pct}

        return indices
    
    def _generate_summary(self) -> Dict:
        """生成信息摘要"""
        summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "rates": {},
            "fx": {},
            "commodities": {},
            "indices": {},
            "news": [],
        }
        
        # 利率
        if self.data["rates"]["fed_funds_rate"]:
            summary["rates"]["fed_funds_rate"] = f"{self.data['rates']['fed_funds_rate']:.2f}%"
        if self.data["rates"]["treasury_10y"]:
            summary["rates"]["treasury_10y"] = f"{self.data['rates']['treasury_10y']:.2f}%"
        
        # 汇率
        for pair, rate in self.data["fx"].items():
            if rate:
                summary["fx"][pair] = f"{rate:.4f}"
        
        # 大宗商品
        if self.data["commodities"]["gold"]:
            summary["commodities"]["gold"] = f"${self.data['commodities']['gold']:.2f}/oz"
        if self.data["commodities"]["oil"]:
            summary["commodities"]["oil"] = f"${self.data['commodities']['oil']:.2f}/bbl"
        
        # 股指
        for index, data in self.data["indices"].items():
            if data:
                change_str = f" ({data['change_pct']:+.2f}%)" if data['change_pct'] else ""
                summary["indices"][index] = f"{data['price']:,.2f}{change_str}"
        
        # 新闻
        summary["news"] = self.data["news"]
        
        return summary
    
    def format_report(self) -> str:
        """格式化报告"""
        if not self.summary:
            self.collect_all()
        
        lines = [
            f"📈 宏观经济信息摘要 - {self.summary['date']}",
            "",
            "═══════════════════════════════════════",
            "📊 关键指标",
            "═══════════════════════════════════════",
            "",
        ]
        
        # 利率
        if self.summary["rates"]:
            lines.append("美国利率")
            if "fed_funds_rate" in self.summary["rates"]:
                lines.append(f"  联邦基金利率：{self.summary['rates']['fed_funds_rate']}")
            if "treasury_10y" in self.summary["rates"]:
                lines.append(f"  10年期国债：{self.summary['rates']['treasury_10y']}")
            lines.append("")
        
        # 汇率
        if self.summary["fx"]:
            lines.append("汇率")
            for pair, rate in self.summary["fx"].items():
                lines.append(f"  {pair}：{rate}")
            lines.append("")
        
        # 大宗商品
        if self.summary["commodities"]:
            lines.append("大宗商品")
            if "gold" in self.summary["commodities"]:
                lines.append(f"  黄金：{self.summary['commodities']['gold']}")
            if "oil" in self.summary["commodities"]:
                lines.append(f"  原油：{self.summary['commodities']['oil']}")
            lines.append("")
        
        # 股指
        if self.summary["indices"]:
            lines.append("股指")
            for index, value in self.summary["indices"].items():
                lines.append(f"  {index}：{value}")
            lines.append("")
        
        # 新闻
        if self.summary["news"]:
            lines.extend([
                "═══════════════════════════════════════",
                "📰 近期重要动态",
                "═══════════════════════════════════════",
                "",
            ])
            
            for news in self.summary["news"][:5]:
                lines.append(f"  • [{news['date']}] {news['title']}")
            
            lines.append("")
        
        # 免责声明
        lines.extend([
            "═══════════════════════════════════════",
            "⚠️  免责声明",
            "═══════════════════════════════════════",
            "",
            "此信息仅供参，不构成投资建议。",
            "具体决策请结合个人情况，必要时咨询专业人士。",
        ])
        
        return "\n".join(lines)
    
    def send_to_feishu(self, webhook_url: str = None) -> bool:
        """发送到飞书"""
        if not webhook_url:
            # 从配置文件读取
            config_path = Path(__file__).parent.parent / "config" / "feishu.yaml"
            if config_path.exists():
                import yaml
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    webhook_url = config.get("feishu", {}).get("webhook_url")
        
        if not webhook_url:
            print("❌ 未配置飞书 webhook URL")
            return False
        
        report = self.format_report()
        
        # 发送到飞书
        import requests
        try:
            response = requests.post(
                webhook_url,
                json={
                    "msg_type": "text",
                    "content": {"text": report}
                },
                timeout=10,
            )
            
            if response.status_code == 200:
                print("✅ 已发送到飞书")
                return True
            else:
                print(f"❌ 发送失败：{response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ 发送失败：{e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="宏观经济信息收集器")
    parser.add_argument("--summary", action="store_true", help="生成信息摘要")
    parser.add_argument("--send-feishu", action="store_true", help="发送到飞书")
    parser.add_argument("--weekly", action="store_true", help="生成每周总结")
    parser.add_argument("--webhook-url", help="飞书 webhook URL")
    parser.add_argument("--no-cache", action="store_true", help="不使用缓存")
    
    args = parser.parse_args()
    
    collector = MacroInfoCollector()
    
    # 收集数据
    collector.collect_all(use_cache=not args.no_cache)
    
    # 生成摘要
    if args.summary or args.send_feishu:
        report = collector.format_report()
        print(report)
        
        # 发送到飞书
        if args.send_feishu:
            collector.send_to_feishu(args.webhook_url)
    
    # 输出 JSON（用于程序处理）
    if not args.summary and not args.send_feishu:
        print(json.dumps(collector.summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
