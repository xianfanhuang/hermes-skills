#!/bin/bash
# auto-memory-v3.sh — 单一写入源，分级存储
# 核心原则：每日记忆只保留精简摘要，session原始数据不进每日记忆
# 
# 写入规则：
#   1. 每日记忆 = 最多1个文件，最多50行，只记决策/教训/状态
#   2. session原始数据 → memory/sessions/raw/ (不进每日记忆)
#   3. 知识提取 → knowledge/ (每6小时)
#   4. 不追加模板，不重复写入

set -euo pipefail

WORKSPACE_DIR="/workspace/projects/workspace"
MEMORY_DIR="${WORKSPACE_DIR}/memory"
TODAY=$(date +%Y-%m-%d)
TODAY_MEMORY="${MEMORY_DIR}/${TODAY}.md"
SESSIONS_DIR="/workspace/projects/agents/main/sessions"
MAX_LINES=50

# 确保目录存在
mkdir -p "${MEMORY_DIR}"

# 如果今日记忆不存在，创建精简模板
if [[ ! -f "${TODAY_MEMORY}" ]]; then
    cat > "${TODAY_MEMORY}" << 'EOF'
# 每日记忆

## 决策与教训
*(当日重要决策和教训)*

## 系统状态
*(引擎/持仓/cron状态)*
EOF
fi

# 从最新session提取今日决策/教训（如果有的话）
# 只提取非模板内容，写入"决策与教训"段落
latest_session=$(ls -t "${SESSIONS_DIR}"/*.jsonl 2>/dev/null | head -1 || echo "")
if [[ -n "$latest_session" ]]; then
    session_name=$(basename "$latest_session" .jsonl)
    marker="<!-- s:${session_name} -->"
    
    # 跳过已处理的session（在截断之前检查）
    if ! grep -qF "$marker" "${TODAY_MEMORY}" 2>/dev/null; then
        # 从session提取包含关键词的用户消息
        decisions=$(tail -100 "$latest_session" | \
            jq -r 'select(.type == "message") | select(.message.role == "user") | .message.content[] | select(.type == "text") | .text' 2>/dev/null | \
            grep -iE "教训|决策|修复|bug|重要|注意|不要|必须|规则" | \
            grep -v "auto-memory\|session-turn-tracker\|heartbeat\|System:" | \
            head -5 || true)
        
        if [[ -n "$decisions" ]]; then
            # 追加到文件末尾
            {
                echo ""
                echo "$marker"
                echo "### $(date +%H:%M) Session更新"
                while IFS= read -r line; do
                    [[ -n "$line" ]] && echo "- ${line:0:150}"
                done <<< "$decisions"
            } >> "${TODAY_MEMORY}"
            echo "[memory] 写入session决策: ${session_name}"
        else
            # 标记已处理但无内容
            echo -e "\n${marker}" >> "${TODAY_MEMORY}"
        fi
    else
        echo "[memory] Session ${session_name} 已处理，跳过"
    fi
fi

# 截断检查（在写入之后，确保不超过上限）
current_lines=$(wc -l < "${TODAY_MEMORY}")
if [[ "$current_lines" -gt "$MAX_LINES" ]]; then
    head -n "$MAX_LINES" "${TODAY_MEMORY}" > "${TODAY_MEMORY}.tmp"
    mv "${TODAY_MEMORY}.tmp" "${TODAY_MEMORY}"
    echo "[memory] 截断: ${current_lines} → ${MAX_LINES} 行"
fi

# 知识提取（每6小时）
KNOWLEDGE_MARKER="${WORKSPACE_DIR}/knowledge/.last_extract_hour"
current_hour=$(date +%H)
last_hour=""
[[ -f "$KNOWLEDGE_MARKER" ]] && last_hour=$(cat "$KNOWLEDGE_MARKER")

if [[ "$current_hour" != "$last_hour" ]] && [[ $((10#$current_hour % 6)) -eq 0 ]]; then
    echo "[memory] 执行知识提取..."
    bash "${WORKSPACE_DIR}/scripts/session-to-md.sh" 2>&1 | tail -1
    bash "${WORKSPACE_DIR}/scripts/knowledge-extract.sh" 2>&1 | tail -1
    echo "$current_hour" > "$KNOWLEDGE_MARKER"
fi

echo "[memory] 完成: ${TODAY_MEMORY} ($(wc -l < "${TODAY_MEMORY}") 行)"
