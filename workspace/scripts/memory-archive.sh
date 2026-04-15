#!/bin/bash
# memory-archive.sh - 记忆归档脚本
# 用途: 压缩和归档旧的记忆文件
# 执行时机: 每天凌晨 2:00

set -euo pipefail

# 配置
WORKSPACE_DIR="/workspace/projects/workspace"
MEMORY_DIR="${WORKSPACE_DIR}/memory"
ARCHIVE_DIR="${MEMORY_DIR}/archive"
ARCHIVE_THRESHOLD_DAYS=30  # 超过30天的记忆归档

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 创建归档目录
mkdir -p "${ARCHIVE_DIR}"

# 获取当前日期
TODAY=$(date +%Y-%m-%d)

log_info "======================================"
log_info "OpenClaw 记忆归档任务"
log_info "时间: ${TODAY}"
log_info "======================================"

# 1. 压缩超过阈值的记忆文件
log_info "检查超过 ${ARCHIVE_THRESHOLD_DAYS} 天的记忆文件..."

count=0
for memory_file in "${MEMORY_DIR}"/*.md; do
    # 跳过归档目录
    [[ "${memory_file}" == "${ARCHIVE_DIR}"* ]] && continue

    # 跳过今天的文件
    [[ "$(basename "${memory_file}")" == "${TODAY}.md" ]] && continue

    # 检查文件日期
    file_date=$(basename "${memory_file}" .md)
    file_seconds=$(date -d "${file_date}" +%s 2>/dev/null || echo "0")
    threshold_seconds=$(date -d "${ARCHIVE_THRESHOLD_DAYS} days ago" +%s)

    if [[ "${file_seconds}" -lt "${threshold_seconds}" && "${file_seconds}" -gt 0 ]]; then
        log_info "归档: ${memory_file}"

        # 创建归档压缩包
        gzip -c "${memory_file}" > "${ARCHIVE_DIR}/${file_date}.md.gz"
        rm "${memory_file}"
        ((count++))
    fi
done

if [[ ${count} -eq 0 ]]; then
    log_info "没有需要归档的记忆文件"
else
    log_info "✅ 已归档 ${count} 个记忆文件"
fi

# 2. 生成记忆目录统计
log_info "记忆目录统计:"
echo ""
echo "文件数量: $(ls -1 "${MEMORY_DIR}"/*.md 2>/dev/null | wc -l)"
echo "归档数量: $(ls -1 "${ARCHIVE_DIR}"/*.md.gz 2>/dev/null | wc -l)"
echo ""
echo "最近的记忆文件:"
ls -lt "${MEMORY_DIR}"/*.md 2>/dev/null | head -5 | awk '{print $9}' | xargs -I {} basename {}
echo ""
echo "归档的记忆文件:"
ls -lt "${ARCHIVE_DIR}"/*.md.gz 2>/dev/null | head -5 | awk '{print $9}' | xargs -I {} basename {}

log_info "✅ 记忆归档任务完成"
