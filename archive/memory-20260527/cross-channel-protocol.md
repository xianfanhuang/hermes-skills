# Cross-Channel Memory Bridge

## 问题
多渠道（飞书/Kimi）并行时，对话上下文不互通，只有文件级记忆共享。

## 解决方案

### 1. 会话摘要自动同步
每次重要对话结束时，写入 `memory/YYYY-MM-DD.md`，格式包含：
- 渠道来源（飞书/Kimi）
- 关键决策
- 待办事项
- 上下文片段

### 2. 跨渠道启动协议
在任一渠道开始新 session 时：
1. 先读 `MEMORY.md`（长期记忆）
2. 再读 `memory/今天.md`（今日记录）
3. 检查是否有来自其他渠道的未完成任务

### 3. HEARTBEAT.md 同步
心跳任务中加入跨渠道检查：
- 扫描所有渠道的最近对话
- 更新共享记忆文件

## 自动执行
在每个 session 结束时，执行 `scripts/auto-memory.sh`，确保记忆落盘。
