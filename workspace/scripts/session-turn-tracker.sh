#!/bin/bash
# session-turn-tracker.sh - Session轮次追踪
# 用途: 追踪对话轮次，达到阈值时提醒开启新会话

set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/projects/workspace}"
TURN_FILE="$WORKSPACE_DIR/.session-turns"
CONFIG_FILE="$WORKSPACE_DIR/.session-config"
MAX_TURNS="${MAX_TURNS:-50}"  # 默认50轮
CONTEXT_THRESHOLD="${CONTEXT_THRESHOLD:-70}"  # 默认70%

# 初始化配置
init_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        cat > "$CONFIG_FILE" << 'CONFIG_EOF'
# Session配置
MAX_TURNS=50
CONTEXT_THRESHOLD=70
AUTO_ARCHIVE=true
CONFIG_EOF
        echo "✅ 配置已创建: $CONFIG_FILE"
    fi
}

# 记录轮次
record_turn() {
    local turn_id=$(date +%s)
    echo "$turn_id" >> "$TURN_FILE"
    local count=$(wc -l < "$TURN_FILE")
    echo "当前轮次: $count"
}

# 检查是否需要提醒
check_reminder() {
    init_config
    
    if [ ! -f "$TURN_FILE" ]; then
        echo "轮次: 0"
        return
    fi
    
    local count=$(wc -l < "$TURN_FILE")
    
    # 读取配置
    source "$CONFIG_FILE" 2>/dev/null || true
    local max_turns=${MAX_TURNS:-50}
    local threshold=${CONTEXT_THRESHOLD:-70}
    local time_limit=${TIME_LIMIT_MINUTES:-45}
    
    # 检查时间
    if [ -f "$TURN_FILE" ]; then
        local first_turn=$(head -1 "$TURN_FILE")
        local current_time=$(date +%s)
        local elapsed=$(( (current_time - first_turn) / 60 ))
        
        if [ "$elapsed" -ge "$time_limit" ]; then
            echo "⚠️ 已对话 ${elapsed}分钟/${time_limit}分钟，建议开启新会话"
            return 1
        fi
    fi
    
    # 检查轮次
    if [ "$count" -ge "$max_turns" ]; then
        echo "⚠️ 轮次已达 $count/$max_turns，建议开启新会话"
        return 1
    fi
    
    # 检查context使用率（需要外部传入）
    local context_pct="${1:-0}"
    if [ "$context_pct" -ge "$threshold" ]; then
        echo "⚠️ Context使用率已达 ${context_pct}%/${threshold}%，建议开启新会话"
        return 1
    fi
    
    echo "轮次: $count/$max_turns | 时间: ${elapsed}分钟/${time_limit}分钟 | Context: ${context_pct}%/${threshold}%"
    return 0
}

# 重置轮次
reset_turns() {
    rm -f "$TURN_FILE"
    echo "✅ 轮次已重置"
}

# 显示状态
show_status() {
    init_config
    
    if [ ! -f "$TURN_FILE" ]; then
        echo "轮次: 0"
    else
        echo "轮次: $(wc -l < "$TURN_FILE")"
    fi
    
    echo "配置:"
    cat "$CONFIG_FILE" 2>/dev/null || echo "  未配置"
}

# 主入口
case "${1:-status}" in
    record)
        record_turn
        ;;
    check)
        check_reminder "${2:-0}"
        ;;
    reset)
        reset_turns
        ;;
    status)
        show_status
        ;;
    init)
        init_config
        ;;
    *)
        echo "使用: $0 {record|check|reset|status|init}"
        ;;
esac
