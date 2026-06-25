# Memory 系统架构总结

## 概述

家庭理财系统使用**两套独立的记忆系统**，各有不同的用途和存储机制：

1. **OpenClaw 内置 Memory** - 会话日志和人类可审计记录
2. **Mem0 (自定义 CLI)** - 语义搜索和结构化分析

两套系统都使用本地 Ollama 的 `qwen3-embedding:0.6b` 模型生成向量嵌入，避免依赖外部 API。

---

## 1. OpenClaw 内置 Memory

### 用途
- 会话上下文存储
- 每日对话日志（Markdown 文件）
- 人类可审计记录
- Agent 的短期记忆

### 存储机制
```
Markdown 文件 → 分块 → Embedding → SQLite + sqlite-vec
```

- **文件位置**: `~/.openclaw/workspace/memory/*.md`
- **索引存储**: `~/.openclaw/memory/main.sqlite`
- **向量维度**: 1024

### 配置
```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "provider": "ollama",
        "model": "qwen3-embedding:0.6b",
        "remote": {
          "baseUrl": "http://localhost:11434"
        },
        "fallback": "none"
      }
    }
  }
}
```

### 当前状态
- ✅ Provider: ollama
- ✅ Model: qwen3-embedding:0.6b
- ✅ Indexed: 1 file, 1 chunk
- ✅ Vector dims: 1024
- ✅ Embeddings: ready
- ✅ FTS: ready

### 使用方式
```bash
# 查看状态
openclaw memory status

# 重建索引
openclaw memory status --index --agent main

# 搜索记忆
openclaw memory search --query "余额更新" --agent main
```

---

## 2. Mem0 (自定义 CLI)

### 用途
- 语义搜索（投资决策、经验教训）
- 结构化分析（投资组合洞察）
- 长期记忆（周度/月度回顾）
- 自动标签分类

### 存储机制
```
Memory → LLM 提取 → Embedding → Qdrant 向量数据库
```

- **向量数据库**: Qdrant (localhost:6333)
- **Collection**: `family_finance_memory`
- **向量维度**: 1024
- **LLM 模型**: 百炼 `qwen3.7-plus` (1M context)
- **Embedding 模型**: Ollama `qwen3-embedding:0.6b`

### 配置
```yaml
# tools/mem0-memory/mem0_memory/config/mem0.yaml
mem0:
  vector_store:
    provider: qdrant
    config:
      host: localhost
      port: 6333
      collection_name: family_finance_memory
      embedding_model_dims: 1024

  llm:
    provider: openai
    config:
      model: qwen3.7-plus
      api_key: ${OPENAI_API_KEY}
      openai_base_url: ${OPENAI_API_BASE}

  embedder:
    provider: ollama
    config:
      model: qwen3-embedding:0.6b
      ollama_base_url: ${OLLAMA_HOST}
      embedding_dims: 1024
```

### 当前状态
- ✅ Total memories: 5
- ✅ Categories: investment_style, lesson_learned, portfolio_insight
- ✅ Search similarity: 0.45-0.61

### 使用方式
```bash
# 列出所有记忆
~/pyenv/maybe/bin/memory list

# 添加记忆
~/pyenv/maybe/bin/memory add --category "investment_style" --content "..."

# 搜索记忆
~/pyenv/maybe/bin/memory search --query "investment policy"

# 查看统计
~/pyenv/maybe/bin/memory stats
```

---

## 两套系统的分工

| 场景 | 使用系统 | 原因 |
|------|---------|------|
| 会话日志、每日记录 | OpenClaw Memory | 人类可读的 Markdown 文件 |
| 投资决策语义搜索 | Mem0 | 需要语义相似度和结构化 metadata |
| 经验教训检索 | Mem0 | 需要按 category 分类和相似度排序 |
| 投资组合分析 | Mem0 | 需要结构化数据和长期记忆 |
| Agent 短期上下文 | OpenClaw Memory | OpenClaw 内置机制 |
| 周度/月度回顾 | Mem0 | 需要长期存储和分析 |

---

## 关键修复记录

### 问题 1: Mem0 默认模型错误
- **现象**: Mem0 写入失败，提示 "gpt-4o-mini 模型不可用"
- **原因**: `mem0.yaml` 中 LLM 配置的默认模型是 `gpt-4o-mini`
- **修复**: 将默认模型改为 `qwen3.7-plus`，移除回退机制

### 问题 2: OpenClaw Memory 索引失败
- **现象**: OpenClaw memory 显示 "Embeddings: unavailable" 和 "Vector search: paused"
- **原因**: 缺少 `agents.defaults.memorySearch` 配置
- **修复**: 
  1. 添加 `memorySearch` 配置到 `openclaw.json`
  2. 运行 `openclaw memory status --index --agent main` 重建索引

### 问题 3: 环境变量未传播
- **现象**: Cron job 和 OpenClaw gateway 运行时找不到正确的模型配置
- **原因**: `.env` 文件中的配置没有自动加载到执行环境
- **修复**: 
  1. 在 `mem0.yaml` 中硬编码模型名称（不依赖环境变量）
  2. 确保 `~/.openclaw/service-env/ai.openclaw.gateway.env` 包含所有必要环境变量

---

## 环境变量配置

### 必需的环境变量

```bash
# OpenAI 兼容 API (百炼)
export OPENAI_API_KEY="sk-xxx"
export OPENAI_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"

# Ollama
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_EMBED_MODEL="qwen3-embedding:0.6b"

# Mem0
export MEM0_TELEMETRY="false"

# Qdrant
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
```

### 配置文件位置

1. **项目级**: `<项目根目录>/.env`（即 maybe 仓库根目录下的 `.env`）
2. **OpenClaw Gateway**: `~/.openclaw/service-env/ai.openclaw.gateway.env`
3. **Mem0 CLI**: `~/.config/maybe-finance/mem0/mem0.yaml`（持久化用户配置，首次运行时自动从包内模板复制）
   - ⚠️ 不要编辑 `site-packages/mem0_memory/config/mem0.yaml`——那只是默认模板，`pip install/upgrade` 会覆盖它。
   - 记忆分类白名单以代码 `mem0_memory/client.py` 的 `ACTIVE_CATEGORIES` 为准；yaml 里的 `categories` 仅供展示。

---

## 验证检查清单

- [x] OpenClaw memory provider 设置为 ollama
- [x] OpenClaw memory model 设置为 qwen3-embedding:0.6b
- [x] OpenClaw memory 索引已重建 (1/1 files, 1 chunks)
- [x] OpenClaw memory 搜索正常工作
- [x] Mem0 LLM 设置为 qwen3.7-plus
- [x] Mem0 Embedding 设置为 qwen3-embedding:0.6b
- [x] Mem0 向量维度为 1024
- [x] Mem0 搜索正常工作 (相似度 0.45-0.61)
- [x] 环境变量正确配置
- [x] OpenClaw gateway 重启并加载新配置

---

## 未来优化方向

1. **记忆同步**: 考虑将 OpenClaw Memory 的重要内容自动同步到 Mem0
2. **记忆清理**: 定期清理过期的 OpenClaw Memory 文件
3. **记忆分类**: 扩展 Mem0 的 category 系统，支持更细粒度的分类
4. **记忆可视化**: 创建 Web UI 查看和搜索记忆
5. **记忆导出**: 支持将记忆导出为 Markdown 或 JSON 格式

---

## 参考文档

- [OpenClaw Memory 配置](https://docs.openclaw.ai/configuration/memory)
- [Mem0 官方文档](https://docs.mem0.ai/)
- [Ollama Embedding 模型](https://ollama.ai/library/qwen3-embedding)
- [Qdrant 向量数据库](https://qdrant.tech/documentation/)
