#!/bin/bash
# restore-layer3-disaster.sh - 备灾恢复层
# 用途: 定时快照 + 多地备份 + 一键恢复
# 特点: 静默运转，最小维护成本

set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/projects/workspace}"
BACKUP_DIR="${BACKUP_DIR:-/data/backups/ai-trading-sync}"
S3_BUCKET="${S3_BUCKET:-}"  # 可选: S3/OSS bucket
BACKUP_REPO="git@github.com:xianfanhuang/ai-trading-sync.git"
MAX_BACKUPS=30  # 保留30天备份

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[DISASTER]${NC} $1"; }
ok() { echo -e "${GREEN}✅${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC} $1"; }
fail() { echo -e "${RED}❌${NC} $1"; }

# ==================== 快照功能 ====================

cmd_snapshot() {
    log "创建本地快照..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    SNAPSHOT_DIR="$BACKUP_DIR/snapshots/$TIMESTAMP"
    
    mkdir -p "$SNAPSHOT_DIR"
    
    # 备份核心目录
    cp -r "$WORKSPACE_DIR/knowledge" "$SNAPSHOT_DIR/" 2>/dev/null || true
    cp -r "$WORKSPACE_DIR/memory" "$SNAPSHOT_DIR/" 2>/dev/null || true
    cp -r "$WORKSPACE_DIR/scripts" "$SNAPSHOT_DIR/" 2>/dev/null || true
    cp "$WORKSPACE_DIR/MEMORY.md" "$SNAPSHOT_DIR/" 2>/dev/null || true
    cp "$WORKSPACE_DIR/USER.md" "$SNAPSHOT_DIR/" 2>/dev/null || true
    cp "$WORKSPACE_DIR/IDENTITY.md" "$SNAPSHOT_DIR/" 2>/dev/null || true
    cp "$WORKSPACE_DIR/SOUL.md" "$SNAPSHOT_DIR/" 2>/dev/null || true
    cp "$WORKSPACE_DIR/AGENTS.md" "$SNAPSHOT_DIR/" 2>/dev/null || true
    cp "$WORKSPACE_DIR/openclaw.json" "$SNAPSHOT_DIR/" 2>/dev/null || true
    
    # 压缩
    tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR/snapshots" "$TIMESTAMP" 2>/dev/null
    rm -rf "$SNAPSHOT_DIR"
    
    # 记录
    echo "$TIMESTAMP" >> "$BACKUP_DIR/backup_log.txt"
    
    ok "快照已创建: backup_$TIMESTAMP.tar.gz"
}

# ==================== 清理旧备份 ====================

cmd_cleanup() {
    log "清理旧备份（保留最近$MAX_BACKUPS个）..."
    
    if [ -d "$BACKUP_DIR" ]; then
        cd "$BACKUP_DIR"
        ls -t backup_*.tar.gz 2>/dev/null | tail -n +$((MAX_BACKUPS+1)) | xargs -r rm -f
        ok "清理完成"
    fi
}

# ==================== 异地备份 ====================

cmd_offsite() {
    log "异地备份..."
    
    # Git push（主要异地备份）
    if [ -d "$WORKSPACE_DIR/.git" ]; then
        cd "$WORKSPACE_DIR"
        git push origin main 2>/dev/null && ok "Git push 完成" || warn "Git push 失败"
    fi
    
    # S3/OSS 备份（可选）
    if [ -n "$S3_BUCKET" ] && command -v aws &>/dev/null; then
        log "上传到 S3..."
        aws s3 sync "$BACKUP_DIR" "s3://$S3_BUCKET/ai-trading-sync/" --exclude "snapshots/*" 2>/dev/null && ok "S3 上传完成" || warn "S3 上传失败"
    fi
}

# ==================== 恢复功能 ====================

cmd_restore() {
    log "从备份恢复..."
    
    # 选择恢复源
    echo ""
    echo "选择恢复源:"
    echo "  1) 最新本地快照"
    echo "  2) GitHub 仓库"
    echo "  3) 指定快照文件"
    read -p "请选择 [1-3]: " choice
    
    case $choice in
        1)
            LATEST=$(ls -t "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | head -1)
            if [ -n "$LATEST" ]; then
                log "恢复自: $LATEST"
                mkdir -p /tmp/restore
                tar -xzf "$LATEST" -C /tmp/restore
                cp -r /tmp/restore/*/knowledge "$WORKSPACE_DIR/" 2>/dev/null
                cp -r /tmp/restore/*/memory "$WORKSPACE_DIR/" 2>/dev/null
                rm -rf /tmp/restore
                ok "恢复完成"
            else
                fail "没有找到本地快照"
            fi
            ;;
        2)
            log "从 GitHub 恢复..."
            if [ -d "$WORKSPACE_DIR/.git" ]; then
                cd "$WORKSPACE_DIR"
                git fetch origin
                git reset --hard origin/main
                ok "GitHub 恢复完成"
            else
                fail "Git 未配置"
            fi
            ;;
        3)
            read -p "输入快照文件路径: " snapshot_file
            if [ -f "$snapshot_file" ]; then
                mkdir -p /tmp/restore
                tar -xzf "$snapshot_file" -C /tmp/restore
                cp -r /tmp/restore/*/knowledge "$WORKSPACE_DIR/" 2>/dev/null
                cp -r /tmp/restore/*/memory "$WORKSPACE_DIR/" 2>/dev/null
                rm -rf /tmp/restore
                ok "恢复完成"
            else
                fail "文件不存在"
            fi
            ;;
        *)
            fail "无效选择"
            ;;
    esac
}

# ==================== 状态检查 ====================

cmd_status() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${BLUE}📊 备灾恢复层状态${NC}"
    echo -e "${BLUE}=======================================${NC}"
    
    echo -e "\n${GREEN}📁 备份目录:${NC} $BACKUP_DIR"
    
    if [ -d "$BACKUP_DIR" ]; then
        echo -e "${GREEN}📦 本地快照:${NC} $(ls "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | wc -l) 个"
        
        LATEST=$(ls -t "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | head -1)
        if [ -n "$LATEST" ]; then
            echo -e "${GREEN}📅 最新快照:${NC} $(basename "$LATEST") ($(du -h "$LATEST" | cut -f1))"
        fi
    else
        echo -e "${YELLOW}⚠️  备份目录不存在${NC}"
    fi
    
    echo -e "\n${GREEN}☁️  GitHub:${NC}"
    if [ -d "$WORKSPACE_DIR/.git" ]; then
        echo "  远程: $(git -C "$WORKSPACE_DIR" remote get-url origin 2>/dev/null || echo '未配置')"
        echo "  最后提交: $(git -C "$WORKSPACE_DIR" log --oneline -1 2>/dev/null || echo '无')"
    else
        echo "  未配置"
    fi
    
    echo -e "\n${GREEN}📊 数据统计:${NC}"
    echo "  知识库: $(find "$WORKSPACE_DIR/knowledge" -name "*.md" 2>/dev/null | wc -l) 个文件"
    echo "  记忆: $(ls "$WORKSPACE_DIR/memory"/2026-*.md 2>/dev/null | wc -l) 个文件"
    echo "  脚本: $(ls "$WORKSPACE_DIR/scripts"/*.sh 2>/dev/null | wc -l) 个脚本"
    
    echo -e "\n${GREEN}⏰ Cron:${NC}"
    if command -v openclaw &>/dev/null && openclaw status &>/dev/null; then
        openclaw cron list 2>/dev/null | grep -E "backup|sync|archive" | head -5 || echo "  无备份相关cron"
    else
        echo "  OpenClaw 未运行"
    fi
}

# ==================== 帮助 ====================

cmd_help() {
    echo -e "${BLUE}restore-layer3-disaster.sh - 备灾恢复层${NC}"
    echo "======================================="
    echo ""
    echo "使用: bash restore-layer3-disaster.sh <command>"
    echo ""
    echo "命令:"
    echo "  snapshot    创建本地快照"
    echo "  cleanup     清理旧备份"
    echo "  offsite     异地备份（Git + S3）"
    echo "  restore     从备份恢复"
    echo "  status      状态检查"
    echo "  help        显示帮助"
    echo ""
    echo "环境变量:"
    echo "  WORKSPACE_DIR  工作目录（默认: /workspace/projects/workspace）"
    echo "  BACKUP_DIR     备份目录（默认: /data/backups/ai-trading-sync）"
    echo "  S3_BUCKET      S3/OSS bucket（可选）"
    echo "  MAX_BACKUPS    保留备份数量（默认: 30）"
}

# ==================== 主入口 ====================

case "${1:-help}" in
    snapshot)
        cmd_snapshot
        ;;
    cleanup)
        cmd_cleanup
        ;;
    offsite)
        cmd_offsite
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
        fail "未知命令: $1"
        cmd_help
        exit 1
        ;;
esac
