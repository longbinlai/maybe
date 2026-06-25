#!/usr/bin/env python3
"""
宏观经济信息收集器

收集、整理、展示宏观经济信息，不提供投资建议。
"""

import sys
import os
import json
import argparse
import signal
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from datahub import SourceRegistry, get_config_path, get_cache_dir


# Ollama 翻译服务配置 — 可用环境变量覆盖，默认本地（避免硬编码地址/模型名）。
# 与 mem0/记忆系统统一使用 OLLAMA_HOST。
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"
TRANSLATE_MODEL = os.environ.get("MACRO_TRANSLATE_MODEL", "translategemma:12b")


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

# 翻译系统提示词（含常见术语对照表，提升翻译质量）
TRANSLATION_SYSTEM_PROMPT = (
    "你是金融新闻翻译专家。将英文财经标题翻译成流畅自然的中文。\n"
    "规则：1) 必须翻译所有英文内容，不要保留任何英文单词（股票代码如MU/AVGO/GOOGL保留） "
    "2) 专有名词用中文通用译法 3) 每条独立翻译，不要混合 4) 只输出译文，每行一条。\n\n"
    "常用译法参考：\n"
    "- 机构：Fed=美联储, ECB=欧洲央行, BOJ=日本央行, PBOC=中国人民银行, IMF=国际货币基金组织, OPEC+=欧佩克+\n"
    "- 指数：S&P 500=标普500, Nasdaq=纳斯达克, Dow Jones=道琼斯, Nikkei=日经, Hang Seng=恒生, Russell=罗素\n"
    "- 公司：Micron=美光, Sandisk=闪迪, Apple=苹果, Nvidia=英伟达, Tesla=特斯拉, Microsoft=微软, "
    "Meta=Meta, Amazon=亚马逊, Google/Alphabet=谷歌, Broadcom=博通, AMD=AMD, Intel=英特尔, "
    "Barclays=巴克莱, Morgan Stanley=摩根士丹利, Goldman Sachs=高盛, UBS=瑞银, "
    "SLB=斯伦贝谢, Baker Hughes=贝克休斯, Chevron=雪佛龙, ExxonMobil=埃克森美孚, "
    "TechnipFMC=德希尼布FMC, Valaris=瓦拉里斯, Liberty Energy=自由能源, Seadrill=海钻, "
    "Tenaris=泰纳里斯, Kosmos Energy=科斯莫斯能源, Permian Resources=二叠纪资源\n"
    "- 术语：earnings=财报/盈利, revenue=营收, EPS=每股收益, guidance=业绩指引, "
    "rate cut=降息, rate hike=加息, inflation=通胀, CPI=消费者价格指数, GDP=国内生产总值, "
    "PMI=采购经理指数, treasury yield=国债收益率, bond=债券, futures=期货, "
    "HBM=高带宽存储器, data center=数据中心, semiconductor=半导体, chip=芯片, "
    "Strait of Hormuz=霍尔木兹海峡, Hezbollah=真主党, Lebanon=黎巴嫩, Israel=以色列, Iran=伊朗, "
    "Bitcoin=比特币, gold=黄金, oil/crude=原油, copper=铜, natural gas=天然气, "
    "spot ETF=现货ETF, offshore yuan=离岸人民币, short selling=做空, rally=反弹, plunge=暴跌\n"
    "- 人名：Powell=鲍威尔, Lagarde=拉加德, Trump=特朗普\n"
    "- 注意：stock trades down=股价下跌, what you need to know=你需要了解的信息"
)

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
                OLLAMA_CHAT_URL,
                json={
                    "model": TRANSLATE_MODEL,
                    "messages": [
                        {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"将以下英文财经标题翻译成中文（只输出译文，不要解释）：\n\n{title}"}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 500, "think": False}
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

        # 设置超时（90秒，translategemma:12b 无 thinking，速度较快）
        def timeout_handler(signum, frame):
            raise TimeoutError("Batch translation timeout")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(90)

        try:
            # 构建批量翻译提示
            titles_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles_to_translate)])

            response = requests.post(
                OLLAMA_CHAT_URL,
                json={
                    "model": TRANSLATE_MODEL,
                    "messages": [
                        {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"翻译以下英文标题为中文（全部翻译成中文，不要保留英文，保持编号格式，每行一条）：\n\n{titles_text}\n\n译文："}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 8000, "think": False}
                },
                timeout=80
            )
            response.raise_for_status()
            data = response.json()

            # 解析翻译结果
            translated_text = data.get("message", {}).get("content", "").strip()

            if not translated_text:
                # 模型返回空内容，回退到关键词翻译
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
        self.failed_sources = []  # 追踪失败的数据源
    
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

        results = {}
        self.failed_sources = []  # 重置失败列表

        # 第一阶段：收集新闻数据（RSS/NewsAPI）- 这些不会卡住
        log("📰 第一阶段：收集新闻数据...")
        news_sources = {
            name: source for name, source in self.registry.sources.items()
            if source.__class__.__name__ in ['RSSSource', 'NewsAPISource']
        }

        for name, source in news_sources.items():
            try:
                result = self.registry._fetch_single(name, source, use_cache, timeout)
                if result and result.status != 'failed':
                    results[name] = result
                else:
                    self.failed_sources.append(name)
                    log(f"  ⚠️ {name} 失败，将重试一次...")
                    # 重试一次，使用更短的超时
                    try:
                        retry_result = self.registry._fetch_single(name, source, use_cache, min(timeout, 10))
                        if retry_result and retry_result.status != 'failed':
                            results[name] = retry_result
                            self.failed_sources.remove(name)
                            log(f"  ✓ {name} 重试成功")
                    except Exception as retry_e:
                        log(f"  ❌ {name} 重试也失败: {retry_e}")
            except Exception as e:
                self.failed_sources.append(name)
                log(f"  ⚠️ {name} 失败: {e}")
                # 重试一次
                try:
                    retry_result = self.registry._fetch_single(name, source, use_cache, min(timeout, 10))
                    if retry_result and retry_result.status != 'failed':
                        results[name] = retry_result
                        self.failed_sources.remove(name)
                        log(f"  ✓ {name} 重试成功")
                except Exception as retry_e:
                    log(f"  ❌ {name} 重试也失败: {retry_e}")

        log(f"✓ 新闻数据收集完成：{len(results)} 个源成功，{len(self.failed_sources)} 个失败")
        if self.failed_sources:
            log(f"  失败源: {', '.join(self.failed_sources)}")
        
        # 立即生成新闻部分的摘要
        self.data = {
            "rates": {"fed_funds_rate": None, "treasury_10y": None, "ecb_rate": None, "boj_rate": None},
            "fx": {"USDCNY": None, "USDJPY": None, "USDAUD": None, "AUDCNY": None, "EURUSD": None},
            "commodities": {"gold": None, "oil": None, "copper": None},
            "indicators": {"gdp_growth": None, "cpi": None, "unemployment": None, "pmi": None},
            "news": self._extract_news(results),
            "indices": {name: None for name in ["SP500", "DJI", "NASDAQ", "Russell2000", "HangSeng", "Shanghai", "Shenzhen", "CSI300", "Nikkei225", "FTSE100", "DAX", "STI"]},
            "risk": {"vix": None, "treasury_10y": None, "treasury_5y": None, "treasury_13w": None, "dxy": None},
            "china": {"hs300etf": None, "gold_etf": None, "bond_etf": None, "tracker_fund": None},
        }
        self.summary = self._generate_summary()
        log(f"✓ 已生成新闻摘要：{len(self.summary.get('news', []))} 条")
        
        # 第二阶段：收集价格数据（yfinance）- 这些可能会卡住
        log("💹 第二阶段：收集价格数据...")
        yf_sources = {
            name: source for name, source in self.registry.sources.items()
            if source.__class__.__name__ == 'YFinanceSource'
        }

        yf_success = 0
        for name, source in yf_sources.items():
            try:
                result = self.registry._fetch_single(name, source, use_cache, timeout)
                if result and result.status != 'failed':
                    results[name] = result
                    yf_success += 1
                else:
                    self.failed_sources.append(name)
                    log(f"  ⚠️ {name} 失败，将重试一次...")
                    try:
                        retry_result = self.registry._fetch_single(name, source, use_cache, min(timeout, 10))
                        if retry_result and retry_result.status != 'failed':
                            results[name] = retry_result
                            yf_success += 1
                            self.failed_sources.remove(name)
                            log(f"  ✓ {name} 重试成功")
                    except Exception as retry_e:
                        log(f"  ❌ {name} 重试也失败: {retry_e}")
            except Exception as e:
                self.failed_sources.append(name)
                log(f"  ⚠️ {name} 失败: {e}")
                try:
                    retry_result = self.registry._fetch_single(name, source, use_cache, min(timeout, 10))
                    if retry_result and retry_result.status != 'failed':
                        results[name] = retry_result
                        yf_success += 1
                        self.failed_sources.remove(name)
                        log(f"  ✓ {name} 重试成功")
                except Exception as retry_e:
                    log(f"  ❌ {name} 重试也失败: {retry_e}")

        log(f"✓ 价格数据收集完成：{yf_success} 个源成功")
        
        # 重新生成完整摘要
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
        self.summary = self._generate_summary()

        return self.data

    def _load_from_cache_all(self) -> Dict:
        """从缓存加载所有数据源"""
        results = {}
        cache_dir = self.registry.cache_dir
        
        if not cache_dir or not cache_dir.exists():
            return results
        
        import pickle
        from datetime import datetime, timedelta
        
        # 缓存有效期：24小时
        cache_ttl = timedelta(hours=24)
        
        for source_name in self.registry.sources.keys():
            cache_file = cache_dir / f"{source_name}.pkl"
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                    
                    cache_time = cached_data.get('timestamp', datetime.min)
                    if datetime.now() - cache_time < cache_ttl:
                        results[source_name] = cached_data['result']
                        log(f"  ✓ {source_name} (缓存)")
                    else:
                        log(f"  ⚠️ {source_name} 缓存已过期")
                except Exception as e:
                    log(f"  ⚠️ {source_name} 缓存读取失败: {e}")
        
        return results

    def collect_yfinance_only(self, use_cache: bool = True) -> Dict:
        """只收集 YFinance 数据（跳过 RSS，速度更快）"""
        log("🔄 仅收集 YFinance 数据...")

        results = {}
        
        # 1. 合并获取所有 yfinance 价格数据（一次请求）
        yf_price_result = self._collect_yfinance_prices_merged(use_cache=use_cache)
        if yf_price_result:
            results['yfinance_prices_merged'] = yf_price_result
        
        # 2. 单独获取 yfinance_news（需要逐 ticker 请求）
        try:
            source = self.registry.get_source('yfinance_news')
            if source:
                log("  获取 yfinance_news...")
                results['yfinance_news'] = source.fetch()
        except Exception as e:
            log(f"  ⚠️ yfinance_news 失败: {e}")
        
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

    def _collect_yfinance_prices_merged(self, use_cache: bool = True):
        """合并获取所有 yfinance 价格数据（一次请求）
        
        把所有 yfinance 价格源的 tickers 合并，用 yf.download() 一次性获取，
        避免多次请求触发 Yahoo 限流。
        """
        import yfinance as yf
        import pandas as pd
        from datetime import datetime
        from datahub.core.base_source import DataSourceResult, DataItem, ValidationResult
        
        log("📊 合并获取 yfinance 价格数据...")
        
        # 收集所有 yfinance 价格源的 tickers
        all_tickers = []
        ticker_to_source = {}  # ticker -> 原始数据源名称
        
        yf_price_sources = [
            'yfinance_gold', 'yfinance_oil', 'yfinance_fx',
            'yfinance_indices', 'yfinance_risk', 'yfinance_china'
        ]
        
        for source_name in yf_price_sources:
            try:
                source = self.registry.get_source(source_name)
                if source and hasattr(source, 'tickers'):
                    for ticker in source.tickers:
                        if ticker not in all_tickers:
                            all_tickers.append(ticker)
                            ticker_to_source[ticker] = source_name
            except Exception as e:
                log(f"  ⚠️ 获取 {source_name} 配置失败: {e}")
        
        if not all_tickers:
            log("  ⚠️ 没有找到任何 yfinance 价格 ticker")
            return None
        
        log(f"  合并 {len(all_tickers)} 个 tickers: {', '.join(all_tickers[:5])}...")
        
        # 检查缓存
        cache_dir = self.registry.cache_dir
        cache_file = cache_dir / 'yfinance_prices_merged.pkl'
        
        if use_cache and cache_file.exists():
            try:
                import pickle
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    cache_time = cached_data.get('time', datetime.min)
                    if (datetime.now() - cache_time).total_seconds() < 14400:  # 4小时缓存
                        log("  ✓ 使用缓存数据")
                        return cached_data['result']
            except Exception as e:
                log(f"  ⚠️ 读取缓存失败: {e}")
        
        # 一次性下载所有 tickers（子进程硬超时，避免 yf.download 无限挂起）
        import subprocess
        import pickle as _pickle
        
        tickers_json = json.dumps(all_tickers)
        
        # 用子进程运行 yf.download，超时后强制杀掉
        _yf_worker_script = f'''
import json, sys, warnings
warnings.filterwarnings("ignore")
import yfinance as yf
tickers = json.loads(sys.argv[1])
try:
    df = yf.download(tickers, period="5d", interval="1d", group_by="ticker",
                     auto_adjust=True, progress=False, threads=False, timeout=10)
    if df is not None and not df.empty:
        # 保存结果到临时文件
        import tempfile, pickle
        tmp = tempfile.mktemp(suffix=".pkl")
        with open(tmp, "wb") as f:
            pickle.dump(df, f)
        print(tmp)
    else:
        print("EMPTY")
except Exception as e:
    print(f"ERROR:{{e}}")
'''
        
        df = None
        try:
            log(f"  🔄 下载 {len(all_tickers)} 个 tickers（子进程，30s超时）...")
            proc = subprocess.run(
                [sys.executable, '-c', _yf_worker_script, tickers_json],
                capture_output=True, text=True, timeout=30
            )
            output = proc.stdout.strip()
            if output and not output.startswith('ERROR') and output != 'EMPTY':
                # 读取临时文件中的 DataFrame
                import pickle as _pkl
                with open(output, 'rb') as f:
                    df = _pkl.load(f)
                import os
                os.unlink(output)
                log(f"  ✓ 下载成功")
            elif output == 'EMPTY':
                log(f"  ⚠️ 返回空数据")
            elif output.startswith('ERROR'):
                error_msg = output[6:]
                if 'Too Many Requests' in error_msg or 'RateLimit' in error_msg:
                    log(f"  ⏳ Yahoo 限流，跳过价格数据")
                else:
                    log(f"  ⚠️ yf.download 失败: {error_msg}")
        except subprocess.TimeoutExpired:
            log(f"  ⏰ yfinance 超时(30s)，跳过价格数据")
        except Exception as e:
            log(f"  ⚠️ yfinance 异常: {e}")
        
        if df is None or df.empty:
            log("  ⚠️ yf.download 失败，尝试使用缓存")
            # 尝试使用缓存（包括过期缓存）
            if cache_file.exists():
                try:
                    import pickle
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                        log("  ✓ 使用缓存数据（可能过期）")
                        return cached_data['result']
                except Exception as e:
                    log(f"  ⚠️ 读取缓存也失败: {e}")
            log("  ⚠️ yfinance 完全失败，跳过价格数据，继续获取新闻")
            return None
        
        # 解析数据，按原始数据源分组
        items_by_source = {}  # source_name -> [DataItem]
        is_multi = isinstance(df.columns, pd.MultiIndex)
        
        for ticker in all_tickers:
            try:
                # 提取单个 ticker 的数据
                if is_multi and ticker in df.columns.get_level_values(0):
                    ticker_df = df[ticker].dropna(how='all')
                elif not is_multi:
                    ticker_df = df.dropna(how='all')
                else:
                    continue
                
                if ticker_df.empty or len(ticker_df) < 1:
                    continue
                
                latest = ticker_df.iloc[-1]
                prev = ticker_df.iloc[-2] if len(ticker_df) > 1 else latest
                
                price = latest['Close']
                prev_price = prev['Close']
                
                import math
                if price is None or (isinstance(price, float) and math.isnan(price)):
                    log(f"  ⚠️ {ticker}: 价格为 NaN，跳过")
                    continue
                
                change = price - prev_price
                change_pct = (change / prev_price * 100) if prev_price != 0 else 0
                
                # 确定数据源名称
                source_name = ticker_to_source.get(ticker, 'yfinance_prices_merged')
                
                # 确定 category
                if 'indices' in source_name:
                    category = 'market'
                elif 'risk' in source_name:
                    category = 'risk'
                elif 'fx' in source_name:
                    category = 'forex'
                elif 'gold' in source_name or 'oil' in source_name:
                    category = 'commodity'
                elif 'china' in source_name:
                    category = 'china'
                else:
                    category = 'market'
                
                title = f"{ticker}: ${price:.2f} ({change_pct:+.2f}%)"
                
                item = DataItem(
                    id=DataItem.generate_id('yfinance_prices_merged', ticker, str(ticker_df.index[-1])),
                    source=source_name,  # 保留原始数据源名称，方便后续提取
                    category=category,
                    title=title,
                    content=f"收盘价: ${price:.2f}\n涨跌: ${change:+.2f} ({change_pct:+.2f}%)",
                    url=f"https://finance.yahoo.com/quote/{ticker}",
                    published=ticker_df.index[-1].to_pydatetime() if hasattr(ticker_df.index[-1], 'to_pydatetime') else datetime.now(),
                    metadata={
                        'ticker': ticker,
                        'price': float(price),
                        'change': float(change),
                        'change_pct': float(change_pct),
                        'volume': int(latest['Volume']) if not math.isnan(latest['Volume']) else 0,
                    }
                )
                
                if source_name not in items_by_source:
                    items_by_source[source_name] = []
                items_by_source[source_name].append(item)
                
            except Exception as e:
                log(f"  ⚠️ 解析 {ticker} 数据失败: {e}")
                continue
        
        # 创建合并的 DataSourceResult
        all_items = []
        for items in items_by_source.values():
            all_items.extend(items)
        
        result = DataSourceResult(
            source_name='yfinance_prices_merged',
            source_type='yfinance',
            category='market',
            status='success' if len(all_items) >= 10 else 'degraded',
            items=all_items,
            validation=ValidationResult(is_valid=len(all_items) >= 10, score=len(all_items) * 10)
        )
        
        # 保存缓存
        try:
            import pickle
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'wb') as f:
                pickle.dump({'time': datetime.now(), 'result': result}, f)
        except Exception as e:
            log(f"  ⚠️ 保存缓存失败: {e}")
        
        log(f"  ✓ 成功获取 {len(all_items)} 个价格数据")
        return result

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

        # 数据源状态
        failed_sources = self.summary.get('_failed_sources', [])
        if failed_sources:
            lines.append("⚠️ 【数据源状态】")
            lines.append("─" * 40)
            lines.append(f"  以下 {len(failed_sources)} 个数据源获取失败（已重试）：")
            for source in failed_sources:
                lines.append(f"    ❌ {source}")
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

        # 数据源状态
        failed_sources = s.get('_failed_sources', [])
        if failed_sources:
            blocks.append({"type": "text", "text": f"⚠️ **数据源状态**\n以下 {len(failed_sources)} 个数据源获取失败（已重试）：\n" + "\n".join(f"  ❌ {src}" for src in failed_sources)})
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

    # 硬超时保护：使用 watchdog 线程强制退出
    # yfinance 被限流时在 socket 层挂死，SIGALRM 无法中断 C 级 socket 调用
    HARD_TIMEOUT = 540  # 秒（9分钟，cron 超时 10 分钟，留 1 分钟余量给输出和翻译）

    def _watchdog(timeout_sec, collector_ref, args_ref):
        """Watchdog 线程：超时后强制输出已有数据并退出"""
        import time
        time.sleep(timeout_sec)
        # 超时了，强制输出
        sys.stderr.write(f"\n⏰ 硬超时({timeout_sec}s)！强制输出已有数据...\n")
        if collector_ref.failed_sources:
            sys.stderr.write(f"   失败源: {', '.join(collector_ref.failed_sources)}\n")
        sys.stderr.flush()
        try:
            # 整理已有数据
            if not collector_ref.summary:
                collector_ref.summary = collector_ref._generate_summary()
            # 添加失败信息到摘要
            if collector_ref.failed_sources:
                collector_ref.summary['_failed_sources'] = collector_ref.failed_sources.copy()
            if args_ref.card:
                print(collector_ref.format_card())
            elif args_ref.summary:
                print(collector_ref.format_report())
            else:
                print(json.dumps(collector_ref.summary, indent=2, ensure_ascii=False))
        except Exception as e:
            error_msg = f"⚠️ 数据收集超时"
            if collector_ref.failed_sources:
                error_msg += f"，失败源: {', '.join(collector_ref.failed_sources)}"
            print(json.dumps({"blocks": [{"type": "text", "text": error_msg}]}, ensure_ascii=False))
        os._exit(1)

    # 启动 watchdog 线程
    watchdog_thread = threading.Thread(
        target=_watchdog,
        args=(HARD_TIMEOUT, collector, args),
        daemon=True
    )
    watchdog_thread.start()

    # 收集数据
    try:
        if args.yfinance_only:
            log("仅获取 YFinance 数据（跳过 RSS）...")
            collector.collect_yfinance_only(use_cache=not args.no_cache)
        elif args.no_yfinance:
            log("跳过 YFinance 数据（只获取 RSS/NewsAPI）...")
            collector.collect_rss_only(use_cache=not args.no_cache, timeout=args.timeout, concurrency=args.concurrency)
        else:
            collector.collect_all(use_cache=not args.no_cache, timeout=args.timeout, concurrency=args.concurrency)
    except Exception as e:
        log(f"⚠️ 数据收集异常: {e}")

    # 取消超时
    if hasattr(signal, 'SIGALRM'):
        signal.alarm(0)

    # 输出到 stdout
    if args.card:
        print(collector.format_card())
    elif args.summary:
        print(collector.format_report())
    else:
        print(json.dumps(collector.summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
