#!/bin/bash
# knowledge-index.sh — 生成知识库索引文件 INDEX.md
# 用途: 汇总 knowledge/ 下所有文件，生成结构化索引
# 调用方式: cron 每天执行，或手动
# 幂等: 每次全量重建（轻量操作）

set -euo pipefail

WORKSPACE_DIR="/workspace/projects/workspace"
KNOWLEDGE_DIR="${WORKSPACE_DIR}/knowledge"
INDEX_FILE="${KNOWLEDGE_DIR}/INDEX.md"
TODAY=$(date +%Y-%m-%d)

GREEN='\033[0;32m'
NC='\033[0m'
log_info() { echo -e "${GREEN}[INDEX]${NC} $1"; }

# 统计文件数量
count_files() {
    local dir="$1"
    find "$dir" -name "*.md" -type f 2>/dev/null | wc -l
}

# 获取文件摘要（第一行非空非标题内容）
file_summary() {
    local file="$1"
    grep -m1 -P '^[^#\-\s]' "$file" 2>/dev/null | head -c 100 || echo ""
}

# 获取文件大小
file_size() {
    local file="$1"
    local bytes=$(stat -c%s "$file" 2>/dev/null || echo 0)
    if [[ $bytes -gt 1024 ]]; then
        echo "$(( bytes / 1024 ))KB"
    else
        echo "${bytes}B"
    fi
}

# 生成索引
generate_index() {
    local b_count=$(count_files "${KNOWLEDGE_DIR}/B-practices")
    local g_count=$(count_files "${KNOWLEDGE_DIR}/G-guides")
    local r_count=$(count_files "${KNOWLEDGE_DIR}/R-rules")
    local total=$((b_count + g_count + r_count))

    cat > "${INDEX_FILE}" << EOF
# 📚 知识库索引

> **自动生成:** ${TODAY}  
> **总计:** ${total} 个文件  
> **分类:** B-practices(${b_count}) | G-guides(${g_count}) | R-rules(${r_count})

---

## 🔴 R-rules — 交易规则 (${r_count})

硬性规则、风控条件、技术约束。违反即止损。

EOF

    # 列出 R-rules
    if [[ -d "${KNOWLEDGE_DIR}/R-rules" ]]; then
        for f in "${KNOWLEDGE_DIR}/R-rules"/*.md; do
            [[ -f "$f" ]] || continue
            local name=$(basename "$f" .md)
            local size=$(file_size "$f")
            local summary=$(file_summary "$f")
            echo "- **[${name}]($(basename "$f"))** (${size})${summary:+ — ${summary}}" >> "${INDEX_FILE}"
        done
    fi

    cat >> "${INDEX_FILE}" << 'EOF'

---

## 🟢 G-guides — 指南与方法论

策略框架、分析方法、SOP流程、系统设计。

EOF

    # 列出 G-guides
    if [[ -d "${KNOWLEDGE_DIR}/G-guides" ]]; then
        for f in "${KNOWLEDGE_DIR}/G-guides"/*.md; do
            [[ -f "$f" ]] || continue
            local name=$(basename "$f" .md)
            local size=$(file_size "$f")
            local summary=$(file_summary "$f")
            echo "- **[${name}]($(basename "$f"))** (${size})${summary:+ — ${summary}}" >> "${INDEX_FILE}"
        done
    fi

    cat >> "${INDEX_FILE}" << 'EOF'

---

## 🔵 B-practices — 实战记录

交易实例、盈亏分析、反思教训。每笔交易都是学费。

EOF

    # 列出 B-practices
    if [[ -d "${KNOWLEDGE_DIR}/B-practices" ]]; then
        for f in "${KNOWLEDGE_DIR}/B-practices"/*.md; do
            [[ -f "$f" ]] || continue
            local name=$(basename "$f" .md)
            local size=$(file_size "$f")
            local summary=$(file_summary "$f")
            echo "- **[${name}]($(basename "$f"))** (${size})${summary:+ — ${summary}}" >> "${INDEX_FILE}"
        done
    fi

    cat >> "${INDEX_FILE}" << 'EOF'

---

## 📊 知识来源

| 来源 | 说明 |
|------|------|
| `memory/sessions/raw/` | Session完整transcripts（自动提取） |
| `chanlun-agent/knowledge/` | 缠论交易系统知识（统一合并） |
| `skills/.../knowledge/` | Skill附带知识（统一合并） |

## 🔄 自动化流程

| 脚本 | 频率 | 功能 |
|------|------|------|
| `session-to-md.sh` | 每小时 | Session JSONL → 完整MD |
| `knowledge-extract.sh` | 每6小时 | 从session提取B/G/R知识 |
| `knowledge-consolidate.sh` | 每天 | 统一散落知识文件 |
| `knowledge-index.sh` | 每天 | 重建本索引 |

---

*本文件由 knowledge-index.sh 自动生成，请勿手动编辑。*
EOF
}

# 主函数
main() {
    log_info "======================================"
    log_info "知识库索引构建 v1.0"
    log_info "时间: $(date)"
    log_info "======================================"

    mkdir -p "${KNOWLEDGE_DIR}"
    generate_index

    local total=$(grep -c '^\- \*\*' "${INDEX_FILE}" 2>/dev/null || echo 0)
    log_info "索引生成: ${total} 个条目"
    log_info "索引文件: ${INDEX_FILE}"
    log_info "✅ 索引构建完成"
}

main "$@"
