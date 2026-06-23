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
from typing import Dict, List, Optional

from datahub import SourceRegistry, get_config_path, get_cache_dir


# 常见英文财经词汇的中文映射（无需 API）
TITLE_TRANSLATIONS = {
    # 机构
    "Fed": "美联储",
    "Federal Reserve": "美联储",
    "ECB": "欧洲央行",
    "European Central Bank": "欧洲央行",
    "BOJ": "日本央行",
    "Bank of Japan": "日本央行",
    "PBOC": "中国人民银行",
    "People's Bank of China": "中国人民银行",
    
    # 政策行动
    "rate hike": "加息",
    "rate cut": "降息",
    "holds rates steady": "维持利率不变",
    "holds rates": "维持利率",
    "maintains rates": "维持利率",
    "signals potential": "暗示可能",
    "signals": "暗示",
    "ultra-loose monetary policy": "超宽松货币政策",
    "loose monetary policy": "宽松货币政策",
    "tight monetary policy": "紧缩货币政策",
    
    # 经济指标
    "inflation": "通胀",
    "GDP": "GDP",
    "PMI": "PMI",
    "CPI": "CPI",
    "unemployment": "失业率",
    "employment": "就业",
    "treasury": "国债",
    "yield": "收益率",
    "manufacturing expansion": "制造业扩张",
    "manufacturing contraction": "制造业收缩",
    "economic growth": "经济增长",
    "economic slowdown": "经济放缓",
    "recession": "衰退",
    
    # 市场
    "S&P 500": "标普500",
    "Nasdaq": "纳斯达克",
    "Dow Jones": "道琼斯",
    "oil": "原油",
    "gold": "黄金",
    "copper": "铜",
    "surge": "飙升",
    "plunge": "暴跌",
    "rally": "反弹",
    "decline": "下跌",
    
    # 地缘政治
    "Strait of Hormuz": "霍尔木兹海峡",
    "ceasefire": "停火",
    "Hezbollah": "真主党",
    "Israel": "以色列",
    "Iran": "伊朗",
    "drone strike": "无人机袭击",
    "Lebanon": "黎巴嫩",
    "Southern Lebanon": "黎巴嫩南部",
    "Middle East": "中东",
    "tensions": "紧张局势",
    
    # 其他常见词汇
    "amid": " amid",
    "concerns": "担忧",
    "potential": "可能",
    "maintains": "维持",
    "shows": "显示",
    "signals": "暗示",
}

# 翻译缓存（避免重复翻译相同的标题）
translation_cache = {}

def translate_title_simple(title: str) -> str:
    """使用关键词映射翻译标题（快速版本）"""
    # 检查缓存
    if title in translation_cache:
        return translation_cache[title]
    
    result = title
    # 按长度排序，先替换长词组，避免部分替换问题
    # 例如：先替换 "Federal Reserve" 再替换 "Fed"
    sorted_translations = sorted(TITLE_TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True)
    for en, zh in sorted_translations:
        # 替换英文关键词（忽略大小写）
        import re
        pattern = re.compile(re.escape(en), re.IGNORECASE)
        result = pattern.sub(zh, result)
    
    # 存入缓存
    translation_cache[title] = result
    return result


def translate_title_llm(title: str) -> str:
    """使用本地 Ollama 模型翻译标题（高质量版本）"""
    # 如果标题主要是中文，直接返回
    if all('\u4e00' <= c <= '\u9fff' or c.isspace() or not c.isalpha() for c in title):
        return title

    try:
        import requests
        import signal

        # 设置超时（30秒）
        def timeout_handler(signum, frame):
            raise TimeoutError("LLM translation timeout")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)

        try:
            response = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "lfm2.5:latest",
                    "messages": [
                        {"role": "system", "content": "Output ONLY the Chinese translation. No explanations. No pinyin. No numbering."},
                        {"role": "user", "content": f"Translate to Chinese: {title}"}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 500, "think": False}
                },
                timeout=25
            )
            response.raise_for_status()
            data = response.json()

            translated = data.get("message", {}).get("content", "").strip()
            return translated if translated else title
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    except Exception as e:
        # 翻译失败时回退到关键词替换
        log(f"⚠️ LLM 翻译失败: {e}，使用关键词替换")
        return translate_title_simple(title)


def translate_titles_batch(titles: List[str]) -> List[str]:
    """批量翻译标题（更高效的版本）"""
    # 过滤出需要翻译的标题
    titles_to_translate = []
    indices = []

    for i, title in enumerate(titles):
        # 如果标题主要是中文，跳过
        if all('\u4e00' <= c <= '\u9fff' or c.isspace() or not c.isalpha() for c in title):
            continue
        titles_to_translate.append(title)
        indices.append(i)

    if not titles_to_translate:
        return titles

    try:
        import requests
        import signal

        # 设置超时（120秒，批量翻译 + thinking 模式）
        def timeout_handler(signum, frame):
            raise TimeoutError("Batch translation timeout")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(120)

        try:
            # 构建批量翻译提示
            titles_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles_to_translate)])

            response = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "lfm2.5:latest",
                    "messages": [
                        {"role": "system", "content": "你是专业的金融新闻翻译。将以下英文财经新闻标题翻译为简洁自然的中文。保留专有名词（如 S&P 500、BABA、ECB）和数字。每行一条，保持原有编号格式。只输出翻译结果，不要解释。"},
                        {"role": "user", "content": f"将以下新闻标题翻译为中文：\n{titles_text}"}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 8000, "think": False}
                },
                timeout=110
            )
            response.raise_for_status()
            data = response.json()

            # 解析翻译结果
            translated_text = data.get("message", {}).get("content", "").strip()

            if not translated_text:
                # 模型返回空内容（thinking 消耗了所有 token），回退到关键词翻译
                log(f"⚠️ LLM 返回空内容，回退到关键词翻译")
                return [translate_title_simple(title) for title in titles]

            translated_lines = [line.strip() for line in translated_text.split("\n") if line.strip()]

            # 提取翻译后的标题（去掉编号）
            translated_titles = []
            for line in translated_lines:
                # 去掉 "1. " 这样的前缀
                if ". " in line:
                    translated_titles.append(line.split(". ", 1)[1])
                else:
                    translated_titles.append(line)

            # 如果翻译结果数量不足，回退到关键词翻译
            if len(translated_titles) < len(titles_to_translate):
                log(f"⚠️ 翻译不完整 ({len(translated_titles)}/{len(titles_to_translate)})，回退到关键词翻译")
                return [translate_title_simple(title) for title in titles]

            # 合并结果
            result = titles.copy()
            for i, idx in enumerate(indices):
                if i < len(translated_titles):
                    result[idx] = translated_titles[i]

            return result
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    except Exception as e:
        # 批量翻译失败时，回退到简单翻译（不调用 LLM）
        log(f"⚠️ 批量翻译失败: {e}，使用简单关键词翻译")
        return [translate_title_simple(title) for title in titles]


# 全局标志：是否在安静模式下运行（用于 cron job）
QUIET_MODE = False


def log(msg: str):
    """进度信息输出到 stderr（不会发送到飞书）"""
    if not QUIET_MODE:
        print(msg, file=sys.stderr)


class MacroInfoCollector:
    """宏观经济信息收集器"""
    
    def __init__(self):
        config_path = get_config_path("sources.yaml")
        cache_dir = get_cache_dir()
        self.registry = SourceRegistry(str(config_path), cache_dir=str(cache_dir))
        self.data = {}
        self.summary = {}
    
    def collect_all(self, use_cache: bool = True, timeout: int = 30, concurrency: int = 4) -> Dict:
        """收集所有数据

        Args:
            use_cache: 是否使用缓存
            timeout: 单个数据源超时时间（秒）
            concurrency: 并发数（1=顺序执行，>1=并发执行）
        """
        log("🔄 收集宏观经济数据...")

        # 设置 fetch_all 的超时和安静模式
        import os
        os.environ['DATAHUB_TIMEOUT'] = str(timeout)

        try:
            results = self.registry.fetch_all(
                use_cache=use_cache, 
                concurrency=concurrency,
                quiet=QUIET_MODE  # 传递安静模式标志
            )
        except Exception as e:
            log(f"⚠️ 数据收集出错: {e}")
            results = {}

        # 整理数据
        self.data = {
            "rates": self._extract_rates(results),
            "fx": self._extract_fx(results),
            "commodities": self._extract_commodities(results),
            "indicators": self._extract_indicators(results),
            "news": self._extract_news(results),
            "indices": self._extract_indices(results),
            "risk": self._extract_risk(results),
            "china": self._extract_china(results),
        }

        # 生成摘要
        self.summary = self._generate_summary()

        return self.data

    def collect_yfinance_only(self, use_cache: bool = True) -> Dict:
        """只收集 YFinance 数据（跳过 RSS，速度更快）"""
        log("🔄 仅收集 YFinance 数据...")

        yfinance_sources = [
            "yfinance_gold", "yfinance_oil", "yfinance_fx",
            "yfinance_indices", "yfinance_risk", "yfinance_china", "yfinance_news"
        ]

        results = {}
        for source_name in yfinance_sources:
            try:
                source = self.registry.get_source(source_name)
                if source:
                    log(f"  获取 {source_name}...")
                    result = source.fetch()
                    results[source_name] = result
            except Exception as e:
                log(f"  ⚠️ {source_name} 失败: {e}")
        
        # 整理数据
        self.data = {
            "rates": self._extract_rates(results),
            "fx": self._extract_fx(results),
            "commodities": self._extract_commodities(results),
            "indicators": self._extract_indicators(results),
            "news": self._extract_news(results),
            "indices": self._extract_indices(results),
            "risk": self._extract_risk(results),
            "china": self._extract_china(results),
        }

        # 生成摘要
        self.summary = self._generate_summary()

        return self.data

    def collect_rss_only(self, use_cache: bool = True, timeout: int = 30, concurrency: int = 4) -> Dict:
        """只收集 RSS/NewsAPI 数据（跳过 YFinance，避免限速）"""
        log("🔄 仅收集 RSS/NewsAPI 数据...")

        # 设置超时
        import os
        os.environ['DATAHUB_TIMEOUT'] = str(timeout)

        # 过滤出非 YFinance 源
        rss_sources = {
            name: source for name, source in self.registry.sources.items()
            if source.__class__.__name__ != 'YFinanceSource'
        }

        log(f"  找到 {len(rss_sources)} 个 RSS/NewsAPI 源")

        try:
            # 使用优先级调度器
            from datahub.core.priority_scheduler import PriorityScheduler, set_quiet_mode
            
            # 设置安静模式
            set_quiet_mode(QUIET_MODE)
            
            scheduler = PriorityScheduler(yf_concurrency=1, rss_concurrency=concurrency)

            # 定义获取函数
            def fetch_func(name, source):
                return self.registry._fetch_single(name, source, use_cache, timeout)

            # 执行调度
            results = scheduler.schedule(
                rss_sources,
                fetch_func,
                yf_sources=set()  # 空集合，表示没有 YF 源
            )
        except Exception as e:
            log(f"⚠️ 数据收集出错: {e}")
            results = {}

        # 整理数据
        self.data = {
            "rates": self._extract_rates(results),
            "fx": self._extract_fx(results),
            "commodities": self._extract_commodities(results),
            "indicators": self._extract_indicators(results),
            "news": self._extract_news(results),
            "indices": self._extract_indices(results),
            "risk": self._extract_risk(results),
            "china": self._extract_china(results),
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
            # Skip None results (from fallback groups)
            if result is None:
                continue
            
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
            "AUDCNY": None,
            "EURUSD": None,
        }

        if "yfinance_fx" in results:
            yf_result = results["yfinance_fx"]
            # Accept both success and degraded status
            if yf_result.status in ["success", "degraded"] and yf_result.items:
                for item in yf_result.items:
                    ticker = item.metadata.get("ticker", "")
                    price = item.metadata.get("price")

                    if ticker in ("USDCNY=X", "CNY=X"):
                        fx["USDCNY"] = price
                    elif ticker in ("USDJPY=X", "JPY=X"):
                        fx["USDJPY"] = price
                    elif ticker in ("USDAUD=X", "AUD=X"):
                        fx["USDAUD"] = price
                    elif ticker == "AUDCNY=X":
                        fx["AUDCNY"] = price
                    elif ticker in ("EURUSD=X", "EUR=X"):
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
            # Skip None results (from fallback groups)
            if result is None:
                continue
            
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

        # 从新闻源中提取（按优先级排序）
        news_sources = [
            ("forexlive", 5),      # 外汇实时新闻 - 取5条
            ("oilprice", 3),       # 油价新闻 - 取3条
            ("scmp", 3),           # 南华早报（亚洲视角）- 取3条
            ("caixin", 3),         # 财新（中国经济）- 取3条
            ("federal_reserve", 2), # 美联储 - 取2条
            ("ecb", 2),            # 欧洲央行 - 取2条
            ("boj", 2),            # 日本央行 - 取2条
        ]

        # 收集所有需要翻译的标题
        all_titles = []
        title_indices = []
        
        for source_name, max_items in news_sources:
            if source_name in results:
                result = results[source_name]
                # Skip None results (from fallback groups)
                if result is None:
                    continue
                # Accept both success and degraded status
                if result.status in ["success", "degraded"] and result.items:
                    for item in result.items[:max_items]:
                        pub_date = item.published if hasattr(item, 'published') else datetime.now()
                        all_titles.append(item.title)
                        title_indices.append({
                            "source": source_name,
                            "item": item,
                            "date": pub_date
                        })

        # 从 yfinance_news 提取
        if "yfinance_news" in results:
            yf_news = results["yfinance_news"]
            if yf_news.status in ["success", "degraded"] and yf_news.items:
                for item in yf_news.items[:10]:  # 取10条
                    pub_date = item.published if hasattr(item, 'published') else datetime.now()
                    all_titles.append(item.title)
                    title_indices.append({
                        "source": "market_news",
                        "item": item,
                        "date": pub_date
                    })

        # 批量翻译所有标题
        if all_titles:
            log(f"🌐 批量翻译 {len(all_titles)} 个新闻标题...")
            translated_titles = translate_titles_batch(all_titles)
        else:
            translated_titles = []

        # 构建新闻列表
        for i, info in enumerate(title_indices):
            if i < len(translated_titles):
                title_zh = translated_titles[i]
            else:
                title_zh = translate_title_simple(info["item"].title)  # 回退到简单翻译
            
            news.append({
                "source": info["source"],
                "title": info["item"].title,
                "title_zh": title_zh,
                "url": info["item"].url if hasattr(info["item"], 'url') else None,
                "date": info["date"].strftime("%m/%d"),
                "summary": info["item"].description[:200] if hasattr(info["item"], 'description') and info["item"].description else None,
            })

        return news[:15]  # 最多15条

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

    def _extract_risk(self, results: Dict) -> Dict:
        """提取风险与利率指标"""
        risk = {
            "vix": None,
            "treasury_10y": None,
            "treasury_5y": None,
            "treasury_13w": None,
            "dxy": None,
        }

        if "yfinance_risk" in results:
            yf_result = results["yfinance_risk"]
            if yf_result.status in ["success", "degraded"] and yf_result.items:
                for item in yf_result.items:
                    ticker = item.metadata.get("ticker", "")
                    price = item.metadata.get("price")
                    change_pct = item.metadata.get("change_pct")

                    if ticker == "^VIX":
                        risk["vix"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "^TNX":
                        risk["treasury_10y"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "^FVX":
                        risk["treasury_5y"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "^IRX":
                        risk["treasury_13w"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "DX-Y.NYB":
                        risk["dxy"] = {"price": price, "change_pct": change_pct}

        return risk

    def _extract_china(self, results: Dict) -> Dict:
        """提取中国市场指标"""
        china = {
            "hs300etf": None,
            "gold_etf": None,
            "bond_etf": None,
            "tracker_fund": None,
        }

        if "yfinance_china" in results:
            yf_result = results["yfinance_china"]
            if yf_result.status in ["success", "degraded"] and yf_result.items:
                for item in yf_result.items:
                    ticker = item.metadata.get("ticker", "")
                    price = item.metadata.get("price")
                    change_pct = item.metadata.get("change_pct")

                    if ticker == "510300.SS":
                        china["hs300etf"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "518880.SS":
                        china["gold_etf"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "511010.SS":
                        china["bond_etf"] = {"price": price, "change_pct": change_pct}
                    elif ticker == "2800.HK":
                        china["tracker_fund"] = {"price": price, "change_pct": change_pct}

        return china
    
    def _generate_summary(self) -> Dict:
        """生成信息摘要"""
        summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "rates": {},
            "fx": {},
            "commodities": {},
            "indices": {},
            "risk": {},
            "china": {},
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

        # 风险指标
        for key, data in self.data["risk"].items():
            if data:
                change_str = f" ({data['change_pct']:+.2f}%)" if data['change_pct'] else ""
                if key in ["treasury_10y", "treasury_5y", "treasury_13w"]:
                    summary["risk"][key] = f"{data['price']:.3f}%{change_str}"
                else:
                    summary["risk"][key] = f"{data['price']:.2f}{change_str}"

        # 中国市场
        china_names = {
            "hs300etf": "沪深300ETF",
            "gold_etf": "黄金ETF",
            "bond_etf": "国债ETF",
            "tracker_fund": "盈富基金",
        }
        for key, data in self.data["china"].items():
            if data:
                change_str = f" ({data['change_pct']:+.2f}%)" if data['change_pct'] else ""
                name = china_names.get(key, key)
                summary["china"][name] = f"¥{data['price']:.3f}{change_str}"

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

        # 风险指标部分
        if self.summary["risk"]:
            lines.append("⚠️ 【风险与利率指标】")
            lines.append("─" * 40)
            risk_names = {
                "vix": "VIX恐慌指数",
                "treasury_10y": "10年期国债收益率",
                "treasury_5y": "5年期国债收益率",
                "treasury_13w": "13周国债收益率",
                "dxy": "美元指数(DXY)",
            }
            for key, value in self.summary["risk"].items():
                name = risk_names.get(key, key)
                lines.append(f"  {name}：{value}")
            lines.append("")

        # 中国市场部分
        if self.summary["china"]:
            lines.append("🇨🇳 【中国市场】")
            lines.append("─" * 40)
            for name, value in self.summary["china"].items():
                lines.append(f"  {name}：{value}")
            lines.append("")

        # 新闻部分
        if self.summary["news"]:
            lines.append("📰 【近期重要动态】")
            lines.append("─" * 40)

            # 来源映射
            source_map = {
                "federal_reserve": "美联储",
                "ecb": "欧洲央行",
                "boj": "日本央行",
                "scmp": "南华早报",
                "caixin": "财新",
                "forexlive": "ForexLive",
                "oilprice": "OilPrice",
                "market_news": "市场新闻",
            }

            for i, news in enumerate(self.summary["news"][:15], 1):  # 显示最多15条
                # 优先显示中文翻译
                title = news.get('title_zh') or news.get('title', '')
                source = news.get('source', '')
                url = news.get('url', '')
                date = news.get('date', '')
                summary = news.get('summary', '')

                source_name = source_map.get(source, source)

                lines.append(f"  {i}. [{date}] {title}")
                lines.append(f"     来源：{source_name}")
                
                # 显示摘要（如果有）
                if summary:
                    # 截断过长的摘要
                    if len(summary) > 150:
                        summary = summary[:147] + "..."
                    lines.append(f"     摘要：{summary}")
                
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

    def format_card(self) -> str:
        """输出 OpenClaw presentation JSON 格式"""
        import json as _json
        if not self.summary:
            self.collect_all()

        s = self.summary
        blocks = []

        # 标题
        blocks.append({"type": "text", "text": f"📈 宏观经济日报 — {s['date']}"})
        blocks.append({"type": "divider"})

        # 全球股指
        us_indices = ["SP500", "DJI", "NASDAQ", "Russell2000"]
        asia_indices = ["Shanghai", "Shenzhen", "CSI300", "HangSeng", "Nikkei225", "STI"]
        europe_indices = ["FTSE100", "DAX"]

        us_data = [(k, v) for k, v in s["indices"].items() if k in us_indices and v]
        asia_data = [(k, v) for k, v in s["indices"].items() if k in asia_indices and v]
        europe_data = [(k, v) for k, v in s["indices"].items() if k in europe_indices and v]

        if us_data or asia_data or europe_data:
            blocks.append({"type": "text", "text": "🌍 **全球股指**"})
            if us_data:
                lines = [f"🇺🇸 {self._format_index_name(k)}：{v}" for k, v in us_data]
                blocks.append({"type": "text", "text": "\n".join(lines)})
            if asia_data:
                lines = [f"🌏 {self._format_index_name(k)}：{v}" for k, v in asia_data]
                blocks.append({"type": "text", "text": "\n".join(lines)})
            if europe_data:
                lines = [f"🇪🇺 {self._format_index_name(k)}：{v}" for k, v in europe_data]
                blocks.append({"type": "text", "text": "\n".join(lines)})
            blocks.append({"type": "divider"})

        # 汇率 + 大宗商品
        market_lines = []
        if s["fx"]:
            fx_str = "  ".join(f"{pair}：{rate}" for pair, rate in s["fx"].items())
            market_lines.append(f"💱 {fx_str}")
        if "gold" in s["commodities"]:
            market_lines.append(f"🥇 黄金：{s['commodities']['gold']}")
        if "oil" in s["commodities"]:
            market_lines.append(f"🛢️ 原油：{s['commodities']['oil']}")
        if market_lines:
            blocks.append({"type": "text", "text": "💰 **汇率与大宗商品**"})
            blocks.append({"type": "text", "text": "\n".join(market_lines)})
            blocks.append({"type": "divider"})

        # 利率 + 风险指标
        rate_lines = []
        risk_names = {
            "vix": "VIX恐慌指数",
            "treasury_10y": "10年期国债收益率",
            "treasury_5y": "5年期国债收益率",
            "treasury_13w": "13周国债收益率",
            "dxy": "美元指数(DXY)",
        }
        if "fed_funds_rate" in s["rates"]:
            rate_lines.append(f"美联储利率：{s['rates']['fed_funds_rate']}")
        for key, value in s["risk"].items():
            name = risk_names.get(key, key)
            rate_lines.append(f"{name}：{value}")
        if rate_lines:
            blocks.append({"type": "text", "text": "📊 **利率与风险指标**"})
            blocks.append({"type": "text", "text": "\n".join(rate_lines)})
            blocks.append({"type": "divider"})

        # 中国市场
        if s["china"]:
            china_lines = [f"{name}：{value}" for name, value in s["china"].items()]
            blocks.append({"type": "text", "text": "🇨🇳 **中国市场**"})
            blocks.append({"type": "text", "text": "\n".join(china_lines)})
            blocks.append({"type": "divider"})

        # 新闻
        source_map = {
            "federal_reserve": "美联储", "ecb": "欧洲央行", "boj": "日本央行",
            "scmp": "南华早报", "caixin": "财新", "forexlive": "ForexLive",
            "oilprice": "OilPrice", "market_news": "市场新闻",
        }
        news_lines = []
        for news in s["news"][:10]:  # 限制10条避免太长
            title = news.get('title_zh') or news.get('title', '')
            source = source_map.get(news.get('source', ''), news.get('source', ''))
            date = news.get('date', '')
            url = news.get('url', '')
            line = f"[{date}] {title}"
            if url:
                line += f"\n来源：{source} | [链接]({url})"
            else:
                line += f"\n来源：{source}"
            news_lines.append(line)
        if news_lines:
            blocks.append({"type": "text", "text": "📰 **近期重要动态**"})
            blocks.append({"type": "text", "text": "\n".join(news_lines)})
            blocks.append({"type": "divider"})

        # 免责声明
        blocks.append({"type": "context", "text": "🤖 家庭理财助手 | 数据来源: DataHub | 仅供参考，不构成投资建议"})

        presentation = {"blocks": blocks}
        return _json.dumps(presentation, ensure_ascii=False)

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

def main():
    parser = argparse.ArgumentParser(description="宏观经济信息收集器")
    parser.add_argument("--summary", action="store_true", help="生成信息摘要（输出到 stdout）")
    parser.add_argument("--no-cache", action="store_true", help="不使用缓存")
    parser.add_argument("--timeout", type=int, default=30, help="单个数据源超时时间（秒）")
    parser.add_argument("--concurrency", type=int, default=4, help="并发数（1=顺序，>1=并发）")
    parser.add_argument("--yfinance-only", action="store_true", help="只获取 YFinance 数据（跳过 RSS）")
    parser.add_argument("--no-yfinance", action="store_true", help="跳过 YFinance 数据（只获取 RSS/NewsAPI）")
    parser.add_argument("--quiet", action="store_true", help="安静模式：不输出进度信息到 stderr（用于 cron job）")
    parser.add_argument("--card", action="store_true", help="输出 OpenClaw 卡片 JSON（配合 openclaw message send --presentation 使用）")

    args = parser.parse_args()

    # 设置安静模式
    global QUIET_MODE
    QUIET_MODE = args.quiet
    
    # 同时设置 SourceRegistry 的安静模式
    from datahub.core.source_registry import set_registry_quiet_mode
    set_registry_quiet_mode(QUIET_MODE)

    collector = MacroInfoCollector()

    # 收集数据
    if args.yfinance_only:
        log("仅获取 YFinance 数据（跳过 RSS）...")
        collector.collect_yfinance_only(use_cache=not args.no_cache)
    elif args.no_yfinance:
        log("跳过 YFinance 数据（只获取 RSS/NewsAPI）...")
        collector.collect_rss_only(use_cache=not args.no_cache, timeout=args.timeout, concurrency=args.concurrency)
    else:
        collector.collect_all(use_cache=not args.no_cache, timeout=args.timeout, concurrency=args.concurrency)

    # 输出到 stdout
    if args.card:
        print(collector.format_card())
    elif args.summary:
        print(collector.format_report())
    else:
        print(json.dumps(collector.summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
