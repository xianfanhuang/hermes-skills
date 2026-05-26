#!/bin/bash
# memory-cli.sh - 统一记忆管理系统 CLI
# 平台无关，纯bash实现，一行命令搞定一切
# 使用: bash memory-cli.sh <command> [args]

set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/projects/workspace}"
MEMORY_DIR="$WORKSPACE_DIR/memory"
KNOWLEDGE_DIR="$WORKSPACE_DIR/knowledge"
SESSIONS_DIR="$MEMORY_DIR/sessions"
BACKUP_REPO="git@github.com:xianfanhuang/ai-trading-sync.git"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==================== 核心功能 ====================

# 搜索记忆和知识库
cmd_search() {
    local query="$1"
    echo -e "${BLUE}🔍 搜索: $query${NC}"
    echo "================================"
    
    # 搜索记忆文件
    echo -e "\n${GREEN}📝 记忆文件:${NC}"
    grep -rn --color=always "$query" "$MEMORY_DIR"/*.md 2>/dev/null | head -20 || echo "  无匹配"
    
    # 搜索知识库
    echo -e "\n${GREEN}📚 知识库:${NC}"
    grep -rn --color=always "$query" "$KNOWLEDGE_DIR"/**/*.md 2>/dev/null | head -20 || echo "  无匹配"
    
    # 搜索session归档
    echo -e "\n${GREEN}💬 Session归档:${NC}"
    grep -rn --color=always "$query" "$SESSIONS_DIR"/*.md 2>/dev/null | head -10 || echo "  无匹配"
}

# 列出知识库
cmd_knowledge() {
    echo -e "${BLUE}📚 知识库状态${NC}"
    echo "================================"
    echo -e "${GREEN}B-practices (实战):${NC} $(ls "$KNOWLEDGE_DIR/B-practices/"*.md 2>/dev/null | wc -l) 个"
    echo -e "${GREEN}G-guides (指南):${NC} $(ls "$KNOWLEDGE_DIR/G-guides/"*.md 2>/dev/null | wc -l) 个"
    echo -e "${GREEN}R-rules (规则):${NC} $(ls "$KNOWLEDGE_DIR/R-rules/"*.md 2>/dev/null | wc -l) 个"
    echo ""
    
    if [ "${1:-}" = "--list" ]; then
        echo -e "${GREEN}文件列表:${NC}"
        find "$KNOWLEDGE_DIR" -name "*.md" -type f | sort | while read f; do
            echo "  $(basename "$f") ($(du -h "$f" | cut -f1))"
        done
    fi
}

# 列出记忆
cmd_memory() {
    echo -e "${BLUE}📝 记忆状态${NC}"
    echo "================================"
    echo -e "${GREEN}每日记忆:${NC} $(ls "$MEMORY_DIR"/2026-*.md 2>/dev/null | wc -l) 个"
    echo -e "${GREEN}Session归档:${NC} $(ls "$SESSIONS_DIR"/*.md 2>/dev/null | wc -l) 个"
    echo -e "${GREEN}长期记忆:${NC} $(wc -l < "$WORKSPACE_DIR/MEMORY.md" 2>/dev/null || echo 0) 行"
    echo ""
    
    if [ "${1:-}" = "--list" ]; then
        echo -e "${GREEN}最近记忆:${NC}"
        ls -lt "$MEMORY_DIR"/2026-*.md 2>/dev/null | head -10 | awk '{print "  " $9 " (" $6 " " $7 ")"}'
    fi
}

# 自动记忆更新
cmd_auto_memory() {
    echo -e "${BLUE}⏰ 自动记忆更新${NC}"
    echo "================================"
    
    if [ -f "$WORKSPACE_DIR/scripts/auto-memory.sh" ]; then
        bash "$WORKSPACE_DIR/scripts/auto-memory.sh"
    else
        echo -e "${RED}❌ auto-memory.sh 不存在${NC}"
    fi
}

# Session归档
cmd_archive() {
    echo -e "${BLUE}💬 Session归档${NC}"
    echo "================================"
    
    if [ -f "$WORKSPACE_DIR/scripts/session-archive.sh" ]; then
        bash "$WORKSPACE_DIR/scripts/session-archive.sh" archive "${1:-feishu}" "${2:-current}"
    else
        echo -e "${RED}❌ session-archive.sh 不存在${NC}"
    fi
}

# 知识提取
cmd_extract() {
    echo -e "${BLUE}📚 知识提取${NC}"
    echo "================================"
    
    if [ -f "$WORKSPACE_DIR/scripts/knowledge-extract.sh" ]; then
        bash "$WORKSPACE_DIR/scripts/knowledge-extract.sh"
    else
        echo -e "${RED}❌ knowledge-extract.sh 不存在${NC}"
    fi
}

# 同步到云端
cmd_sync() {
    echo -e "${BLUE}☁️  同步到云端${NC}"
    echo "================================"
    
    if [ -f "$WORKSPACE_DIR/scripts/sync-to-backup.sh" ]; then
        bash "$WORKSPACE_DIR/scripts/sync-to-backup.sh"
    else
        echo -e "${RED}❌ sync-to-backup.sh 不存在${NC}"
    fi
}

# 从云端恢复
cmd_restore() {
    echo -e "${BLUE}🔄 从云端恢复${NC}"
    echo "================================"
    
    if [ -f "$WORKSPACE_DIR/scripts/full-restore.sh" ]; then
        bash "$WORKSPACE_DIR/scripts/full-restore.sh"
    else
        echo -e "${RED}❌ full-restore.sh 不存在${NC}"
    fi
}

# 系统状态
cmd_status() {
    echo -e "${BLUE}📊 系统状态${NC}"
    echo "================================"
    
    # 基本信息
    echo -e "${GREEN}工作目录:${NC} $WORKSPACE_DIR"
    echo -e "${GREEN}记忆目录:${NC} $MEMORY_DIR"
    echo -e "${GREEN}知识库:${NC} $KNOWLEDGE_DIR"
    echo ""
    
    # 统计
    echo -e "${GREEN}📝 记忆:${NC}"
    echo "  每日记忆: $(ls "$MEMORY_DIR"/2026-*.md 2>/dev/null | wc -l) 个"
    echo "  Session归档: $(ls "$SESSIONS_DIR"/*.md 2>/dev/null | wc -l) 个"
    echo "  长期记忆: $(wc -l < "$WORKSPACE_DIR/MEMORY.md" 2>/dev/null || echo 0) 行"
    echo ""
    
    echo -e "${GREEN}📚 知识库:${NC}"
    echo "  B-practices: $(ls "$KNOWLEDGE_DIR/B-practices/"*.md 2>/dev/null | wc -l) 个"
    echo "  G-guides: $(ls "$KNOWLEDGE_DIR/G-guides/"*.md 2>/dev/null | wc -l) 个"
    echo "  R-rules: $(ls "$KNOWLEDGE_DIR/R-rules/"*.md 2>/dev/null | wc -l) 个"
    echo ""
    
    echo -e "${GREEN}⏰ Cron:${NC}"
    if command -v openclaw &>/dev/null && openclaw status &>/dev/null; then
        openclaw cron list 2>/dev/null | grep -E "^\*|^[0-9]" | head -5 || echo "  无cron任务"
    else
        echo "  OpenClaw 未运行"
    fi
    echo ""
    
    echo -e "${GREEN}☁️  备份:${NC}"
    if [ -d "$WORKSPACE_DIR/.git" ]; then
        echo "  Git: 已配置"
        echo "  远程: $(git -C "$WORKSPACE_DIR" remote get-url origin 2>/dev/null || echo '未配置')"
        echo "  最后提交: $(git -C "$WORKSPACE_DIR" log --oneline -1 2>/dev/null || echo '无')"
    else
        echo "  Git: 未配置"
    fi
}

# 帮助
cmd_help() {
    echo -e "${BLUE}memory-cli.sh - 统一记忆管理系统${NC}"
    echo "================================"
    echo ""
    echo "使用: bash memory-cli.sh <command> [args]"
    echo ""
    echo "命令:"
    echo "  search <query>     搜索记忆和知识库"
    echo "  knowledge [--list] 列出知识库"
    echo "  memory [--list]    列出记忆"
    echo "  auto-memory        自动记忆更新"
    echo "  archive [channel] [session]  Session归档"
    echo "  extract            知识提取"
    echo "  sync               同步到云端"
    echo "  restore            从云端恢复"
    echo "  status             系统状态"
    echo "  help               显示帮助"
    echo ""
    echo "示例:"
    echo "  bash memory-cli.sh search '止损'"
    echo "  bash memory-cli.sh knowledge --list"
    echo "  bash memory-cli.sh status"
}

# ==================== 主入口 ====================

case "${1:-help}" in
    search)
        shift
        cmd_search "${1:-}"
        ;;
    knowledge)
        shift
        cmd_knowledge "${1:-}"
        ;;
    memory)
        shift
        cmd_memory "${1:-}"
        ;;
    auto-memory)
        cmd_auto_memory
        ;;
    archive)
        shift
        cmd_archive "$@"
        ;;
    extract)
        cmd_extract
        ;;
    sync)
        cmd_sync
        ;;
    restore)
        cmd_restore
        ;;
    status)
        cmd_status
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        echo -e "${RED}❌ 未知命令: $1${NC}"
        cmd_help
        exit 1
        ;;
esac
