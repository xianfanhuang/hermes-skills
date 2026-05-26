#!/bin/bash
# cron-restore.sh - Cron任务恢复脚本
# 用途: 从备份恢复所有cron任务
# 使用: bash scripts/cron-restore.sh

set -euo pipefail

echo "======================================="
echo "Cron 任务恢复"
echo "时间: $(date)"
echo "======================================="

# 检查OpenClaw是否运行
if ! openclaw status >/dev/null 2>&1; then
    echo "❌ OpenClaw 未运行，请先启动: openclaw gateway start"
    exit 1
fi

echo "✅ OpenClaw 运行中"

# Cron任务定义（从当前运行环境导出）
# 格式: name|schedule_expr|payload_text|session_target

declare -a CRON_JOBS=(
    "auto-memory-hourly|0 * * * *|执行自动记忆更新：运行 bash /workspace/projects/workspace/scripts/auto-memory.sh，然后检查今日对话是否有重要信息需要补充到 memory/今天.md。如果有，直接写入。|main"
    "session-archive-check|0 */2 * * *|Session 归档检查：查看 memory/sessions/ 目录状态，检查当前飞书 session 是否需要归档。如果今日有活跃对话但未归档，执行 session-archive.sh archive feishu <session_id> 并生成摘要。|main"
    "backup-sync|0 */6 * * *|执行自动备份同步：运行 bash /workspace/projects/workspace/scripts/sync-to-backup.sh，将本地记忆/代码/配置同步到 ai-trading-sync GitHub 仓库。完成后简要汇报结果。|main"
    "memory-archive-daily|0 2 * * *|执行每日记忆归档：运行 bash /workspace/projects/workspace/scripts/memory-archive.sh 压缩超过30天的记忆文件。然后运行 bash /workspace/projects/workspace/scripts/session-archive.sh cleanup 清理旧session归档。完成后汇报结果。|main"
)

echo ""
echo "📋 恢复 ${#CRON_JOBS[@]} 个cron任务..."

for job_def in "${CRON_JOBS[@]}"; do
    IFS='|' read -r name schedule payload target <<< "$job_def"
    
    echo -n "  创建: $name ($schedule) ... "
    
    # 检查是否已存在
    existing=$(openclaw cron list 2>/dev/null | grep -c "$name" || true)
    if [ "$existing" -gt 0 ]; then
        echo "已存在，跳过"
        continue
    fi
    
    # 创建cron任务
    openclaw cron add \
        --name "$name" \
        --schedule "$schedule" \
        --payload "$payload" \
        --target "$target" \
        --tz "Asia/Shanghai" \
        >/dev/null 2>&1 && echo "✅" || echo "❌"
done

echo ""
echo "======================================="
echo "恢复完成！"
echo ""
echo "当前cron任务:"
openclaw cron list 2>/dev/null | head -20
echo "======================================="
