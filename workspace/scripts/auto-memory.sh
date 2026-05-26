#!/bin/bash
# auto-memory.sh - OpenClaw 自动记忆管理脚本 (v2 - 幂等版)
# 用途: 自动检测重要对话并写入记忆文件
# 调用方式: cron 每小时执行一次
# 修复: 所有操作幂等，不重复追加已有内容

set -euo pipefail

# 配置
WORKSPACE_DIR="/workspace/projects/workspace"
MEMORY_DIR="${WORKSPACE_DIR}/memory"
LONG_TERM_MEMORY="${WORKSPACE_DIR}/MEMORY.md"
USER_FILE="${WORKSPACE_DIR}/USER.md"
IDENTITY_FILE="${WORKSPACE_DIR}/IDENTITY.md"
SESSIONS_DIR="/workspace/projects/agents/main/sessions"

# 当前日期
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "1 day ago" +%Y-%m-%d)
TODAY_MEMORY="${MEMORY_DIR}/${TODAY}.md"
YESTERDAY_MEMORY="${MEMORY_DIR}/${YESTERDAY}.md"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查文件中是否已包含某个标记文本（精确匹配一行即可）
has_marker() {
    local file="$1"
    local marker="$2"
    grep -qF "$marker" "$file" 2>/dev/null
}

# 初始化今天记忆文件（仅创建，不覆盖）
init_today_memory() {
    mkdir -p "${MEMORY_DIR}"
    if [[ ! -f "${TODAY_MEMORY}" ]]; then
        log_info "创建今天的记忆文件: ${TODAY_MEMORY}"
        cat > "${TODAY_MEMORY}" << EOF
# ${TODAY} 每日记忆

## 📅 基本信息
- 日期: ${TODAY}
- 星期: $(date +%A)
- Agent: Trading Assistant 🦞

---

## 💬 对话摘要
*(自动生成，待更新)*

---

## 🔑 关键信息
*(自动检测并记录)*

---

## 📝 决策与行动
*(自动记录重要决策)*

---

## ⚠️ 问题与教训
*(自动记录错误和教训)*

---

*自动生成时间: $(date "+%Y-%m-%d %H:%M:%S")*
EOF
    fi
}

# 提取用户偏好（幂等：已存在则跳过）
extract_user_preferences() {
    if has_marker "${TODAY_MEMORY}" "### 🎯 当前用户偏好"; then
        log_info "用户偏好已存在，跳过"
        return
    fi

    log_info "提取用户偏好..."
    local preferences=""

    if [[ -f "${USER_FILE}" ]]; then
        if grep -q "单笔最大亏损" "${USER_FILE}"; then
            local loss=$(grep "单笔最大亏损" "${USER_FILE}" | head -1 | cut -d':' -f2- | xargs 2>/dev/null || echo "")
            [[ -n "$loss" ]] && preferences="${preferences}\n- 单笔最大亏损: ${loss}"
        fi
        if grep -q "关注品种" "${USER_FILE}"; then
            local symbols=$(grep -A 8 "关注品种" "${USER_FILE}" | grep -E "^\s*-\s*\*\*" | head -5 | sed 's/^\s*//' | tr '\n' ' ' | xargs 2>/dev/null || echo "")
            [[ -n "$symbols" ]] && preferences="${preferences}\n- 关注品种: ${symbols}"
        fi
    fi

    if [[ -n "$preferences" ]]; then
        echo -e "\n### 🎯 当前用户偏好\n${preferences}" >> "${TODAY_MEMORY}"
        log_info "用户偏好已写入"
    fi
}

# 分析最近 Session 的用户消息（幂等：按session文件名标记）
analyze_recent_session() {
    local latest_session=$(ls -t "${SESSIONS_DIR}"/*.jsonl 2>/dev/null | head -1 || echo "")
    [[ -z "${latest_session}" ]] && return

    local session_name=$(basename "${latest_session}" .jsonl)
    local marker="<!-- session:${session_name} -->"

    if has_marker "${TODAY_MEMORY}" "$marker"; then
        log_info "Session ${session_name} 已分析过，跳过"
        return
    fi

    log_info "分析 Session: ${session_name}"

    local recent_messages=$(tail -100 "${latest_session}" | jq -r 'select(.type == "message") | select(.message.role == "user") | .message.content[] | select(.type == "text") | .text' 2>/dev/null | tail -20 || echo "")

    [[ -z "$recent_messages" ]] && return

    local keywords=("记住" "重要" "偏好" "喜欢" "决策" "策略" "交易" "风险" "止损" "止盈" "不要" "避免" "注意" "教训" "bug" "修复")
    local important_messages=()

    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        # 跳过系统自动消息
        echo "$line" | grep -q "执行自动记忆更新" && continue
        echo "$line" | grep -q "auto-memory.sh" && continue
        for keyword in "${keywords[@]}"; do
            if echo "$line" | grep -qi "$keyword"; then
                important_messages+=("$line")
                break
            fi
        done
    done <<< "$recent_messages"

    if [[ ${#important_messages[@]} -gt 0 ]]; then
        {
            echo ""
            echo "${marker}"
            echo "### 🔑 关键对话记录 ($(date +%H:%M))"
            echo ""
            for msg in "${important_messages[@]}"; do
                # 截断过长的消息
                local short_msg="${msg:0:200}"
                echo "- ${short_msg}"
            done
        } >> "${TODAY_MEMORY}"
        log_info "写入 ${#important_messages[@]} 条关键消息"
    else
        # 即使没有重要消息也写标记，避免重复扫描
        echo -e "\n${marker}\n<!-- 无关键消息 -->" >> "${TODAY_MEMORY}"
    fi
}

# 生成对话摘要（幂等：按session文件名标记）
generate_summary() {
    local latest_session=$(ls -t "${SESSIONS_DIR}"/*.jsonl 2>/dev/null | head -1 || echo "")
    [[ -z "${latest_session}" ]] && return

    local session_name=$(basename "${latest_session}" .jsonl)
    local marker="<!-- summary:${session_name} -->"

    if has_marker "${TODAY_MEMORY}" "$marker"; then
        log_info "摘要 ${session_name} 已存在，跳过"
        return
    fi

    log_info "生成对话摘要..."

    local user_messages=$(tail -50 "${latest_session}" | jq -r 'select(.type == "message") | select(.message.role == "user") | .message.content[] | select(.type == "text") | .text' 2>/dev/null | grep -v "执行自动记忆更新" | grep -v "auto-memory.sh" | head -3 || echo "")

    if [[ -n "$user_messages" ]]; then
        {
            echo ""
            echo "${marker}"
            echo "## 💬 对话摘要 ($(date +%H:%M))"
            echo ""
            while IFS= read -r line; do
                [[ -n "$line" ]] && echo "- ${line:0:200}"
            done <<< "$user_messages"
        } >> "${TODAY_MEMORY}"
    fi
}

# 主函数
main() {
    log_info "======================================"
    log_info "OpenClaw 自动记忆管理 v2"
    log_info "时间: $(date)"
    log_info "======================================"

    init_today_memory
    extract_user_preferences
    analyze_recent_session
    generate_summary

    log_info "✅ 自动记忆更新完成"
    log_info "记忆文件: ${TODAY_MEMORY} ($(wc -c < "${TODAY_MEMORY}") bytes)"
}

# 知识提取集成（每6小时执行一次）
run_knowledge_pipeline() {
    local hour=$(date +%H)
    local marker="${KNOWLEDGE_DIR:-/workspace/projects/workspace/knowledge}/.last_extract_hour"
    mkdir -p "$(dirname "$marker")"

    local last_hour=""
    [[ -f "$marker" ]] && last_hour=$(cat "$marker")

    # 每6小时执行一次（00, 06, 12, 18）
    local current_hour=$(date +%H)
    if [[ "$current_hour" != "$last_hour" ]] && [[ $((current_hour % 6)) -eq 0 ]]; then
        log_info "执行知识提取流水线..."
        bash "${WORKSPACE_DIR}/scripts/session-to-md.sh" 2>&1 | tail -1
        bash "${WORKSPACE_DIR}/scripts/knowledge-extract.sh" 2>&1 | tail -3
        bash "${WORKSPACE_DIR}/scripts/knowledge-consolidate.sh" 2>&1 | tail -3
        bash "${WORKSPACE_DIR}/scripts/knowledge-index.sh" 2>&1 | tail -1
        echo "$current_hour" > "$marker"
    fi
}

main "$@"
run_knowledge_pipeline
