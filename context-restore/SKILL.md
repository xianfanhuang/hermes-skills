# Context Restore Skill

> **版本:** 1.0.0  
> **优先级:** 85 (高于 token-budget-manager)  
> **作用:** 会话归档后的上下文自动恢复

---

## 什么时候触发

每次新会话开始时，**自动执行**以下检查：

1. 读取 `.last_session_id`（如有）
2. 恢复上一个会话的摘要和关键信息
3. 清除标记（防重复恢复）

---

## 恢复策略

### 默认恢复内容

| 内容 | 来源 | 说明 |
|------|------|------|
| 会话摘要 | `summaries/{session_id}_summary.md` | 上一个会话的关键结论 |
| 最近消息 | `raw/{chunk_files}` | 最后 N 条对话（默认30） |
| 关键词 | `index/session_index.json` | 会话主题标签 |
| 待办事项 | 从摘要中提取 | 如摘要中包含 TODO |

### 恢复深度配置

```json
{
  "last_n_messages": 30,
  "include_summary": true,
  "include_keywords": true,
  "compress_threshold": 50,
  "compress_strategy": "keep_decisions"
}
```

- `last_n_messages`: 恢复最近N条消息
- `include_summary`: 是否输出摘要
- `compress_threshold`: 超过此条数时压缩（只保留决策和结论）
- `compress_strategy`: 压缩策略（`keep_decisions` / `keep_all` / `summary_only`）

---

## 使用方式

### Agent 自动调用（推荐）

在 AGENTS.md 的 "Every Session" 中：

```
6. 恢复上一个会话上下文（如存在）:
   cd /workspace/projects/workspace/skills/hermes-skills/context-restore
   python3 restore.py auto
```

### 手动调用

```bash
# 自动恢复（读 .last_session_id）
python3 restore.py auto

# 指定 session_id 恢复
python3 restore.py restore <session_id> [last_n]

# 查看所有会话
python3 restore.py list

# 查看恢复历史
python3 restore.py history
```

---

## 输出格式

```
🔄 恢复上一个会话: session_20260523_062150
   平台: feishu
   消息数: 47
   关键词: CRCL, 缠论, 买点

📝 会话摘要:
   讨论了CRCL的缠论分析，确认日线级别存在底背驰信号，
   决定等待5分钟级别确认后开仓。

📋 最近对话:
   [user] 帮我看看CRCL的买点
   [assistant] CRCL当前日线级别...
   ...

✅ 恢复完成（已清除标记）
```

---

## 与其他 Skill 的关系

| Skill | 关系 |
|-------|------|
| token-budget-manager | 触发归档 → context-restore 接管恢复 |
| session_local.py | 提供存储后端，context-restore 调用其 API |
| hermes-migration | 迁移时保留恢复标记 |

---

## 未来扩展

- [ ] 嵌入式语义检索（不只返回 last_n）
- [ ] 摘要压缩（超长会话只返回关键决策）
- [ ] 多会话关联（恢复相关主题的历史）
- [ ] 恢复后自动执行待办检查
