# OpenClaw Memory 管理策略分析与改进建议

## 当前 Memory 架构

### 1. 三层结构

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent 对话层                               │
│  - memory_get / memory_search 工具                           │
│  - 自动注入 MEMORY.md 内容到每次对话                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              MEMORY.md（唯一数据源）                          │
│  位置: ~/.openclaw/workspace/MEMORY.md                       │
│  - 纯文本 Markdown 格式                                      │
│  - Agent 直接读写这个文件                                    │
│  - 包含模板 + 实际记录                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           SQLite（搜索引擎索引）                              │
│  位置: ~/.openclaw/memory/main.sqlite                        │
│  表结构:                                                     │
│  - files: 跟踪被索引的文件（仅 MEMORY.md）                    │
│  - chunks: 文本分块 + embedding 向量                         │
│  - chunks_fts: 全文搜索索引（FTS5）                           │
│  - chunks_vec: 向量相似度搜索索引                             │
│  - embedding_cache: 缓存 embedding 计算结果                   │
│  - meta: 索引配置信息                                        │
└─────────────────────────────────────────────────────────────┘
```

### 2. 当前配置

```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "provider": "ollama",
        "model": "qwen3-embedding:0.6b"
      }
    }
  }
}
```

**Embedding 模型**: qwen3-embedding:0.6b (1024 维向量)  
**索引策略**: 400 token 分块，80 token 重叠  
**搜索模式**: 语义搜索 + 全文搜索

### 3. 工作流

```
1. 用户与 Agent 对话
   ↓
2. OpenClaw 自动注入 MEMORY.md 全文到对话上下文
   ↓
3. Agent 执行任务（如 collect_macro_info.py）
   ↓
4. Agent 使用 write/edit 工具追加新记录到 MEMORY.md
   ↓
5. OpenClaw 检测文件变更，触发重新索引
   ↓
6. MEMORY.md 被切分为 chunks → 生成 embedding → 写入 SQLite
   ↓
7. 下次 memory_search 时可以语义搜索
```

---

## 当前问题分析

### 1. 单文件存储的局限性

| 问题 | 描述 | 影响 |
|------|------|------|
| **无限增长** | MEMORY.md 会越来越大，没有归档机制 | 上下文窗口消耗增加 |
| **全文注入** | 每次对话都加载完整 MEMORY.md | Token 浪费，成本高 |
| **格式不一致** | Agent 直接 append，没有验证 | 搜索质量下降 |
| **无结构化查询** | 无法做精确查询（如"所有债券决策"） | 分析困难 |

### 2. 角色冲突

MEMORY.md 同时承担两个矛盾的角色：

```
角色 A: 上下文注入
- 需要保持简短（节省 token）
- 只包含"最重要的"信息
- 频繁更新

角色 B: 历史记录
- 需要不断追加
- 包含所有细节
- 永久保存
```

**核心矛盾**: 这两个需求是互斥的。

### 3. Dreaming 功能未启用

OpenClaw 有一个 **Dreaming（做梦）** 机制，用于：
- 短期记忆 → 长期记忆的晋升
- 自动整理和归纳对话历史
- 生成"记忆日记"

**当前状态**: Dreaming: off

---

## 改进方案

### 方案 1: 分层记忆架构（推荐）

```
┌─────────────────────────────────────────────────────────────┐
│              Layer 1: 工作记忆（Working Memory）              │
│  文件: MEMORY.md                                             │
│  内容: 仅包含模板 + 最近 7 天的摘要                           │
│  大小: 控制在 2000 token 以内                                 │
│  更新: 每日自动归档旧记录                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓ 归档
┌─────────────────────────────────────────────────────────────┐
│              Layer 2: 历史记忆（Historical Memory）           │
│  文件: memory/YYYY-MM-DD.md（每日文件）                       │
│  内容: 当天的完整记录                                         │
│  更新: Agent 追加写入                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓ 索引
┌─────────────────────────────────────────────────────────────┐
│              Layer 3: 语义索引（Semantic Index）              │
│  文件: SQLite (main.sqlite)                                  │
│  内容: 所有历史文件的 embedding                               │
│  查询: memory_search 语义搜索                                │
└─────────────────────────────────────────────────────────────┘
```

**优点**:
- MEMORY.md 保持精简，节省 token
- 历史记录完整保存
- 语义搜索仍然可用

**实现步骤**:
1. 创建 cron 任务：每日 23:59 归档旧记录
2. 更新 SKILL.md：指导 Agent 写入日期文件而非 MEMORY.md
3. 修改索引配置：包含 memory/ 目录

### 方案 2: 启用 Dreaming 功能

OpenClaw 内置的 Dreaming 机制可以自动：
- 从对话中提取重要信息
- 生成"记忆日记"（dreaming diary）
- 晋升短期记忆到长期记忆

**启用配置**（需要研究正确的配置方式）:

```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "provider": "ollama",
        "model": "qwen3-embedding:0.6b",
        "dreaming": {
          "enabled": true,
          "schedule": "0 3 * * *",  // 每天凌晨 3 点
          "diary": true
        }
      }
    }
  }
}
```

**Dreaming 工作流**:
```
白天: 正常对话 → 生成对话历史
         ↓
凌晨 3 点: Dreaming 启动
         ↓
分析对话历史 → 提取重要信息 → 生成日记
         ↓
晋升到 MEMORY.md（如果需要）
```

### 方案 3: 结构化数据存储（长期方案）

为投资决策创建独立的 SQLite 数据库：

```sql
-- 投资决策表
CREATE TABLE investment_decisions (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    action TEXT NOT NULL,  -- buy/sell/rebalance/hold
    account TEXT NOT NULL,
    ticker TEXT NOT NULL,
    quantity REAL,
    price REAL,
    total_value REAL,
    rationale TEXT,
    market_context TEXT,
    expected_outcome TEXT,
    confidence INTEGER,
    status TEXT,  -- active/closed/reviewing
    actual_result TEXT,
    evaluation TEXT,
    lesson TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 市场事件表
CREATE TABLE market_events (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    category TEXT NOT NULL,
    market TEXT NOT NULL,
    key_data TEXT,
    sentiment TEXT,
    impact_sectors TEXT,
    relevance TEXT,
    source TEXT,
    url TEXT,
    our_action TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 周度回顾表
CREATE TABLE weekly_reviews (
    id INTEGER PRIMARY KEY,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    market_environment TEXT,
    operations TEXT,
    decision_evaluation TEXT,
    portfolio_analysis TEXT,
    investment_advice TEXT,
    next_week_outlook TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**优点**:
- 精确查询（如"所有债券决策"）
- 统计分析（如"决策成功率"）
- 历史对比

**缺点**:
- 需要额外的 Skill 来管理数据库
- 与 OpenClaw 的 memory 系统不集成

---

## 推荐实施方案

### 短期（立即可做）

1. **修复 MEMORY.md 增长问题**
   - 创建 cron 任务：每日 23:59 归档旧记录
   - 将 7 天前的记录移到 `memory/YYYY-MM-DD.md`
   - MEMORY.md 只保留模板 + 最近 7 天摘要

2. **优化 Agent 指令**
   - 更新 SKILL.md：指导 Agent 写入日期文件
   - 添加验证：确保记录格式正确

3. **启用 Dreaming 功能**（如果配置可行）
   - 研究正确的配置方式
   - 设置每日凌晨自动做梦

### 中期（1-2 周）

1. **创建 memory-archive Skill**
   - 自动归档旧记录
   - 清理 MEMORY.md
   - 维护索引

2. **优化索引配置**
   - 包含 memory/ 目录
   - 调整分块大小（当前 400 token 可能太大）

### 长期（1-2 月）

1. **评估是否需要结构化数据库**
   - 如果 MEMORY.md + 语义搜索足够，则不需要
   - 如果需要精确查询和统计分析，则创建独立数据库

2. **创建投资决策分析 Skill**
   - 查询历史决策
   - 计算成功率
   - 生成洞察报告

---

## 参考设计

### 1. OpenClaw 官方文档

- [Memory Search](https://docs.openclaw.ai/memory/search)
- [Dreaming](https://docs.openclaw.ai/memory/dreaming)
- [Session Memory Hook](https://docs.openclaw.ai/automation/hooks#session-memory)

### 2. 业界最佳实践

**MemGPT / Letta**:
- 分层记忆（Core Memory + Archival Memory + Recall Memory）
- 自动压缩和归档
- 智能检索

**LangChain Memory**:
- ConversationBufferMemory（完整历史）
- ConversationSummaryMemory（摘要）
- ConversationBufferWindowMemory（滑动窗口）
- VectorStoreRetrieverMemory（向量检索）

**AutoGPT**:
- 短期记忆（对话历史）
- 长期记忆（向量数据库）
- 永久记忆（文件系统）

### 3. 关键原则

1. **分层存储**: 工作记忆（快）+ 历史记忆（慢但完整）
2. **自动归档**: 旧数据自动移到低成本存储
3. **智能检索**: 语义搜索 + 关键词搜索
4. **定期整理**: Dreaming / Summarization
5. **验证机制**: 确保写入数据的格式和质量

---

## 下一步行动

1. ✅ **Embedding 已修复**: 使用 Ollama qwen3-embedding:0.6b
2. ⏳ **研究 Dreaming 配置**: 找到正确的启用方式
3. ⏳ **设计归档机制**: 创建 cron 任务自动归档
4. ⏳ **更新 SKILL.md**: 指导 Agent 使用新的记忆结构

---

## 附录：当前 MEMORY.md 分析

### 文件统计

- **文件大小**: 8371 bytes
- **行数**: 约 310 行
- **索引分块**: 8 chunks（每块约 400 token）
- **Embedding 缓存**: 16 entries

### 内容结构

```
1. AI 使用说明（模板和规则）
2. 当前投资组合（目标配置）
3. 市场事件（模板 + 实际记录）
4. 决策记录（模板 + 实际记录）
5. 周度回顾（模板）
6. 月度分析（模板）
7. 投资洞察（模板 + 实际记录）
```

### 增长预测

- **当前**: 8 KB
- **1 个月后**（假设每天 1 条市场事件）: ~15 KB
- **3 个月后**: ~25 KB
- **6 个月后**: ~40 KB

**结论**: 如果不归档，半年后 MEMORY.md 将消耗大量 token。

---

**文档版本**: 1.0  
**最后更新**: 2026-05-25  
**作者**: OpenClaw Assistant
