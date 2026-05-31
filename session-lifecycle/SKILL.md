---
name: session-lifecycle
description: "Session 全生命周期管理 — 归档、防溢出、上下文恢复、备份同步。用于理解 OpenClaw session 机制和排查相关问题。"
---

# Session 全生命周期管理

## 核心机制

### 1. Session 启动流程
```
context-restore.sh → auto-archive-on-reset → 问候 Captain
```

- `context-restore.sh`：恢复今日记忆 + 长期记忆 + 上一个session摘要
- `auto-archive-on-reset.sh`：归档上一个未归档session
- 自动注入：AGENTS.md / SOUL.md / USER.md / IDENTITY.md / MEMORY.md / TOOLS.md

### 2. /new 与 /reset
- **行为完全相同**：保存旧session为 `.jsonl.reset.TIMESTAMP` → 创建新session → 恢复上下文
- 无任何区别，都触发 `auto-archive-on-reset`

### 3. 防溢出机制（四层）

| 层级 | 机制 | 阈值 | 动作 |
|------|------|------|------|
| 输出防溢出 | 单轮输出检查 | >400字 | 精简：列表代替段落、一句话回复 |
| 轮次防溢出 | session-turn-tracker | ≥50轮 | ⚠️ 提醒开新会话 |
| 时间防溢出 | session时长检查 | >45分钟 | ⚠️ 提醒开新会话 |
| Context防溢出 | 上下文使用率 | ≥70% | ⚠️ 提醒开新会话 |

### 4. 定时任务（五层保护）

| 任务 | 频率 | 作用 |
|------|------|------|
| auto-archive-on-reset | 每次reset | 立即归档上一个session |
| session-archive cron | 每2小时 | 补充归档活跃session |
| backup-sync | 每6小时 | 增量同步到GitHub |
| session-cleanup | 每小时 | 清理超24h孤立文件 |
| memory-archive | 每天02:00 | 压缩超30天记忆 |

### 5. 数据流

```
Session运行 → .jsonl（逐条写入）
  → /new或/reset → .jsonl.reset.TIMESTAMP
    → auto-archive → .md 归档
    → backup-sync → GitHub (ai-trading-sync)
    → session-cleanup → 删除本地文件（24h后）
```

## 关键文件

| 文件 | 作用 |
|------|------|
| `scripts/context-restore.sh` | 启动时恢复上下文 |
| `scripts/auto-archive-on-reset.sh` | reset时归档上一个session |
| `scripts/session-turn-tracker.sh` | 轮次/时间/context检查 |
| `scripts/sync-to-backup.sh` | 同步到GitHub |
| `scripts/session-cleanup.sh` | 清理孤立文件 |
| `scripts/memory-archive.sh` | 压缩旧记忆 |
| `memory/YYYY-MM-DD.md` | 今日记忆 |
| `memory/MEMORY.md` | 长期记忆 |
| `memory/sessions/` | session归档目录 |

## 排查指南

**Session卡住/context满了：**
1. 检查轮次：`bash scripts/session-turn-tracker.sh check`
2. 手动归档：触发 `/new` 或 `/reset`

**归档丢失：**
1. 检查 `memory/sessions/` 目录
2. 检查 `.jsonl.reset.*` 文件是否存在
3. 手动运行 `bash scripts/auto-archive-on-reset.sh`

**备份不同步：**
1. 检查 cron 任务状态
2. 手动运行 `bash scripts/sync-to-backup.sh`

---
*提炼自: workspace/docs/session-lifecycle-backup.md v2.0 | 2026-05-31*
