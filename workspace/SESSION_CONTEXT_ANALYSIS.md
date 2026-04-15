# Session 上下文保持问题深度分析

> **问题核心**: 用户希望开启新 session 后能自动访问之前的聊天记录
> **用户期望**: 不应该因为 `/new` 就不知道之前的事了

---

## 🎯 用户的核心关注点

```
用户不关心：
❌ 是否写进 memory 文件
❌ 什么时候写进记忆

用户关心：
✅ 聊天记录是否一直保存
✅ 开启新 session 后能否自动访问之前的聊天记录
✅ 为什么 `/new` 后就不知道之前的事了
```

---

## 📊 OpenClaw 的实际机制

### 1. Session 文件（聊天记录）

**位置**: `/workspace/projects/agents/main/sessions/*.jsonl`

**特点**:
- ✅ **一直保存**: 所有聊天记录都在 Session 文件中
- ✅ **永久保存**: 不会被自动删除（除非手动清理）
- ✅ **完整记录**: 包含所有用户消息、助手回复、工具调用等

**验证**:
```bash
# 查看有多少个 session 文件
ls -la /workspace/projects/agents/main/sessions/ | wc -l
# 输出: 35 个 session 文件

# 查看 session 文件内容
head -5 /workspace/projects/agents/main/sessions/3bf0318d-*.jsonl
```

---

### 2. `/new` 的实际行为

**当你执行 `/new` 时**:

```
旧 Session: 3bf0318d-05d2-4548-8767-9a05f7dedd3b.jsonl
├─ 用户消息: "今天做的事没有写进记忆吗"
├─ 助手回复: "让我检查一下今天的记忆文件..."
└─ 完整对话历史...

    用户执行: /new
         ↓
新 Session: 新的 UUID.jsonl
├─ 系统消息: "Run your Session Startup sequence..."
├─ 助手回复: "Hey Captain! 你的交易助手已上线..."
└─ ❌ 没有加载旧 session 的历史
```

**关键问题**:
- ✅ 旧 session 文件仍然存在
- ✅ 旧 session 的聊天记录完整保存
- ❌ 新 session **不会自动加载**旧 session 的历史

---

### 3. 为什么新 session 不能自动访问旧 session？

**技术原因**:

| 原因 | 说明 |
|------|------|
| **Session 隔离设计** | 每个 session 是独立的对话上下文 |
| **上下文窗口限制** | 模型的上下文窗口有限，不能无限加载历史 |
| **性能考虑** | 每次新 session 加载所有历史会很慢 |
| **隐私保护** | 新 session 应该是"干净"的开始 |

**OpenClaw 的设计哲学**:
- `/new` = 完全重新开始
- `/reset` = 保留 session ID 但清空对话历史
- 旧 session 历史可以通过工具手动访问

---

## 🔧 OpenClaw 的解决方案：session-memory Hook

### Hook 机制

OpenClaw 有一个内置的 `session-memory` hook，可以在 `/new` 或 `/reset` 时自动保存 session 上下文。

**状态**: ✅ 已启用

```bash
$ openclaw hooks list
Hooks (4/4 ready)
💾 session-memory ✓ Ready
  Save session context to memory when /new or /reset command is issued
```

**功能**:
- 触发时机: `command:new`, `command:reset`
- 提取内容: 最后 15 条用户/助手消息
- 输出格式: `<workspace>/memory/YYYY-MM-DD-slug.md`
- 文件命名: 使用 LLM 生成描述性 slug

**配置**:
```json
{
  "hooks": {
    "internal": {
      "entries": {
        "session-memory": {
          "enabled": true
        }
      }
    }
  }
}
```

---

### session-memory Hook 的限制

| 限制 | 说明 | 影响 |
|------|------|------|
| **只保存 15 条消息** | 不是完整历史，只是最近的消息 | 可能丢失更早的重要信息 |
| **保存到 memory 文件** | 不是直接加载到新 session | 需要配置才能自动读取 |
| **需要手动启用** | 默认可能未启用 | 用户不知道这个功能 |
| **文件名自动生成** | 使用 LLM 生成 slug | 可能不够直观 |

---

## 🚀 如何实现真正的"连续对话"

### 方案 1: session-memory Hook + 自动加载（推荐）

**当前配置**:
```json
{
  "hooks": {
    "internal": {
      "entries": {
        "session-memory": {
          "enabled": true
        }
      }
    }
  }
}
```

**需要补充**:
在 `AGENTS.md` 的 "Every Session" 流程中，自动加载最近的 memory 文件：

```markdown
## Every Session

Before doing anything else:

1. Read `SOUL.md`
2. Read `USER.md`
3. Read `IDENTITY.md`
4. Read `memory/YYYY-MM-DD.md` (今天 + 昨天)
5. **新增**: 读取最近的 session memory 文件
   ```
   # 读取最近的 3 个 session memory 文件
   ls -t memory/*.md 2>/dev/null | head -3
   ```
6. **If in MAIN SESSION**: Also read `MEMORY.md`
```

---

### 方案 2: 使用 session 工具手动访问历史

OpenClaw 提供了 session 工具，可以在对话中手动访问历史：

```
用户: 列出最近 5 个 session
Agent: 调用 sessions_list 工具

用户: 查看特定 session 的历史
Agent: 调用 sessions_history 工具
```

---

### 方案 3: 自定义 Hook 实现

创建一个自定义 hook，在 `/new` 时自动加载最近的 session 摘要：

```typescript
// hooks/load-session-history/HOOK.md
---
name: load-session-history
description: Load recent session context on /new
metadata:
  openclaw:
    emoji: 📚
    events: ["command:new"]
---

# Load Session History Hook

On `/new`, automatically load the last N session summaries
```

```typescript
// hooks/load-session-history/handler.ts
const handler = async (event) => {
  if (event.type !== "command" || event.action !== "new") {
    return;
  }

  // 读取最近的 session history
  const recentSessions = await getRecentSessions(3);

  // 添加到新 session 的上下文
  event.context.sessionHistory = recentSessions;
};

export default handler;
```

---

## 📋 当前配置检查

### 1. session-memory Hook 状态

```bash
$ openclaw hooks info session-memory
💾 session-memory ✓ Ready
  Events: command:new, command:reset
  Status: enabled
```

### 2. Memory 文件状态

```bash
$ ls -lt workspace/memory/*.md
-rw-r--r-- 1 root root 1115 Apr 16 01:10 2026-04-16.md
-rw-r--r-- 1 root root 5955 Apr 10 18:13 2026-04-10.md
# ... 其他日期的文件
```

### 3. Session 文件状态

```bash
$ ls -la agents/main/sessions/*.jsonl | wc -l
35 个 session 文件
```

---

## ✅ 结论

### 用户的期望是否合理？

**✅ 是的，完全合理！**

用户期望：
- 聊天记录一直保存 → ✅ 已实现（Session 文件）
- 新 session 能访问历史 → ❌ **未实现**（需要配置）

### 为什么没有实现？

1. **OpenClaw 的设计哲学**：`/new` = 完全重新开始
2. **技术限制**：上下文窗口限制、性能考虑
3. **功能存在但需要配置**：session-memory hook 已存在但需要正确配置

### 如何实现？

**立即可用的方案**：
1. ✅ session-memory hook 已启用
2. ⚠️ 需要在 AGENTS.md 中配置自动加载最近的 memory 文件
3. ⚠️ 或者使用 session 工具手动访问历史

**长期方案**：
1. 创建自定义 hook 实现"连续对话"模式
2. 或者使用向量化存储实现语义检索历史

---

## 🎯 下一步建议

### 选项 1: 启用 session-memory Hook（已完成）
```bash
openclaw hooks enable session-memory
```

### 选项 2: 配置 AGENTS.md 自动加载历史
在 "Every Session" 流程中添加：
```markdown
5. 读取最近的 session memory 文件
   ```
   ls -t workspace/memory/*.md 2>/dev/null | head -3
   ```
```

### 选项 3: 测试验证
执行 `/new`，检查是否自动加载了最近的历史。

---

*分析时间: 2026-04-16 01:20*
*版本: OpenClaw 2026.3.13 + session-memory hook*
