#!/bin/bash
# session-archive.sh - Session 归档脚本
# 用途: 将当前/最近的 session 对话归档到 memory/sessions/
# 调用方式: 手动或 heartbeat 中自动执行

set -euo pipefail

WORKSPACE_DIR="/workspace/projects/workspace"
MEMORY_DIR="${WORKSPACE_DIR}/memory"
SESSIONS_DIR="${MEMORY_DIR}/sessions"
TODAY=$(date +%Y-%m-%d)
NOW=$(date +%Y%m%d_%H%M%S)

mkdir -p "${SESSIONS_DIR}"

# 归档函数
archive_session() {
    local channel="$1"
    local session_id="$2"
    local summary="$3"
    local decisions="$4"
    local todos="$5"

    # 跳过空壳归档 — 无实质内容时不写文件
    if [[ "${summary}" == "无摘要" ]] && [[ "${decisions}" == "无" ]] && [[ "${todos}" == "无" ]]; then
        echo "[archive] 跳过空壳归档 (channel=${channel}, session=${session_id})"
        return
    fi

    local archive_file="${SESSIONS_DIR}/${TODAY}-${channel}-${session_id}.md"

    cat > "${archive_file}" << EOF
# Session 归档

- **渠道**: ${channel}
- **Session ID**: ${session_id}
- **归档时间**: $(date '+%Y-%m-%d %H:%M:%S %z')

## 对话摘要
${summary}

## 重要决策
${decisions}

## 待办事项
${todos}

---
*自动归档 by session-archive.sh*
EOF

    echo "[archive] 已归档: ${archive_file}"

    # 写入 .last_session_id 标记（供 context-restore 读取）
    local restore_sessions="${WORKSPACE_DIR}/memory/sessions"
    mkdir -p "${restore_sessions}"
    echo "${session_id}" > "${restore_sessions}/.last_session_id"

    # 自动同步到备份仓库
    if [ -f "${WORKSPACE_DIR}/scripts/sync-to-backup.sh" ]; then
        bash "${WORKSPACE_DIR}/scripts/sync-to-backup.sh" "archive: session ${session_id}" 2>&1 | tail -1
    fi
}

# 清理旧归档（保留30天以上的摘要）
cleanup_old_archives() {
    local cutoff_date=$(date -d "30 days ago" +%Y-%m-%d 2>/dev/null || date -v-30d +%Y-%m-%d 2>/dev/null)

    if [ -z "${cutoff_date}" ]; then
        echo "[archive] 无法计算截止日期，跳过清理"
        return
    fi

    local count=0
    for f in "${SESSIONS_DIR}"/*.md; do
        [ -f "$f" ] || continue
        local file_date=$(basename "$f" | grep -oP '^\d{4}-\d{2}-\d{2}' || true)
        if [ -n "${file_date}" ] && [[ "${file_date}" < "${cutoff_date}" ]]; then
            # 只删除原始对话，保留摘要文件
            if grep -q "摘要" "$f" 2>/dev/null; then
                count=$((count + 1))
            else
                rm -f "$f"
                count=$((count + 1))
            fi
        fi
    done
    echo "[archive] 清理了 ${count} 个旧归档"
}

# 统计归档
stats() {
    local total=$(find "${SESSIONS_DIR}" -name "*.md" -type f 2>/dev/null | wc -l)
    local today=$(find "${SESSIONS_DIR}" -name "${TODAY}-*.md" -type f 2>/dev/null | wc -l)
    echo "[archive] 总归档: ${total} | 今日: ${today}"
}

# 主逻辑
case "${1:-stats}" in
    archive)
        archive_session "${2:-unknown}" "${3:-manual}" "${4:-无摘要}" "${5:-无}" "${6:-无}"
        ;;
    cleanup)
        cleanup_old_archives
        ;;
    stats)
        stats
        ;;
    *)
        echo "用法: $0 {archive|cleanup|stats} [channel] [session_id] [summary] [decisions] [todos]"
        ;;
esac
