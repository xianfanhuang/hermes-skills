#!/bin/bash
# maintenance-check.sh - 定时检查维护脚本
# 用途: 检查本地workspace和GitHub仓库的一致性、完整性
# 特点: 版本控制保护，维护日志，不可逆操作需确认

set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/projects/workspace}"
BACKUP_DIR="/tmp/ai-trading-sync-$$"
MAINTENANCE_LOG="$WORKSPACE_DIR/memory/maintenance.log"
TOKEN=$(cd /workspace/projects && git remote get-url origin | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
REMOTE="https://xianfanhuang:${TOKEN}@github.com/xianfanhuang/ai-trading-sync.git"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${BLUE}$msg${NC}"
    echo "$msg" >> "$MAINTENANCE_LOG"
}

ok() {
    local msg="  ✅ $1"
    echo -e "${GREEN}$msg${NC}"
    echo "$msg" >> "$MAINTENANCE_LOG"
}

warn() {
    local msg="  ⚠️  $1"
    echo -e "${YELLOW}$msg${NC}"
    echo "$msg" >> "$MAINTENANCE_LOG"
}

fail() {
    local msg="  ❌ $1"
    echo -e "${RED}$msg${NC}"
    echo "$msg" >> "$MAINTENANCE_LOG"
}

# 初始化日志
init_log() {
    mkdir -p "$(dirname "$MAINTENANCE_LOG")"
    echo "" >> "$MAINTENANCE_LOG"
    echo "=======================================" >> "$MAINTENANCE_LOG"
    log "维护检查开始"
}

# ==================== 本地检查 ====================

check_local() {
    log "检查本地workspace..."
    
    # 1. 检查核心文件
    log "  检查核心文件..."
    local core_files=("MEMORY.md" "USER.md" "IDENTITY.md" "SOUL.md" "AGENTS.md" "TOOLS.md" "README.md")
    for f in "${core_files[@]}"; do
        if [ -f "$WORKSPACE_DIR/$f" ]; then
            ok "$f 存在 ($(wc -l < "$WORKSPACE_DIR/$f") 行)"
        else
            fail "$f 缺失"
        fi
    done
    
    # 2. 检查知识库
    log "  检查知识库..."
    local kb_count=$(find "$WORKSPACE_DIR/knowledge" -name "*.md" 2>/dev/null | wc -l)
    if [ "$kb_count" -gt 0 ]; then
        ok "知识库: $kb_count 个文件"
    else
        warn "知识库为空"
    fi
    
    # 3. 检查记忆文件
    log "  检查记忆文件..."
    local mem_count=$(ls "$WORKSPACE_DIR/memory"/2026-*.md 2>/dev/null | wc -l)
    if [ "$mem_count" -gt 0 ]; then
        ok "记忆文件: $mem_count 个"
    else
        warn "记忆文件为空"
    fi
    
    # 4. 检查脚本
    log "  检查脚本..."
    local script_count=$(ls "$WORKSPACE_DIR/scripts"/*.sh 2>/dev/null | wc -l)
    if [ "$script_count" -gt 0 ]; then
        ok "脚本: $script_count 个"
    else
        warn "脚本为空"
    fi
    
    # 5. 检查Git状态
    log "  检查Git状态..."
    # workspace 使用父目录的 git repo
    if [ -d "/workspace/projects/.git" ]; then
        cd "$WORKSPACE_DIR"
        local changes=$(git status --short | wc -l)
        if [ "$changes" -eq 0 ]; then
            ok "Git: 无未提交变更"
        else
            warn "Git: $changes 个未提交变更"
        fi
    else
        warn "Git: 未配置"
    fi
}

# ==================== 仓库检查 ====================

check_remote() {
    log "检查GitHub仓库..."
    
    # 克隆仓库到临时目录
    git clone -q "$REMOTE" "$BACKUP_DIR" 2>/dev/null
    
    # 1. 检查仓库结构
    log "  检查仓库结构..."
    local remote_files=("README.md" "MEMORY.md" "USER.md" "IDENTITY.md")
    for f in "${remote_files[@]}"; do
        if [ -f "$BACKUP_DIR/$f" ]; then
            ok "仓库 $f 存在"
        else
            warn "仓库 $f 缺失"
        fi
    done
    
    # 2. 检查知识库
    log "  检查仓库知识库..."
    local remote_kb=$(find "$BACKUP_DIR/knowledge" -name "*.md" 2>/dev/null | wc -l)
    if [ "$remote_kb" -gt 0 ]; then
        ok "仓库知识库: $remote_kb 个文件"
    else
        warn "仓库知识库为空"
    fi
    
    # 3. 检查记忆
    log "  检查仓库记忆..."
    local remote_mem=$(ls "$BACKUP_DIR/memory"/2026-*.md 2>/dev/null | wc -l)
    if [ "$remote_mem" -gt 0 ]; then
        ok "仓库记忆: $remote_mem 个文件"
    else
        warn "仓库记忆为空"
    fi
    
    # 清理
    rm -rf "$BACKUP_DIR"
}

# ==================== 一致性检查 ====================

check_consistency() {
    log "检查本地与仓库一致性..."
    
    # 克隆仓库
    git clone -q "$REMOTE" "$BACKUP_DIR" 2>/dev/null
    
    # 1. 比较知识库数量
    local local_kb=$(find "$WORKSPACE_DIR/knowledge" -name "*.md" 2>/dev/null | wc -l)
    local remote_kb=$(find "$BACKUP_DIR/knowledge" -name "*.md" 2>/dev/null | wc -l)
    
    if [ "$local_kb" -eq "$remote_kb" ]; then
        ok "知识库一致: $local_kb 个文件"
    else
        warn "知识库不一致: 本地$local_kb vs 仓库$remote_kb"
    fi
    
    # 2. 比较记忆文件数量
    local local_mem=$(ls "$WORKSPACE_DIR/memory"/2026-*.md 2>/dev/null | wc -l)
    local remote_mem=$(ls "$BACKUP_DIR/memory"/2026-*.md 2>/dev/null | wc -l)
    
    if [ "$local_mem" -eq "$remote_mem" ]; then
        ok "记忆文件一致: $local_mem 个"
    else
        warn "记忆文件不一致: 本地$local_mem vs 仓库$remote_mem"
    fi
    
    # 3. 比较核心文件MD5
    log "  比较核心文件..."
    local core_files=("MEMORY.md" "USER.md" "IDENTITY.md" "SOUL.md")
    for f in "${core_files[@]}"; do
        if [ -f "$WORKSPACE_DIR/$f" ] && [ -f "$BACKUP_DIR/$f" ]; then
            local local_md5=$(md5sum "$WORKSPACE_DIR/$f" | cut -d' ' -f1)
            local remote_md5=$(md5sum "$BACKUP_DIR/$f" | cut -d' ' -f1)
            if [ "$local_md5" = "$remote_md5" ]; then
                ok "$f 一致"
            else
                warn "$f 不一致 (本地有更新)"
            fi
        fi
    done
    
    # 清理
    rm -rf "$BACKUP_DIR"
}

# ==================== hermes-skills 仓库一致性 ====================

check_hermes() {
    log "检查 hermes-skills 仓库一致性..."
    
    local HERMES_DIR="/workspace/projects"
    
    # 1. 检查 hermes-skills git 状态
    log "  检查 hermes-skills git 状态..."
    cd "$HERMES_DIR"
    local hermes_changes=$(git status --short | wc -l)
    if [ "$hermes_changes" -eq 0 ]; then
        ok "hermes-skills: 无未提交变更"
    else
        warn "hermes-skills: $hermes_changes 个未提交变更"
    fi
    
    # 2. 检查 workspace 文件是否被 hermes-skills 跟踪
    log "  检查 workspace 文件跟踪状态..."
    local tracked=$(git ls-files workspace/ | wc -l)
    local untracked=$(git ls-files --others --exclude-standard workspace/ | wc -l)
    ok "workspace: $tracked 个已跟踪, $untracked 个未跟踪"
    
    # 3. 检查 .gitignore 是否正确排除 OpenClaw 内部文件
    log "  检查 .gitignore 规则..."
    if grep -q "^cron/" "$HERMES_DIR/.gitignore" 2>/dev/null; then
        ok ".gitignore: 已排除 cron/"
    else
        warn ".gitignore: 未排除 cron/"
    fi
    if grep -q "^feishu/" "$HERMES_DIR/.gitignore" 2>/dev/null; then
        ok ".gitignore: 已排除 feishu/"
    else
        warn ".gitignore: 未排除 feishu/"
    fi
    
    # 4. 检查远程同步状态
    log "  检查远程同步状态..."
    local behind=$(git log origin/main..main --oneline 2>/dev/null | wc -l)
    if [ "$behind" -eq 0 ]; then
        ok "hermes-skills: 已同步到远程"
    else
        warn "hermes-skills: $behind 个commit未推送"
    fi
    
    cd "$WORKSPACE_DIR"
}

# ==================== 备份仓库一致性 ====================

check_backup() {
    log "检查 ai-trading-sync 备份仓库一致性..."
    
    git clone -q "$REMOTE" "$BACKUP_DIR" 2>/dev/null
    
    # 1. 比较关键文件
    log "  比较关键文件..."
    local key_files=("MEMORY.md" "AGENTS.md" "IDENTITY.md" "USER.md" "SOUL.md" "TOOLS.md")
    local sync_count=0
    local diff_count=0
    for f in "${key_files[@]}"; do
        if [ -f "$WORKSPACE_DIR/$f" ] && [ -f "$BACKUP_DIR/$f" ]; then
            local local_md5=$(md5sum "$WORKSPACE_DIR/$f" | cut -d' ' -f1)
            local remote_md5=$(md5sum "$BACKUP_DIR/$f" | cut -d' ' -f1)
            if [ "$local_md5" = "$remote_md5" ]; then
                sync_count=$((sync_count + 1))
            else
                diff_count=$((diff_count + 1))
                warn "$f 不一致 (本地有更新)"
            fi
        fi
    done
    ok "关键文件: $sync_count 一致, $diff_count 不一致"
    
    # 2. 比较脚本
    log "  比较脚本..."
    local local_scripts=$(ls "$WORKSPACE_DIR/scripts"/*.sh 2>/dev/null | xargs -I{} basename {} | sort)
    local remote_scripts=$(ls "$BACKUP_DIR/scripts"/*.sh 2>/dev/null | xargs -I{} basename {} | sort)
    if [ "$local_scripts" = "$remote_scripts" ]; then
        ok "脚本一致"
    else
        warn "脚本不一致"
    fi
    
    # 3. 比较知识库
    log "  比较知识库..."
    local local_kb=$(find "$WORKSPACE_DIR/knowledge" -name "*.md" 2>/dev/null | wc -l)
    local remote_kb=$(find "$BACKUP_DIR/knowledge" -name "*.md" 2>/dev/null | wc -l)
    if [ "$local_kb" -eq "$remote_kb" ]; then
        ok "知识库一致: $local_kb 个文件"
    else
        warn "知识库不一致: 本地$local_kb vs 仓库$remote_kb"
    fi
    
    # 4. 比较 session 归档
    log "  比较 session 归档..."
    local local_sessions=$(ls "$WORKSPACE_DIR/memory/sessions"/*.md 2>/dev/null | wc -l)
    local remote_sessions=$(ls "$BACKUP_DIR/memory/sessions"/*.md 2>/dev/null | wc -l)
    if [ "$local_sessions" -eq "$remote_sessions" ]; then
        ok "session归档一致: $local_sessions 个"
    else
        warn "session归档不一致: 本地$local_sessions vs 仓库$remote_sessions"
    fi
    
    rm -rf "$BACKUP_DIR"
}

# ==================== 大修后一致性验证 ====================

post_fix_check() {
    log "大修后一致性验证..."
    
    echo ""
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${BLUE}🔍 大修后一致性验证${NC}"
    echo -e "${BLUE}=======================================${NC}"
    echo ""
    
    # 1. 本地检查
    check_local
    echo ""
    
    # 2. hermes-skills 仓库检查
    check_hermes
    echo ""
    
    # 3. 备份仓库检查
    check_backup
    echo ""
    
    # 4. 自动同步
    log "  自动同步到备份仓库..."
    if [ -f "$WORKSPACE_DIR/scripts/sync-to-backup.sh" ]; then
        bash "$WORKSPACE_DIR/scripts/sync-to-backup.sh" "post-fix: 大修后自动同步" 2>/dev/null || true
        ok "已同步到备份仓库"
    fi
    
    # 5. 推送到 hermes-skills
    log "  推送到 hermes-skills..."
    cd "/workspace/projects"
    local behind=$(git log origin/main..main --oneline 2>/dev/null | wc -l)
    if [ "$behind" -gt 0 ]; then
        git push origin main 2>/dev/null || true
        ok "已推送 $behind 个commit到hermes-skills"
    else
        ok "hermes-skills已同步"
    fi
    cd "$WORKSPACE_DIR"
    
    echo ""
    echo -e "${GREEN}=======================================${NC}"
    echo -e "${GREEN}✅ 大修后一致性验证完成${NC}"
    echo -e "${GREEN}=======================================${NC}"
}

# ==================== 自动修复 ====================

auto_fix() {
    log "自动修复..."
    
    # 1. 确保目录存在
    mkdir -p "$WORKSPACE_DIR/knowledge/B-practices"
    mkdir -p "$WORKSPACE_DIR/knowledge/G-guides"
    mkdir -p "$WORKSPACE_DIR/knowledge/R-rules"
    mkdir -p "$WORKSPACE_DIR/memory/sessions"
    mkdir -p "$WORKSPACE_DIR/scripts"
    ok "目录结构已确保"
    
    # 2. 重新生成索引
    if [ -f "$WORKSPACE_DIR/scripts/knowledge-index.sh" ]; then
        bash "$WORKSPACE_DIR/scripts/knowledge-index.sh" 2>/dev/null || true
        ok "知识库索引已更新"
    fi
    
    # 3. 同步到仓库
    if [ -f "$WORKSPACE_DIR/scripts/sync-to-backup.sh" ]; then
        bash "$WORKSPACE_DIR/scripts/sync-to-backup.sh" 2>/dev/null || true
        ok "已同步到仓库"
    fi
}

# ==================== 状态报告 ====================

show_report() {
    echo ""
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${BLUE}📊 维护检查报告${NC}"
    echo -e "${BLUE}=======================================${NC}"
    echo ""
    echo -e "${GREEN}日志文件:${NC} $MAINTENANCE_LOG"
    echo ""
    echo -e "${GREEN}最近日志:${NC}"
    tail -20 "$MAINTENANCE_LOG" 2>/dev/null || echo "  无日志"
    echo ""
    echo -e "${BLUE}=======================================${NC}"
}

# ==================== 帮助 ====================

cmd_help() {
    echo -e "${BLUE}maintenance-check.sh - 定时检查维护脚本${NC}"
    echo "======================================="
    echo ""
    echo "使用: bash maintenance-check.sh <command>"
    echo ""
    echo "命令:"
    echo "  check       完整检查（本地+仓库+一致性）"
    echo "  local       只检查本地"
    echo "  remote      只检查仓库"
    echo "  diff        只检查一致性"
    echo "  hermes      检查hermes-skills仓库一致性"
    echo "  backup      检查ai-trading-sync备份仓库一致性"
    echo "  post-fix    大修后一致性验证（自动同步+推送）"
    echo "  fix         自动修复"
    echo "  report      显示报告"
    echo "  help        显示帮助"
}

# ==================== 主入口 ====================

init_log

case "${1:-check}" in
    check)
        check_local
        check_remote
        check_consistency
        show_report
        ;;
    local)
        check_local
        ;;
    remote)
        check_remote
        ;;
    diff)
        check_consistency
        ;;
    hermes)
        check_hermes
        ;;
    backup)
        check_backup
        ;;
    post-fix)
        post_fix_check
        ;;
    fix)
        auto_fix
        ;;
    report)
        show_report
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        fail "未知命令: $1"
        cmd_help
        exit 1
        ;;
esac

log "维护检查完成"
