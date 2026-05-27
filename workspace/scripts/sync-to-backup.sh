#!/bin/bash
# sync-to-backup.sh — 自动同步本地到 ai-trading-sync 仓库
# 用法: bash sync-to-backup.sh [commit_message]

set -euo pipefail

WORKSPACE="/workspace/projects/workspace"
BACKUP_DIR="/tmp/ai-trading-sync-$$"
TOKEN=$(cd /workspace/projects && git remote get-url origin | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
REMOTE="https://xianfanhuang:${TOKEN}@github.com/xianfanhuang/ai-trading-sync.git"
MSG="${1:-auto-sync: $(date '+%Y-%m-%d %H:%M')}"

# 克隆
git clone -q "$REMOTE" "$BACKUP_DIR"
cd "$BACKUP_DIR"

# 同步顶层文件
cp "$WORKSPACE"/README.md . 2>/dev/null || true
cp "$WORKSPACE"/RESTORE.md . 2>/dev/null || true
cp "$WORKSPACE"/RESTORE-3LAYER.md . 2>/dev/null || true
cp "$WORKSPACE"/SESSION-TIMER-PROMPT.md . 2>/dev/null || true
cp "$WORKSPACE"/MEMORY.md . 2>/dev/null || true
cp "$WORKSPACE"/USER.md . 2>/dev/null || true
cp "$WORKSPACE"/IDENTITY.md . 2>/dev/null || true
cp "$WORKSPACE"/SOUL.md . 2>/dev/null || true
cp "$WORKSPACE"/AGENTS.md . 2>/dev/null || true
cp "$WORKSPACE"/TOOLS.md . 2>/dev/null || true

# 同步记忆
cp "$WORKSPACE"/memory/*.md memory/ 2>/dev/null || true
cp "$WORKSPACE"/memory/sessions/*.md memory/sessions/ 2>/dev/null || true

# 同步交易代码
cp "$WORKSPACE"/chanlun-agent/*.py chanlun-agent/ 2>/dev/null || true
cp "$WORKSPACE"/chanlun-agent/*.md chanlun-agent/ 2>/dev/null || true
cp "$WORKSPACE"/chanlun-agent/paper-trading/*.py chanlun-agent/paper-trading/ 2>/dev/null || true
cp "$WORKSPACE"/chanlun-agent/paper-trading/*.json chanlun-agent/paper-trading/ 2>/dev/null || true
mkdir -p chanlun-agent/paper-trading/unified
cp "$WORKSPACE"/chanlun-agent/paper-trading/unified/*.py chanlun-agent/paper-trading/unified/ 2>/dev/null || true
cp "$WORKSPACE"/chanlun-agent/paper-trading/unified/*.json chanlun-agent/paper-trading/unified/ 2>/dev/null || true

# 同步脚本
cp "$WORKSPACE"/scripts/*.sh scripts/ 2>/dev/null || true

# 同步 skills（context-restore 等核心 skill）
mkdir -p skills/hermes-skills/context-restore && \
cp "$WORKSPACE"/skills/hermes-skills/context-restore/*.py skills/hermes-skills/context-restore/ && \
cp "$WORKSPACE"/skills/hermes-skills/context-restore/*.md skills/hermes-skills/context-restore/ 2>/dev/null || true

# 同步配置
for f in AGENTS.md IDENTITY.md USER.md SOUL.md HEARTBEAT.md TOOLS.md; do
    cp "$WORKSPACE/$f" config/"$f" 2>/dev/null || true
done

# 同步模拟交易
cp "$WORKSPACE"/paper-trading/*.json paper-trading/ 2>/dev/null || true
cp "$WORKSPACE"/paper-trading/*.md paper-trading/ 2>/dev/null || true

# 同步知识库
mkdir -p knowledge/B-practices knowledge/G-guides knowledge/R-rules
cp "$WORKSPACE"/knowledge/*.md knowledge/ 2>/dev/null || true
cp "$WORKSPACE"/knowledge/B-practices/*.md knowledge/B-practices/ 2>/dev/null || true
cp "$WORKSPACE"/knowledge/G-guides/*.md knowledge/G-guides/ 2>/dev/null || true
cp "$WORKSPACE"/knowledge/R-rules/*.md knowledge/R-rules/ 2>/dev/null || true

# 检查是否有变更
if git diff --quiet && git diff --cached --quiet; then
    echo "[sync] 无变更，跳过"
    rm -rf "$BACKUP_DIR"
    exit 0
fi

# 提交并推送
git add -A
git commit -m "$MSG"
git push -q

echo "[sync] ✅ 已同步: $(git diff --stat HEAD~1 --shortstat)"

# 清理
rm -rf "$BACKUP_DIR"
