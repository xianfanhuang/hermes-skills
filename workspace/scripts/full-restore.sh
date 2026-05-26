#!/bin/bash
# full-restore.sh - 一键恢复完整系统
# 用途: 从GitHub备份恢复workspace + cron + 知识库
# 使用: bash scripts/full-restore.sh

set -euo pipefail

WORKSPACE_DIR="/workspace/projects/workspace"
BACKUP_REPO="git@github.com:xianfanhuang/ai-trading-sync.git"

echo "======================================="
echo "OpenClaw 一键恢复"
echo "时间: $(date)"
echo "======================================="

# 1. 检查环境
echo ""
echo "🔍 检查环境..."
if ! command -v openclaw &>/dev/null; then
    echo "❌ OpenClaw 未安装，请先安装: npm install -g openclaw"
    exit 1
fi
echo "✅ OpenClaw 已安装"

if ! openclaw status >/dev/null 2>&1; then
    echo "⚠️  OpenClaw 未运行，尝试启动..."
    openclaw gateway start
    sleep 5
fi
echo "✅ OpenClaw 运行中"

# 2. 恢复workspace（如果不存在）
echo ""
echo "📦 恢复workspace..."
if [ -d "$WORKSPACE_DIR/.git" ]; then
    echo "  workspace已存在，跳过克隆"
else
    echo "  克隆备份仓库..."
    cd /workspace/projects
    git clone "$BACKUP_REPO" workspace_temp
    mv workspace_temp/* workspace_temp/.* workspace/ 2>/dev/null || true
    rmdir workspace_temp 2>/dev/null || true
    echo "  ✅ workspace已恢复"
fi

# 3. 恢复cron任务
echo ""
echo "⏰ 恢复cron任务..."
if [ -f "$WORKSPACE_DIR/scripts/cron-restore.sh" ]; then
    bash "$WORKSPACE_DIR/scripts/cron-restore.sh"
else
    echo "  ⚠️  cron-restore.sh 不存在，跳过"
fi

# 4. 初始化知识库索引
echo ""
echo "📚 初始化知识库..."
if [ -f "$WORKSPACE_DIR/scripts/knowledge-index.sh" ]; then
    bash "$WORKSPACE_DIR/scripts/knowledge-index.sh" 2>/dev/null || true
    echo "  ✅ 知识库索引已生成"
fi

# 5. 检查memory search
echo ""
echo "🔍 检查Memory Search..."
ms_status=$(openclaw memory status 2>/dev/null | head -5)
echo "$ms_status"

# 6. 完成
echo ""
echo "======================================="
echo "✅ 恢复完成！"
echo ""
echo "📊 系统状态:"
echo "  - 知识库: $(find $WORKSPACE_DIR/knowledge/ -name '*.md' 2>/dev/null | wc -l) 个文件"
echo "  - 记忆: $(ls $WORKSPACE_DIR/memory/*.md 2>/dev/null | wc -l) 个文件"
echo "  - Cron: $(openclaw cron list 2>/dev/null | grep -c '^\*' || echo 0) 个任务"
echo ""
echo "下一步:"
echo "  1. 检查 API Keys: cat $WORKSPACE_DIR/SECRET.md"
echo "  2. 测试记忆搜索: openclaw memory search '测试'"
echo "  3. 查看cron: openclaw cron list"
echo "======================================="
