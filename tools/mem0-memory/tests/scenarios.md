# Mem0 记忆管理 — 场景验证定义

## 场景 1: 查询家庭净资产
- **用户说**: "我们家现在有多少钱？"
- **期望**: AI 从 Mem0 找到 baseline overview 记忆，返回 ~$1.46M
- **验证**: `memory search -q "家庭净资产"` 返回包含 1457274 或 1.46M 的记录

## 场景 2: 查询单个账户
- **用户说**: "我的活期账户A还有多少钱？"
- **期望**: AI 精确找到活期账户A记忆，返回 ~800K CNY
- **验证**: `memory search -q "活期账户A"` 返回包含 800 的记录

## 场景 3: 投资决策记录（Quick Trigger）
- **用户说**: "今天买了50股苹果，价格190，放在券商账户A"
- **期望**: memory add 写入 investment_decision，包含 ticker=AAPL, qty=50, price=190, account=券商账户A
- **验证**: `memory search -q "苹果 AAPL 买入"` 返回刚写入的记录
- **清理标记**: metadata.test=true

## 场景 4: 投资政策查询
- **用户说**: "我的目标配置比例是什么？再平衡阈值是多少？"
- **期望**: AI 找到 allocation_strategy 记忆，返回现金15%/权益45%/固收30%等
- **验证**: `memory search -q "目标配置比例 再平衡"` 返回包含 15% 45% 30% 的记录

## 场景 5: 告警规则查询
- **用户说**: "什么情况下你会给我发告警？"
- **期望**: AI 找到告警条件记忆，列出5个触发条件
- **验证**: `memory search -q "告警触发条件"` 返回包含 8% 3% 0.25% 的记录

## 场景 6: 记忆更新（资产变化）
- **操作**: 写入一条"测试：活期账户A余额变为 850K CNY"（标记 test=true）
- **期望**: Mem0 应该能区分新旧数据，不覆盖原始 baseline
- **验证**: `memory search -q "活期账户A"` 返回 >=2 条记录（原始 + 更新）
- **清理**: 删除 test=true 的记录

## 场景 7: 按分类过滤
- **操作**: `memory list -c investment_decision`
- **期望**: 只返回 investment_decision 类别的记录（含场景3写入的测试记录）
- **验证**: 所有返回记录的 category 都是 investment_decision

## 场景 8: 删除单条记忆
- **操作**: 删除场景3写入的测试记忆
- **期望**: memory delete 成功，后续 search 不再返回该记录
- **验证**: delete 返回成功，再次 search 不包含该记录

## 场景 9: 记忆统计
- **操作**: `memory stats`
- **期望**: 返回总数、按分类统计、日期范围
- **验证**: 输出包含 total、category 等字段，数字 >= 20

## 场景 10: 语义搜索相关性
- **用户说**: "如果市场崩盘我的组合会怎样？"
- **期望**: 搜索应该返回 alert_rules（提到大盘跌幅3%触发告警）和 allocation_strategy
- **验证**: `memory search -q "市场崩盘 组合影响"` 返回 allocation_strategy 相关记录

## 清理规则
- 所有测试写入的记忆必须带 metadata: `{"test": "true"}`
- 测试完成后执行: `memory search -q "test" -c investment_decision` 找到所有测试记忆
- 逐条删除 test=true 的记忆
- 验证 baseline 记忆未被修改（总数应回到 ~20）
