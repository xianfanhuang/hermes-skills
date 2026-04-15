# OpenClaw 自动化记忆系统 - 使用说明

> **版本**: 1.0
> **更新时间**: 2026-04-16
> **状态**: ✅ 已部署并测试通过

---

## 🎯 系统概述

OpenClaw 自动化记忆系统解决了"需要人为提醒才写入记忆"的问题，实现了成熟的 Agent 记忆管理范式。

### 核心特性

| 特性 | 状态 | 说明 |
|------|------|------|
| **自动触发** | ✅ | 检测关键字自动记录重要信息 |
| **分层存储** | ✅ | 短期/中期/长期记忆分离 |
| **智能判断** | ✅ | 根据关键字识别重要内容 |
| **对话摘要** | ✅ | Session 结束时自动生成摘要 |
| **用户偏好同步** | ✅ | 自动同步到长期记忆 |
| **记忆归档** | ✅ | 30 天后自动压缩归档 |

---

## 📂 文件结构

```
workspace/
├── scripts/
│   ├── auto-memory.sh      # 自动记忆管理脚本
│   ├── memory-write.sh     # 手动记忆写入工具
│   └── memory-archive.sh   # 记忆归档脚本
├── memory/
│   ├── 2026-04-10.md       # 每日记忆文件
│   ├── 2026-04-16.md       # 当天记忆
│   └── archive/            # 归档目录（30 天+）
├── MEMORY.md               # 长期记忆
└── AUTO_MEMORY_DESIGN.md   # 系统设计文档
```

---

## 🚀 如何使用

### 1. Agent 自动记忆（无需用户操作）

Agent 会在以下情况自动记录记忆：

| 触发条件 | 示例用户消息 | 记录内容 |
|---------|------------|---------|
| 用户偏好 | "我喜欢保守型策略，单笔最大亏损 2%" | 风险偏好设置 |
| 重要决策 | "决定平仓 A50，盈利 +2%" | 交易决策 |
| 学到知识 | "学习到缠论第三类买点的确认方法" | 新知识 |
| 错误教训 | "止损设置太紧，被频繁止损" | 教训总结 |
| 市场观察 | "比特币突破 $73,000" | 市场动态 |
| 对话记录 | "用户询问关于黄金的投资策略" | 对话主题 |

### 2. 手动写入记忆（供 Agent 调用）

```bash
# 记录用户偏好
bash /workspace/projects/workspace/scripts/memory-write.sh "preference" "用户喜欢保守型策略"

# 记录重要决策
bash /workspace/projects/workspace/scripts/memory-write.sh "decision" "决定平仓 USO，触发止损 -5%"

# 记录学到知识
bash /workspace/projects/workspace/scripts/memory-write.sh "knowledge" "学习到缠论中枢理论"

# 记录错误和教训
bash /workspace/projects/workspace/scripts/memory-write.sh "error" "之前的止损设置太紧"
```

### 3. 手动更新今日记忆

```bash
bash /workspace/projects/workspace/scripts/auto-memory.sh
```

### 4. 归档旧记忆

```bash
bash /workspace/projects/workspace/scripts/memory-archive.sh
```

---

## 🔧 Agent 集成

### AGENTS.md 中已配置：

```markdown
## Every Session

... 读取配置文件 ...

**🔄 自动记忆**

在任何重要对话后，自动写入记忆文件，无需用户提醒：

- 用户偏好 → `memory-write.sh "preference"`
- 重要决策 → `memory-write.sh "decision"`
- 学到知识 → `memory-write.sh "knowledge"`
- 错误教训 → `memory-write.sh "error"`
- 市场观察 → `memory-write.sh "observation"`
```

### Session 结束时自动执行：

```markdown
当检测到会话即将结束时：

1. 执行自动记忆脚本
2. 生成会话摘要
3. 更新长期记忆
```

---

## 📊 记忆检索

### Agent 如何检索记忆：

1. **当前 Session**：直接访问对话历史
2. **今天 + 昨天**：自动读取 `memory/YYYY-MM-DD.md`
3. **最近 7 天**：按需读取对应的 memory 文件
4. **长期记忆**：读取 `MEMORY.md`（仅限主会话）
5. **归档记忆**：解压并读取 `memory/archive/*.md.gz`

### 检索优先级：

```
1. Session 上下文（最快）
2. 今天 + 昨天的 Memory（最新）
3. 最近 7 天的 Memory（中期）
4. MEMORY.md（长期）
5. 归档 Memory（历史）
```

---

## ✅ 测试验证

### 已完成的测试：

| 测试项 | 状态 | 结果 |
|-------|------|------|
| 脚本语法检查 | ✅ | 通过 |
| 手动写入记忆 | ✅ | 成功写入 `2026-04-16.md` |
| 自动记忆更新 | ✅ | 成功生成对话摘要 |
| 用户偏好提取 | ✅ | 成功提取并记录 |
| 关键字检测 | ✅ | 检测机制正常 |
| 文件创建 | ✅ | 自动创建 memory 目录 |
| AGENTS.md 集成 | ✅ | 已更新配置 |

### 测试结果示例：

```bash
$ bash /workspace/projects/workspace/scripts/memory-write.sh "preference" "用户 VAN 喜欢保守型策略"

✅ 已写入记忆文件
   文件: /workspace/projects/workspace/memory/2026-04-16.md
   类别: preference
   内容: 用户 VAN 喜欢保守型策略

$ bash /workspace/projects/workspace/scripts/auto-memory.sh

[INFO] ======================================
[INFO] OpenClaw 自动记忆管理
[INFO] 时间: Thu Apr 16 01:10:27 AM CST 2026
[INFO] ======================================
[INFO] 提取用户偏好...
[INFO] 分析最近的 Session...
[INFO] 分析 Session: 3bf0318d-05d2-4548-8767-9a05f7dedd3b.jsonl
[INFO] 生成对话摘要...
[INFO] 更新长期记忆...
[INFO] ✅ 自动记忆更新完成
[INFO] 记忆文件: /workspace/projects/workspace/memory/2026-04-16.md
```

---

## 📈 效果对比

### 改进前：

```
用户说："我喜欢保守型策略，单笔最大亏损 2%"
↓
Agent: "好的，记住了" (但实际上没写进文件)
↓
Session 结束
↓
用户: /new
↓
Agent: "你好！我是 Trading Assistant..."
↓
用户: "我的风险偏好是什么？"
↓
Agent: "抱歉，我不记得了" 😱
```

### 改进后：

```
用户说："我喜欢保守型策略，单笔最大亏损 2%"
↓
Agent: 检测到关键字"偏好"、"亏损"
     ↓
     自动执行: memory-write.sh "preference" "..."
     ↓
     写入: memory/2026-04-16.md
     ↓
     同步: MEMORY.md
     ↓
Agent: "好的，已记录你的风险偏好：保守型，单笔最大亏损 2%" ✅
↓
Session 结束
↓
用户: /new
↓
Agent: 读取 memory/2026-04-16.md
     ↓
     Agent: "你的风险偏好是保守型，单笔最大亏损 2%" ✅
```

---

## 🎓 成熟范式参考

本系统参考了以下成熟的 Agent 记忆系统：

1. **LangChain Memory**
   - ConversationBufferMemory
   - ConversationSummaryMemory
   - VectorStoreMemory

2. **AutoGPT**
   - 事件驱动记忆更新
   - 自动存储关键决策

3. **Mem0 (开源)**
   - 智能记忆管理
   - 自动重要性评估

4. **ChatGPT Custom Instructions**
   - 永久保存用户偏好
   - 自动应用到所有对话

5. **Claude Projects**
   - 项目级记忆
   - 自动引用历史对话

---

## 🔐 安全性

- ✅ 不记录敏感信息（API Key、密码等）
- ✅ 记忆文件本地存储，不上传云端
- ✅ 支持手动删除记忆
- ✅ 归档后的记忆可选择性保留

---

## 🚧 后续优化

### Phase 2（进阶）：

- [ ] 使用 LLM 评估消息重要性（当前仅用关键字）
- [ ] 实现记忆压缩算法
- [ ] 添加向量数据库支持语义检索
- [ ] 实现跨会话关联记忆

### Phase 3（未来）：

- [ ] 记忆冲突检测和解决
- [ ] 记忆可视化界面
- [ ] 记忆导出和导入功能
- [ ] 多用户记忆隔离

---

## 📞 问题反馈

如果遇到问题，请检查：

1. 脚本权限：`chmod +x workspace/scripts/*.sh`
2. 目录权限：`chmod -R 755 workspace/memory/`
3. 查看日志：`tail -f workspace/logs/auto-memory.log`
4. 测试脚本：`bash -n workspace/scripts/auto-memory.sh`

---

*系统设计参考: AUTO_MEMORY_DESIGN.md*
*最后更新: 2026-04-16 01:10*
