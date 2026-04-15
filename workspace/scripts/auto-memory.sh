#!/bin/bash
# auto-memory.sh - OpenClaw 自动记忆管理脚本
# 用途: 自动检测重要对话并写入记忆文件
# 调用方式: 在 AGENTS.md 中配置为 Session 结束时执行

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

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 初始化今天记忆文件
init_today_memory() {
    mkdir -p "${MEMORY_DIR}"

    if [[ ! -f "${TODAY_MEMORY}" ]]; then
        log_info "创建今天的记忆文件: ${TODAY_MEMORY}"
        cat > "${TODAY_MEMORY}" << 'EOF'
# ${TODAY} 每日记忆

## 📅 基本信息
- 日期: ${TODAY}
- 星期: $(date +%A)
- Agent: Trading Assistant 🦞
- 用户: $(grep "^- \*\*Name:\*\*" "${USER_FILE}" | cut -d':' -f2- | xargs)

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

# 提取用户偏好
extract_user_preferences() {
    log_info "提取用户偏好..."

    if [[ ! -f "${USER_FILE}" ]]; then
        log_warn "USER.md 文件不存在"
        return
    fi

    local preferences=""
    if grep -q "风险承受级别" "${USER_FILE}"; then
        local level=$(grep "级别:" "${USER_FILE}" | cut -d':' -f2- | xargs || echo "")
        if [[ -n "$level" ]]; then
            preferences="${preferences}\n- 风险偏好: ${level}"
        fi
    fi
    if grep -q "单笔最大亏损" "${USER_FILE}"; then
        local loss=$(grep "单笔最大亏损" "${USER_FILE}" | cut -d':' -f2- | xargs || echo "")
        if [[ -n "$loss" ]]; then
            preferences="${preferences}\n- 单笔最大亏损: ${loss}"
        fi
    fi
    if grep -q "关注品种" "${USER_FILE}"; then
        local symbols=$(grep -A 5 "关注品种" "${USER_FILE}" | grep -E "^\s*-" | head -5 | tr '\n' ',' | sed 's/,$//' || echo "")
        if [[ -n "$symbols" ]]; then
            preferences="${preferences}\n- 关注品种: ${symbols}"
        fi
    fi

    if [[ -n "$preferences" ]]; then
        echo -e "\n### 🎯 当前用户偏好\n$preferences" >> "${TODAY_MEMORY}"
    fi
}

# 分析最近的 Session 并提取关键信息
analyze_recent_session() {
    log_info "分析最近的 Session..."

    local latest_session=$(ls -t "${SESSIONS_DIR}"/*.jsonl 2>/dev/null | head -1 || echo "")

    if [[ -z "${latest_session}" ]]; then
        log_warn "没有找到最近的 Session 文件"
        return
    fi

    log_info "分析 Session: $(basename "${latest_session}")"

    local recent_messages=$(tail -100 "${latest_session}" | jq -r 'select(.type == "message") | select(.message.role == "user") | .message.content[] | select(.type == "text") | .text' 2>/dev/null || echo "")

    if [[ -z "$recent_messages" ]]; then
        log_warn "Session 中没有用户消息"
        return
    fi

    local keywords=("记住" "重要" "偏好" "喜欢" "决策" "策略" "交易" "风险" "止损" "止盈" "不要" "避免" "注意")
    local important_messages=()

    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            for keyword in "${keywords[@]}"; do
                if echo "$line" | grep -qi "$keyword"; then
                    important_messages+=("$line")
                    break
                fi
            done
        fi
    done <<< "$recent_messages"

    if [[ ${#important_messages[@]} -gt 0 ]]; then
        log_info "检测到 ${#important_messages[@]} 条重要消息"

        echo -e "\n### 🔑 关键对话记录\n" >> "${TODAY_MEMORY}"
        echo -e "*检测到的关键字: ${keywords[*]}*\n" >> "${TODAY_MEMORY}"

        for msg in "${important_messages[@]}"; do
            echo -e "**用户**: $msg\n" >> "${TODAY_MEMORY}"
        done
    else
        log_info "未检测到关键字触发的消息"
    fi
}

# 生成对话摘要
generate_summary() {
    log_info "生成对话摘要..."

    local latest_session=$(ls -t "${SESSIONS_DIR}"/*.jsonl 2>/dev/null | head -1 || echo "")

    if [[ -z "${latest_session}" ]]; then
        return
    fi

    local user_messages=$(tail -50 "${latest_session}" | jq -r 'select(.type == "message") | select(.message.role == "user") | .message.content[] | select(.type == "text") | .text' 2>/dev/null | head -5 || echo "")

    if [[ -n "$user_messages" ]]; then
        echo -e "\n## 💬 对话摘要\n" >> "${TODAY_MEMORY}"
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                echo "- $line" >> "${TODAY_MEMORY}"
            fi
        done <<< "$user_messages"
    fi
}

# 更新长期记忆
update_long_term_memory() {
    log_info "更新长期记忆..."

    if [[ -f "${USER_FILE}" ]]; then
        local preferences=$(grep -A 10 "投资偏好" "${USER_FILE}" 2>/dev/null || echo "")
        if [[ -n "$preferences" ]]; then
            log_info "用户偏好已在 USER.md 中，确保 MEMORY.md 同步"
        fi
    fi
}

# 主函数
main() {
    log_info "======================================"
    log_info "OpenClaw 自动记忆管理"
    log_info "时间: $(date)"
    log_info "======================================"

    init_today_memory
    extract_user_preferences
    analyze_recent_session
    generate_summary
    update_long_term_memory

    log_info "✅ 自动记忆更新完成"
    log_info "记忆文件: ${TODAY_MEMORY}"
}

# 执行主函数
main "$@"
