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

        # 翻译新闻
        print("🌐 翻译英文新闻...")
        self.data["news"] = self._translate_news(self.data["news"])

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
                            "url": item.url if hasattr(item, 'url') else None,
                            "date": pub_date.strftime("%m/%d"),
                        })

        return news[:10]  # 最多10条
    
    def _translate_news(self, news_list: List[Dict]) -> List[Dict]:
        """翻译英文新闻标题为中文"""
        import requests
        
        # 从 OpenClaw 配置读取 bailian API key
        openclaw_config_path = Path.home() / ".openclaw" / "openclaw.json"
        if not openclaw_config_path.exists():
            return news_list
        
        try:
            with open(openclaw_config_path) as f:
                openclaw_config = json.load(f)
            
            bailian_config = openclaw_config.get("models", {}).get("providers", {}).get("bailian", {})
            api_key = bailian_config.get("apiKey")
            
            if not api_key:
                return news_list
            
            # 翻译每条新闻
            for news in news_list:
                title = news.get("title", "")
                source = news.get("source", "")
                
                # 如果标题是英文（简单判断：不包含中文字符）
                if title and not any('\u4e00' <= char <= '\u9fff' for char in title):
                    try:
                        # 调用 bailian API 翻译
                        response = requests.post(
                            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "qwen-turbo",
                                "messages": [
                                    {
                                        "role": "system",
                                        "content": "你是一个专业的财经新闻翻译，将英文标题翻译成简洁的中文，保持专业术语准确。只输出翻译结果，不要添加任何解释。"
                                    },
                                    {
                                        "role": "user",
                                        "content": title
                                    }
                                ],
                                "temperature": 0.3,
                                "max_tokens": 100
                            },
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            translated = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                            if translated:
                                news["title_zh"] = translated.strip()
                    except Exception as e:
                        print(f"  ⚠️ 翻译失败: {e}")
                        news["title_zh"] = title
            
            return news_list
        
        except Exception as e:
            print(f"  ⚠️ 翻译服务不可用: {e}")
            return news_list
    
    def _extract_indices(self, results: Dict) -> Dict:
        """提取股指数据"""
        # 指数映射表
        index_mapping = {
            "^GSPC": "SP500",
            "^DJI": "DJI",
            "^IXIC": "NASDAQ",
            "^RUT": "Russell2000",
            "^HSI": "HangSeng",
            "000001.SS": "Shanghai",
            "399001.SZ": "Shenzhen",
            "000300.SS": "CSI300",
            "^N225": "Nikkei225",
            "^FTSE": "FTSE100",
            "^GDAXI": "DAX",
            "^STI": "STI",
        }
        
        indices = {name: None for name in index_mapping.values()}

        if "yfinance_indices" in results:
            yf_result = results["yfinance_indices"]
            # Accept both success and degraded status
            if yf_result.status in ["success", "degraded"] and yf_result.items:
                for item in yf_result.items:
                    ticker = item.metadata.get("ticker", "")
                    price = item.metadata.get("price")
                    change_pct = item.metadata.get("change_pct")
                    
                    if ticker in index_mapping:
                        index_name = index_mapping[ticker]
                        indices[index_name] = {
                            "price": price,
                            "change_pct": change_pct
                        }

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
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            f"┃  📈 宏观经济日报 - {self.summary['date']}              ┃",
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
            "",
        ]

        # 股指部分 - 按地区分组
        if self.summary["indices"]:
            lines.append("🌍 【全球股指】")
            lines.append("─" * 40)
            
            # 美国市场
            us_indices = ["SP500", "DJI", "NASDAQ", "Russell2000"]
            us_data = [(k, v) for k, v in self.summary["indices"].items() if k in us_indices and v]
            if us_data:
                lines.append("🇺🇸 美国市场")
                for index, value in us_data:
                    lines.append(f"  {self._format_index_name(index)}：{value}")
            
            # 亚洲市场
            asia_indices = ["Shanghai", "Shenzhen", "CSI300", "HangSeng", "Nikkei225", "STI"]
            asia_data = [(k, v) for k, v in self.summary["indices"].items() if k in asia_indices and v]
            if asia_data:
                lines.append("🌏 亚太市场")
                for index, value in asia_data:
                    lines.append(f"  {self._format_index_name(index)}：{value}")
            
            # 欧洲市场
            europe_indices = ["FTSE100", "DAX"]
            europe_data = [(k, v) for k, v in self.summary["indices"].items() if k in europe_indices and v]
            if europe_data:
                lines.append("🇪🇺 欧洲市场")
                for index, value in europe_data:
                    lines.append(f"  {self._format_index_name(index)}：{value}")
            
            lines.append("")

        # 汇率部分
        if self.summary["fx"]:
            lines.append("💱 【汇率】")
            lines.append("─" * 40)
            for pair, rate in self.summary["fx"].items():
                lines.append(f"  {pair}：{rate}")
            lines.append("")

        # 大宗商品部分
        if self.summary["commodities"]:
            lines.append("🛢️ 【大宗商品】")
            lines.append("─" * 40)
            if "gold" in self.summary["commodities"]:
                lines.append(f"  🥇 黄金：{self.summary['commodities']['gold']}")
            if "oil" in self.summary["commodities"]:
                lines.append(f"  🛢️ 原油：{self.summary['commodities']['oil']}")
            lines.append("")

        # 利率部分
        if self.summary["rates"]:
            lines.append("📊 【利率】")
            lines.append("─" * 40)
            if "fed_funds_rate" in self.summary["rates"]:
                lines.append(f"  美联储利率：{self.summary['rates']['fed_funds_rate']}")
            if "treasury_10y" in self.summary["rates"]:
                lines.append(f"  10年期国债：{self.summary['rates']['treasury_10y']}")
            lines.append("")

        # 新闻部分
        if self.summary["news"]:
            lines.append("📰 【近期重要动态】")
            lines.append("─" * 40)

            for i, news in enumerate(self.summary["news"][:6], 1):
                # 优先显示中文翻译
                title = news.get('title_zh') or news.get('title', '')
                source = news.get('source', '')
                url = news.get('url', '')
                date = news.get('date', '')
                
                # 来源映射
                source_map = {
                    "federal_reserve": "美联储",
                    "ecb": "欧洲央行",
                    "boj": "日本央行",
                    "scmp": "南华早报",
                    "forexlive": "ForexLive",
                    "oilprice": "OilPrice",
                }
                source_name = source_map.get(source, source)
                
                lines.append(f"  {i}. [{date}] {title}")
                lines.append(f"     来源：{source_name}")
                if url:
                    lines.append(f"     链接：{url}")
                lines.append("")

        # 免责声明
        lines.extend([
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "┃  ⚠️  免责声明                                     ┃",
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
            "",
            "此信息仅供参考，不构成投资建议。",
            "具体决策请结合个人情况，必要时咨询专业人士。",
            "",
            "─" * 40,
            "🤖 家庭理财助手 | 数据来源: DataHub",
        ])

        return "\n".join(lines)
    
    def _format_index_name(self, index_key: str) -> str:
        """格式化指数名称"""
        name_map = {
            "SP500": "标普500",
            "DJI": "道琼斯",
            "NASDAQ": "纳斯达克",
            "Russell2000": "罗素2000",
            "HangSeng": "恒生指数",
            "Shanghai": "上证综指",
            "Shenzhen": "深证成指",
            "CSI300": "沪深300",
            "Nikkei225": "日经225",
            "FTSE100": "富时100",
            "DAX": "德国DAX",
            "STI": "新加坡STI",
        }
        return name_map.get(index_key, index_key)

    def send_to_feishu(self, webhook_url: str = None, chat_id: str = None) -> bool:
        """发送到飞书
        
        支持两种方式：
        1. 使用 webhook URL（简单，但需要单独的机器人）
        2. 使用飞书开放平台 API（复用现有机器人）
        """
        import requests
        
        report = self.format_report()
        
        # 方式 1: 使用 webhook URL
        if webhook_url:
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
                    print("✅ 已发送到飞书 (webhook)")
                    return True
                else:
                    print(f"❌ 发送失败：{response.status_code}")
                    return False

            except Exception as e:
                print(f"❌ 发送失败：{e}")
                return False
        
        # 方式 2: 使用飞书开放平台 API（复用"家庭理财助手"机器人）
        else:
            # 从 OpenClaw 配置读取飞书应用信息
            openclaw_config_path = Path.home() / ".openclaw" / "openclaw.json"
            if not openclaw_config_path.exists():
                print("❌ 未找到 OpenClaw 配置文件")
                return False
            
            try:
                with open(openclaw_config_path) as f:
                    openclaw_config = json.load(f)
                
                feishu_config = openclaw_config.get("channels", {}).get("feishu", {})
                app_id = feishu_config.get("appId")
                app_secret = feishu_config.get("appSecret")
                
                if not app_id or not app_secret:
                    print("❌ OpenClaw 配置中未找到飞书 appId 或 appSecret")
                    return False
                
                # 如果没有指定 chat_id，从配置中读取或询问用户
                if not chat_id:
                    config_path = Path(__file__).parent.parent / "config" / "feishu.yaml"
                    if config_path.exists():
                        import yaml
                        with open(config_path) as f:
                            config = yaml.safe_load(f)
                            chat_id = config.get("feishu", {}).get("chat_id")
                
                if not chat_id:
                    print("❌ 未配置飞书群聊 chat_id")
                    print("💡 请在 config/feishu.yaml 中配置 chat_id，或使用 --chat-id 参数")
                    return False
                
                # 获取 tenant_access_token
                token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
                token_response = requests.post(
                    token_url,
                    json={
                        "app_id": app_id,
                        "app_secret": app_secret
                    },
                    timeout=10,
                )
                
                if token_response.status_code != 200:
                    print(f"❌ 获取 token 失败：{token_response.status_code}")
                    return False
                
                token_data = token_response.json()
                if token_data.get("code") != 0:
                    print(f"❌ 获取 token 失败：{token_data.get('msg')}")
                    return False
                
                access_token = token_data.get("tenant_access_token")
                
                # 发送消息
                send_url = "https://open.feishu.cn/open-apis/im/v1/messages"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                send_response = requests.post(
                    send_url,
                    headers=headers,
                    params={"receive_id_type": "chat_id"},
                    json={
                        "receive_id": chat_id,
                        "msg_type": "text",
                        "content": json.dumps({"text": report})
                    },
                    timeout=10,
                )
                
                if send_response.status_code == 200:
                    send_data = send_response.json()
                    if send_data.get("code") == 0:
                        print("✅ 已发送到飞书 (家庭理财助手)")
                        return True
                    else:
                        print(f"❌ 发送失败：{send_data.get('msg')}")
                        return False
                else:
                    print(f"❌ 发送失败：{send_response.status_code}")
                    return False
            
            except Exception as e:
                print(f"❌ 发送失败：{e}")
                import traceback
                traceback.print_exc()
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
