#!/bin/bash
# knowledge-consolidate.sh — 统一散落在三处的知识文件到 knowledge/
# 用途: 将 chanlun-agent/knowledge/ 和 skills/.../knowledge/ 的文件复制到统一位置
# 调用方式: cron 每天执行，或手动
# 幂等: 按文件名+内容hash去重，不重复复制

set -euo pipefail

WORKSPACE_DIR="/workspace/projects/workspace"
KNOWLEDGE_DIR="${WORKSPACE_DIR}/knowledge"
CONSOLIDATED_MARKER="${KNOWLEDGE_DIR}/.consolidated_sources"
TODAY=$(date +%Y-%m-%d)

# 知识来源目录
SOURCE_DIRS=(
    "${WORKSPACE_DIR}/chanlun-agent/knowledge"
    "${WORKSPACE_DIR}/skills/hermes-skills/trading-assistant/knowledge"
    "${WORKSPACE_DIR}/knowledge"
)

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
log_info() { echo -e "${GREEN}[CONSOLIDATE]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[CONSOLIDATE]${NC} $1"; }

# 初始化
init() {
    mkdir -p "${KNOWLEDGE_DIR}/B-practices" "${KNOWLEDGE_DIR}/G-guides" "${KNOWLEDGE_DIR}/R-rules"
    touch "${CONSOLIDATED_MARKER}"
}

# 文件内容hash
file_hash() {
    md5sum "$1" 2>/dev/null | cut -d' ' -f1
}

# 检查文件是否已合并（按相对路径+hash）
is_consolidated() {
    local src="$1"
    local hash="$2"
    local key="${src}:${hash}"
    grep -qF "$key" "${CONSOLIDATED_MARKER}" 2>/dev/null
}

# 标记已合并
mark_consolidated() {
    local src="$1"
    local hash="$2"
    echo "${src}:${hash}" >> "${CONSOLIDATED_MARKER}"
}

# 根据文件名/路径判断目标分类
classify_file() {
    local filepath="$1"
    local filename=$(basename "$filepath")
    local dirpath=$(dirname "$filepath")

    # 已在B/G/R子目录中
    if echo "$dirpath" | grep -qP '/B-practices(/|$)'; then
        echo "B-practices"
        return
    fi
    if echo "$dirpath" | grep -qP '/G-guides(/|$)'; then
        echo "G-guides"
        return
    fi
    if echo "$dirpath" | grep -qP '/R-rules(/|$)'; then
        echo "R-rules"
        return
    fi

    # 按文件名关键词分类
    if echo "$filename" | grep -qiP '(loss|win|profit|trade|实践|实战|记录|reflection|反思)'; then
        echo "B-practices"
        return
    fi
    if echo "$filename" | grep -qiP '(rule|规则|风控|止损|条件)'; then
        echo "R-rules"
        return
    fi
    if echo "$filename" | grep -qiP '(guide|sop|method|策略|方法|框架|system|体系|mapping|映射)'; then
        echo "G-guides"
        return
    fi

    # 按内容关键词分类（读取前20行）
    local head_content=$(head -20 "$filepath" 2>/dev/null || echo "")
    if echo "$head_content" | grep -qiP '(交易记录|入场.*出场|盈亏|平仓)'; then
        echo "B-practices"
        return
    fi
    if echo "$head_content" | grep -qiP '(规则|必须|禁止|风控|条件|触发)'; then
        echo "R-rules"
        return
    fi

    # 默认归入 G-guides
    echo "G-guides"
}

# 合并单个文件
consolidate_file() {
    local src="$1"
    local filename=$(basename "$src")
    local src_hash=$(file_hash "$src")
    local rel_path="${src#${WORKSPACE_DIR}/}"

    # 跳过已合并
    if is_consolidated "$rel_path" "$src_hash"; then
        return
    fi

    # 跳过空文件或太小的文件
    local size=$(stat -c%s "$src" 2>/dev/null || echo 0)
    if [[ $size -lt 50 ]]; then
        mark_consolidated "$rel_path" "$src_hash"
        return
    fi

    local category=$(classify_file "$src")
    local dest_dir="${KNOWLEDGE_DIR}/${category}"

    # 如果目标位置就是源位置（knowledge/下的B/G/R），只标记不复制
    if echo "$src" | grep -qP "^${KNOWLEDGE_DIR}/(B-practices|G-guides|R-rules)/" 2>/dev/null; then
        mark_consolidated "$rel_path" "$src_hash"
        return
    fi

    # 检查目标文件是否已存在（同名文件）
    local dest="${dest_dir}/${filename}"
    if [[ -f "$dest" ]]; then
        local dest_hash=$(file_hash "$dest")
        if [[ "$dest_hash" == "$src_hash" ]]; then
            mark_consolidated "$rel_path" "$src_hash"
            return
        fi
        # 内容不同，添加来源后缀
        local name_no_ext="${filename%.md}"
        dest="${dest_dir}/${name_no_ext}_$(echo "$rel_path" | md5sum | cut -c1-8).md"
    fi

    log_info "  ${rel_path} → ${category}/${filename}"
    cp "$src" "$dest"
    mark_consolidated "$rel_path" "$src_hash"
}

# 清理已不存在的源文件对应的目标文件
cleanup_orphans() {
    log_info "检查孤立文件..."
    local cleaned=0

    for category in B-practices G-guides R-rules; do
        local dir="${KNOWLEDGE_DIR}/${category}"
        [[ -d "$dir" ]] || continue

        for target_file in "${dir}"/*.md; do
            [[ -f "$target_file" ]] || continue
            local filename=$(basename "$target_file")

            # 跳过session提取的文件（由knowledge-extract.sh管理）
            if echo "$filename" | grep -qP '^session_'; then
                continue
            fi

            # 检查源文件是否还存在
            local found=false
            for src_dir in "${SOURCE_DIRS[@]}"; do
                [[ -d "$src_dir" ]] || continue
                # 在源目录中查找同名文件
                local found_file
                found_file=$(find "$src_dir" -name "$filename" -type f 2>/dev/null || true)
                if [[ -n "$found_file" ]]; then
                    found=true
                    break
                fi
            done || true

            # 如果源文件不存在且不是手动创建的，标记为可清理
            if [[ "$found" == "false" ]]; then
                # 不删除，只记录日志
                log_warn "  孤立文件: ${category}/${filename}（源文件已不存在）"
                cleaned=$((cleaned + 1))
            fi
        done
    done

    [[ $cleaned -gt 0 ]] && log_info "发现 ${cleaned} 个孤立文件" || true
}

# 主函数
main() {
    log_info "======================================"
    log_info "知识文件统一 v1.0"
    log_info "时间: $(date)"
    log_info "======================================"

    init

    local total=0
    local consolidated=0

    for src_dir in "${SOURCE_DIRS[@]}"; do
        [[ -d "$src_dir" ]] || continue
        log_info "扫描: ${src_dir#${WORKSPACE_DIR}/}"

        while IFS= read -r -d '' file; do
            [[ -f "$file" ]] || continue
            total=$((total + 1))

            local rel_path="${file#${WORKSPACE_DIR}/}"
            local src_hash=$(file_hash "$file")

            if ! is_consolidated "$rel_path" "$src_hash"; then
                consolidate_file "$file"
                consolidated=$((consolidated + 1))
            fi
        done < <(find "$src_dir" -name "*.md" -type f -print0 2>/dev/null)
    done

    # 移除根目录下已迁移到子目录的文件
    # （knowledge/chanlun-meta-trading-system.md 等已在consolidate时复制到G-guides）

    cleanup_orphans

    log_info "======================================"
    log_info "扫描: ${total} 个文件 | 新合并: ${consolidated} 个"
    log_info "知识库统计:"
    log_info "  B-practices: $(find "${KNOWLEDGE_DIR}/B-practices" -name "*.md" -type f 2>/dev/null | wc -l) 个文件"
    log_info "  G-guides:    $(find "${KNOWLEDGE_DIR}/G-guides" -name "*.md" -type f 2>/dev/null | wc -l) 个文件"
    log_info "  R-rules:     $(find "${KNOWLEDGE_DIR}/R-rules" -name "*.md" -type f 2>/dev/null | wc -l) 个文件"
    log_info "✅ 知识统一完成"
}

main "$@"
