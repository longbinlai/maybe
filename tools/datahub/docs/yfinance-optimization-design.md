# YFinance 数据获取优化方案 — 技术设计文档

## 1. 现状分析

### 当前架构

```
MacroInfoCollector.collect_all()
  └─ SourceRegistry.fetch_all(concurrency=4)
       ├─ Phase 1: YFinance 源 → 串行执行（已有，但无优先级排序）
       │    ├─ yfinance_gold
       │    ├─ yfinance_oil
       │    ├─ yfinance_fx
       │    ├─ yfinance_indices
       │    ├─ yfinance_risk
       │    ├─ yfinance_china
       │    └─ yfinance_news
       └─ Phase 2: RSS/NewsAPI 源 → 并发执行 (workers=4)
```

### 已存在的问题

| 问题 | 影响 |
|------|------|
| YFinance 源之间无优先级区分 | 新闻可能先于股指获取，浪费限速配额 |
| 无动态股票价格获取 | `daily_sync.py` 独立调 yf.Ticker()，与 DataHub 重复请求 |
| 重试间隔过短 (`2^attempt * 3` = 3s, 6s) | 容易持续触发 429 |
| 缓存 14400s (4h) 对新闻源不够灵活 | 新闻 2h 合理，但股指日内可更长 |
| YF 源与 RSS 源共享 concurrency 参数 | 语义混淆 |

## 2. 设计方案总览

### 核心思路：分阶段 + 优先级排序 + 自适应限速

```
SourceRegistry.fetch_all()
  │
  ├─ Phase 0: 非 YF 源并发获取（与 YF 并行，不阻塞）
  │
  ├─ Phase 1: YF 关键数据 — 股指 + 风险指标（串行，delay=3s）
  │    ├─ yfinance_indices    [priority=1]
  │    └─ yfinance_risk       [priority=1]
  │
  ├─ Phase 2: YF 市场数据 — 汇率 + 商品（串行，delay=3s）
  │    ├─ yfinance_fx         [priority=2]
  │    ├─ yfinance_gold       [priority=2]
  │    ├─ yfinance_oil        [priority=2]
  │    └─ yfinance_china      [priority=2]
  │
  ├─ Phase 3: 持仓股票价格 — 从 Maybe API 获取 ticker 列表后批量获取
  │    └─ yfinance_holdings   [priority=3]  ← 动态生成
  │
  └─ Phase 4: YF 新闻（最易触发限速，放最后）
       └─ yfinance_news       [priority=4]
```

### 关键设计决策

1. **不修改 `BaseDataSource` / `YFinanceSource` 类结构** — 只改 SourceRegistry 调度逻辑
2. **优先级通过 YAML 配置中的 `fetch_priority` 字段声明** — 不硬编码
3. **动态注册 holdings 源** — 在 fetch 时查询 Maybe API，运行时注入
4. **Phase 0 与 Phase 1 并行启动** — RSS 源在后台线程池执行，不等待 YF

## 3. 数据结构设计

### 3.1 YAML 配置扩展

在 `sources.yaml` 中为每个 yfinance 源增加 `fetch_priority` 字段：

```yaml
sources:
  yfinance_indices:
    type: yfinance
    category: market
    priority: high            # 现有：业务优先级（用于 UI 显示）
    fetch_priority: 1         # 新增：获取顺序（1=最先，数字越小越先）
    fetch_phase: critical     # 新增：阶段标签（用于日志和监控）
    yf_concurrency: 1         # 新增：YF 源内部并发（1=串行）
    cache_ttl: 14400
    retry:                    # 新增：每个源可配置重试策略
      max_retries: 3
      base_delay: 5           # 基础延迟秒数
      backoff_multiplier: 2.5 # 退避倍数
    # ... 其余不变

  yfinance_news:
    type: yfinance
    fetch_priority: 4         # 最后获取
    fetch_phase: best_effort  # 尽力而为
    cache_ttl: 10800          # 3h（从 2h 增加到 3h）
    retry:
      max_retries: 2
      base_delay: 8
      backoff_multiplier: 3.0
    # ...
```

### 3.2 新增数据结构：FetchPlan

```python
@dataclass
class FetchPriority:
    """单个源的获取优先级配置"""
    source_name: str
    priority: int              # 1-4，越小越先
    phase: str                 # critical / important / standard / best_effort
    retry_max: int = 3
    retry_base_delay: float = 5.0
    retry_backoff: float = 2.5

@dataclass
class FetchPlan:
    """分阶段获取计划"""
    # Phase 0: 与 YF 并行执行的源
    parallel_sources: List[str]         # RSS, NewsAPI 等

    # Phase 1-4: YF 源按 fetch_priority 分组排序
    yf_phases: Dict[int, List[str]]     # {1: [...], 2: [...], ...}

    # 动态源（运行时注入）
    dynamic_sources: List[str] = field(default_factory=list)
```

### 3.3 动态 Holdings 源

运行时从 Maybe API 获取持仓 ticker，动态创建 `YFinanceSource`：

```python
def _create_holdings_source(self) -> Optional[YFinanceSource]:
    """从 Maybe API 获取持仓列表，创建动态 YF 源"""
    try:
        from maybe_cli.client import MaybeClient
        client = MaybeClient()  # 从环境变量读取配置
        holdings_data = client.holdings()
        tickers = list({
            h.get("security", {}).get("ticker", "")
            for h in holdings_data.get("holdings", [])
            if h.get("security", {}).get("ticker")
        })
        client.close()

        if not tickers:
            return None

        config = {
            "category": "portfolio",
            "priority": "medium",
            "fetch_priority": 3,
            "fetch_phase": "standard",
            "enabled": True,
            "cache_ttl": 14400,
            "retention_days": 365,
            "tickers": sorted(tickers),
            "data_type": "price",
            "period": "5d",
            "interval": "1d",
            "validation": {
                "min_items": 1,
                "max_age_days": 1,
            },
        }
        return YFinanceSource("yfinance_holdings", config)

    except Exception as e:
        print(f"⚠️  无法获取持仓列表: {e}")
        return None
```

## 4. 获取流程设计

### 4.1 主流程伪代码

```python
def fetch_all(self, use_cache=True, cache_ttl=3600, concurrency=4,
              yf_concurrency=1) -> Dict[str, DataSourceResult]:
    """
    分阶段获取所有数据源

    Args:
        use_cache: 是否使用缓存
        cache_ttl: 默认缓存 TTL
        concurrency: 非 YF 源并发数
        yf_concurrency: YF 源并发数（建议 1，即串行）
    """
    # 0. 清理过期缓存
    if self.cache_dir:
        self._prune_cache(cache_ttl)

    # 1. 构建获取计划
    plan = self._build_fetch_plan()

    # 2. 动态注入 holdings 源
    self._inject_dynamic_sources(plan)

    results = {}

    # 3. Phase 0: 非 YF 源后台并发（不阻塞 YF）
    parallel_executor = None
    parallel_futures = {}
    if plan.parallel_sources:
        parallel_executor = ThreadPoolExecutor(
            max_workers=min(concurrency, len(plan.parallel_sources))
        )
        for name in plan.parallel_sources:
            source = self.sources[name]
            future = parallel_executor.submit(
                self._fetch_single, name, source, use_cache, cache_ttl
            )
            parallel_futures[name] = future

    # 4. Phase 1-4: YF 源分阶段串行
    for phase_num in sorted(plan.yf_phases.keys()):
        phase_sources = plan.yf_phases[phase_num]
        phase_label = self._phase_label(phase_num)
        print(f"📊 Phase {phase_num} ({phase_label}): {', '.join(phase_sources)}")

        for name in phase_sources:
            source = self.sources.get(name)
            if not source:
                continue

            # 获取该源的 retry 配置
            retry_config = self._get_retry_config(source)

            result = self._fetch_with_retry(
                name, source, use_cache, cache_ttl, retry_config
            )
            results[name] = result

            # 源之间加延迟（最后一个不等待）
            if name != phase_sources[-1] or phase_num < max(plan.yf_phases.keys()):
                delay = retry_config.retry_base_delay
                time.sleep(delay)

    # 5. 收集 Phase 0 结果
    if parallel_executor:
        for name, future in parallel_futures.items():
            try:
                results[name] = future.result(timeout=60)
            except Exception as e:
                source = self.sources[name]
                results[name] = DataSourceResult(
                    source_name=name,
                    source_type=source.__class__.__name__,
                    category=source.category,
                    status='failed',
                    error=str(e)
                )
        parallel_executor.shutdown(wait=False)

    return results
```

### 4.2 构建获取计划

```python
def _build_fetch_plan(self) -> FetchPlan:
    """根据源配置构建分阶段获取计划"""
    parallel = []
    yf_phases = defaultdict(list)

    for name, source in self.sources.items():
        is_yf = source.__class__.__name__ == 'YFinanceSource'

        if not is_yf:
            parallel.append(name)
        else:
            # 从源配置读取 fetch_priority
            priority = source.config.get('fetch_priority', 2)  # 默认 2
            yf_phases[priority].append(name)

    # 每个 phase 内按名称排序（保证确定性）
    for phase in yf_phases:
        yf_phases[phase].sort()

    return FetchPlan(
        parallel_sources=parallel,
        yf_phases=dict(yf_phases),
    )
```

### 4.3 带自适应重试的获取

```python
def _fetch_with_retry(self, source_name, source, use_cache, cache_ttl,
                      retry_config) -> DataSourceResult:
    """
    带自适应重试的获取

    策略：
    - 第一次失败：等待 base_delay * backoff^1 秒
    - 第二次失败：等待 base_delay * backoff^2 秒
    - 如果是 429 (Too Many Requests)：额外等待 30s
    - 最后一次失败：回退到过期缓存
    """
    max_retries = retry_config.retry_max
    base_delay = retry_config.retry_base_delay
    backoff = retry_config.retry_backoff

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = self._fetch_single(
                source_name, source, use_cache, cache_ttl
            )

            # _fetch_single 内部已处理缓存回退
            # 如果是 degraded 状态（缓存回退），不算失败
            if result.status in ('success', 'degraded'):
                if attempt > 0:
                    print(f"✅ {source_name}: 第 {attempt+1} 次尝试成功")
                return result

            # status == 'failed'
            last_error = result.error

        except Exception as e:
            last_error = str(e)

        # 判断是否需要重试
        if attempt < max_retries:
            delay = base_delay * (backoff ** attempt)

            # 429 限速特殊处理：额外等待
            if last_error and "Too Many Requests" in str(last_error):
                delay = max(delay, 30)  # 至少等 30 秒
                print(f"⏳ {source_name}: 限速! 等待 {delay:.0f}s (attempt {attempt+1}/{max_retries})")
            else:
                print(f"⏳ {source_name}: 重试等待 {delay:.0f}s (attempt {attempt+1}/{max_retries})")

            time.sleep(delay)

    # 所有重试用尽 — _fetch_single 内部已处理缓存回退
    print(f"❌ {source_name}: {max_retries} 次重试均失败")
    return self._fetch_single(source_name, source, use_cache, cache_ttl)
```

## 5. 重试与缓存策略

### 5.1 重试参数配置（YAML 级别）

| 阶段 | 源 | max_retries | base_delay | backoff | 最坏情况总等待 |
|------|-----|-------------|------------|---------|---------------|
| Phase 1 | indices, risk | 3 | 5s | 2.5x | 5 + 12.5 + 31.25 = 48.75s |
| Phase 2 | fx, gold, oil, china | 3 | 5s | 2.5x | 同上 |
| Phase 3 | holdings | 3 | 5s | 2.5x | 同上 |
| Phase 4 | news | 2 | 8s | 3.0x | 8 + 24 = 32s |

### 5.2 缓存 TTL 调整

| 源类型 | 当前 TTL | 建议 TTL | 理由 |
|--------|----------|----------|------|
| yfinance_indices | 14400 (4h) | 14400 (4h) | 不变，日内够用 |
| yfinance_risk | 14400 (4h) | 14400 (4h) | 不变 |
| yfinance_fx | 14400 (4h) | 21600 (6h) | 汇率日内变化小 |
| yfinance_gold/oil | 14400 (4h) | 21600 (6h) | 商品波动可控 |
| yfinance_china | 14400 (4h) | 21600 (6h) | ETF 价格 |
| yfinance_holdings | N/A (新增) | 21600 (6h) | 持仓价格每天同步一次 |
| yfinance_news | 7200 (2h) | 10800 (3h) | 减少新闻请求频率 |

### 5.3 429 限速处理

```python
# yfinance_source.py 中的 _retry_on_rate_limit 改造
_REQUEST_DELAY = 3.0       # 从 2.0 增加到 3.0
_MAX_RETRIES = 3           # 从 2 增加到 3

def _retry_on_rate_limit(func, max_retries=_MAX_RETRIES, source_name=""):
    """遇到 429 时指数退避重试，增加抖动避免雷群效应"""
    import random

    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries and "Too Many Requests" in str(e):
                # 指数退避 + 随机抖动
                base_wait = (2.5 ** attempt) * 5  # 5, 12.5, 31.25
                jitter = random.uniform(0, base_wait * 0.3)
                wait = base_wait + jitter
                print(f"⏳ [{source_name}] 限速等待 {wait:.1f}s (attempt {attempt+1})...")
                time.sleep(wait)
                continue
            raise
```

## 6. 文件修改清单

### 需要修改的文件

| 文件 | 修改内容 | 风险 |
|------|----------|------|
| `datahub/core/source_registry.py` | 重写 `fetch_all()`，新增 `_build_fetch_plan()`, `_fetch_with_retry()`, `_inject_dynamic_sources()` | 中（核心路径） |
| `datahub/sources/yfinance_source.py` | 调整 `_REQUEST_DELAY`, `_MAX_RETRIES`, `_retry_on_rate_limit` 参数 | 低 |
| `config/sources.yaml` | 增加 `fetch_priority`, `fetch_phase`, `retry` 配置项 | 低 |
| `datahub/core/base_source.py` | `BaseDataSource.__init__()` 读取新配置字段（可选） | 低 |

### 新增文件

| 文件 | 用途 |
|------|------|
| `datahub/core/fetch_plan.py` | `FetchPlan`, `FetchPriority` 数据结构 |
| `datahub/sources/holdings_source.py` | 动态 holdings 源的工厂函数 |

### 不需要修改的文件

- `cli.py` — 只调用 `fetch_all()`，接口不变
- `collect_macro_info.py` — 只调用 `fetch_all()`，接口不变
- `history_store.py` — 数据持久化层，不受影响
- `rss_source.py`, `newsapi_source.py` — 非 YF 源不受影响

## 7. 配置方式选择：YAML 扩展 vs 代码硬编码

**选择：YAML 扩展**

理由：
1. 现有架构已是 YAML 配置驱动，保持一致
2. 优先级调整无需改代码、无需重新部署
3. 可以为不同环境（开发/生产）使用不同配置
4. `retry` 策略按源配置，灵活度高

YAML 向后兼容策略：
- 所有新字段都有默认值（`fetch_priority=2`, `fetch_phase="standard"`）
- 旧配置文件中没有新字段时，行为与当前一致
- `_build_fetch_plan()` 对缺少新字段的源自动降级

## 8. 向后兼容性保证

```python
# source_registry.py 中的兼容性处理

def _build_fetch_plan(self) -> FetchPlan:
    """
    兼容逻辑：
    - 没有 fetch_priority 的 YF 源 → 默认 priority=2
    - 没有 fetch_phase 的 YF 源 → 默认 phase="standard"
    - 没有 retry 配置的源 → 使用全局默认值
    """
    DEFAULT_RETRY = {
        "max_retries": 3,
        "base_delay": 5.0,
        "backoff_multiplier": 2.5,
    }
    # ...
```

### 接口兼容性

`fetch_all()` 的签名扩展（新增参数都有默认值）：

```python
def fetch_all(
    self,
    use_cache: bool = True,
    cache_ttl: int = 3600,
    concurrency: int = 4,
    # 新增参数（全部有默认值）
    yf_concurrency: int = 1,
    enable_holdings: bool = True,       # 是否动态注入 holdings 源
    holdings_api_url: str = None,       # Maybe API URL（默认从环境变量读）
    holdings_api_key: str = None,       # Maybe API Key（默认从环境变量读）
) -> Dict[str, DataSourceResult]:
```

调用方（`MacroInfoCollector`, `cli.py`）无需任何修改。

## 9. 监控与可观测性

### 9.1 执行日志增强

```
📊 Phase 1 (critical): yfinance_indices, yfinance_risk
  🔄 yfinance_indices: 获取数据...
  ✅ yfinance_indices: 12 tickers, 耗时 2.3s
  ⏳ 延迟 5.0s...
  🔄 yfinance_risk: 获取数据...
  ✅ yfinance_risk: 5 tickers, 耗时 1.8s
📊 Phase 2 (important): yfinance_china, yfinance_fx, yfinance_gold, yfinance_oil
  🔄 yfinance_china: 获取数据...
  ⏳ 限速等待 32.5s (attempt 1/3)...
  ✅ yfinance_china: 4 tickers, 耗时 35.1s (含重试)
  ...
📊 Phase 3 (standard): yfinance_holdings [动态]
  🔍 从 Maybe API 获取持仓列表: 8 个 ticker
  🔄 yfinance_holdings: 获取数据...
  ✅ yfinance_holdings: 8 tickers, 耗时 2.1s
📊 Phase 4 (best_effort): yfinance_news
  🔄 yfinance_news: 获取数据...
  ⏳ 限速! 等待 30.0s (attempt 1/2)...
  ♻️ yfinance_news: 回退到过期缓存 (status → degraded)
```

### 9.2 HistoryStore 日志字段扩展

```python
# history_store.log_fetch() 增加字段
self.history_store.log_fetch(
    source_name,
    status,
    items_count,
    duration_ms=fetch_duration_ms,
    error=result.error,
    # 新增
    phase=fetch_phase,        # critical / important / standard / best_effort
    attempt_count=attempts,   # 实际尝试次数
    retry_wait_ms=retry_ms,   # 重试等待总时间
)
```

## 10. 风险评估

| 风险 | 概率 | 缓解措施 |
|------|------|----------|
| Maybe API 不可用导致 holdings 源注入失败 | 低 | 静默跳过，不影响其他源 |
| Phase 0 与 Phase 1 并行时线程池竞争 | 低 | Phase 0 用独立 executor，不共享 |
| 总获取时间变长（串行 + 重试） | 中 | 缓存命中率提高可补偿；RSS 并行不阻塞 |
| 429 仍然触发 | 中 | 3s 间隔 + 指数退避 + 抖动，大幅降低概率 |
| 旧 YAML 配置缺字段 | 低 | 全部字段有默认值，向后兼容 |

## 11. 实施步骤

1. **Step 1**: 修改 `sources.yaml` 添加 `fetch_priority` 和 `retry` 字段
2. **Step 2**: 创建 `fetch_plan.py` 定义数据结构
3. **Step 3**: 修改 `source_registry.py` 的 `fetch_all()` 实现分阶段获取
4. **Step 4**: 调整 `yfinance_source.py` 的限速参数
5. **Step 5**: 创建 `holdings_source.py` 动态 holdings 源工厂
6. **Step 6**: 集成测试，验证分阶段执行和重试逻辑
7. **Step 7**: 更新 `collect_macro_info.py` 的 `_extract_*` 方法以处理 holdings 数据

## 12. 预期收益

| 指标 | 当前 | 优化后 |
|------|------|--------|
| YF 429 错误率 | ~30% 的 fetch 触发 | <5% |
| 股指数据获取成功率 | ~85% | >99% |
| 缓存命中率 | ~40% | ~70%（TTL 延长 + 减少失败导致的缓存失效） |
| 总获取时间 | ~45s（含失败重试） | ~60s（含延迟），但成功率大幅提升 |
| 持仓价格覆盖 | 无（独立脚本） | 集成到 DataHub 统一管道 |
