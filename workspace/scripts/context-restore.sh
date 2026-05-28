#!/bin/bash
# context-restore.sh — 会话启动时恢复上下文
# 输出：精简的上下文摘要（供模型快速理解当前状态）
# 用法: bash scripts/context-restore.sh

set -euo pipefail

WORKSPACE_DIR="/workspace/projects/workspace"
SESSIONS_DIR="${WORKSPACE_DIR}/memory/sessions"
MEMORY_DIR="${WORKSPACE_DIR}/memory"
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "1 day ago" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null)

echo "=== 上下文恢复 ==="
echo ""

# 1. 最新session归档（仅读最新一个，跳过空壳）
latest=$(ls -t "${SESSIONS_DIR}"/*.md 2>/dev/null | head -1)
if [ -n "$latest" ] && [ "$(wc -l < "$latest")" -ge 10 ]; then
    echo "## 最近Session ($(basename "$latest"))"
    cat "$latest"
    echo ""
else
    echo "## 最近Session: 无有效归档"
fi

# 2. 今日记忆（仅输出关键决策和教训，跳过模板）
today_file="${MEMORY_DIR}/${TODAY}.md"
if [ -f "$today_file" ]; then
    echo "## 今日记忆 (${TODAY})"
    # 只提取关键段落
    sed -n '/^## 🔑 关键决策/,/^## /p' "$today_file" | head -20
    sed -n '/^## ⚠️ 重要教训/,/^## /p' "$today_file" | head -10
    echo ""
fi

# 3. 系统状态快照
echo "## 系统状态"
# 持仓
positions_file="${WORKSPACE_DIR}/chanlun-agent/paper-trading/unified/portfolio.json"
if [ -f "$positions_file" ]; then
    echo "持仓: $(cat "$positions_file" | grep -o '"symbol":[^,}]*' | tr '\n' ', ' || echo '空仓')"
fi
# 引擎进程
engine_pid=$(pgrep -f "engine.py" 2>/dev/null | head -1 || true)
if [ -n "$engine_pid" ]; then
    echo "引擎: 运行中 (PID $engine_pid)"
else
    echo "引擎: 未运行"
fi
# Cron (OpenClaw internal cron, not system crontab)
echo "Cron: OpenClaw内部管理"

echo ""
echo "=== 恢复完成 ==="
