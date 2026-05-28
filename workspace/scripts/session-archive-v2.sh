#!/bin/bash
# session-archive-v2.sh — Session归档脚本（v2: 真实内容，非模板）
# 用法: bash scripts/session-archive-v2.sh [summary] [decisions] [todos]
# 如果不传参数，从最近的session transcript自动提取

set -euo pipefail

WORKSPACE_DIR="/workspace/projects/workspace"
SESSIONS_DIR="${WORKSPACE_DIR}/memory/sessions"
TODAY=$(date +%Y-%m-%d)
CHANNEL="feishu"

mkdir -p "${SESSIONS_DIR}"

# 获取session ID
SESSION_ID="${1:-$(date +%Y%m%d_%H%M%S)}"
SUMMARY="${2:-}"
DECISIONS="${3:-}"
TODOS="${4:-}"

# 如果没传summary，尝试从session transcript自动提取
if [ -z "$SUMMARY" ]; then
    # 查找最新的session transcript
    TRANSCRIPT_DIR="/workspace/projects/agents/main/sessions"
    latest_jsonl=$(ls -t "${TRANSCRIPT_DIR}"/*.jsonl 2>/dev/null | head -1)
    
    if [ -n "$latest_jsonl" ] && [ -f "$latest_jsonl" ]; then
        # 提取用户消息（非系统、非工具）作为摘要
        SUMMARY=$(grep '"role":"user"' "$latest_jsonl" 2>/dev/null | \
            grep -v '"content":"System:' | \
            grep -v 'session-turn-tracker' | \
            grep -v 'heartbeat' | \
            tail -10 | \
            sed 's/.*"content":"//;s/".*//' | \
            head -5 || echo "无摘要")
        SESSION_ID=$(basename "$latest_jsonl" .jsonl)
    fi
    
    [ -z "$SUMMARY" ] && SUMMARY="无摘要"
fi

# 跳过空壳
if [[ "$SUMMARY" == "无摘要" ]] && [[ "$DECISIONS" == "无" || -z "$DECISIONS" ]] && [[ "$TODOS" == "无" || -z "$TODOS" ]]; then
    echo "[archive] 跳过空壳归档"
    exit 0
fi

# 写入归档
ARCHIVE_FILE="${SESSIONS_DIR}/${TODAY}-${CHANNEL}-${SESSION_ID}.md"

cat > "${ARCHIVE_FILE}" << EOF
# Session 归档

- **渠道**: ${CHANNEL}
- **Session ID**: ${SESSION_ID}
- **归档时间**: $(date '+%Y-%m-%d %H:%M:%S %z')

## 对话摘要
${SUMMARY}

## 重要决策
${DECISIONS:-无}

## 待办事项
${TODOS:-无}
EOF

echo "[archive] 已归档: ${ARCHIVE_FILE}"

# 更新last session marker
echo "${SESSION_ID}" > "${SESSIONS_DIR}/.last_session_id"
