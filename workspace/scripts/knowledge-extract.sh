#!/bin/bash
# knowledge-extract.sh — 从 session transcripts 自动提取知识到 B/G/R 分类
# 用途: 扫描 memory/sessions/raw/*.md，提取交易相关知识
# 调用方式: cron 每6小时执行一次，或手动
# 幂等: 按 session UUID 标记已处理，不重复提取

set -euo pipefail

WORKSPACE_DIR="/workspace/projects/workspace"
RAW_SESSIONS="${WORKSPACE_DIR}/memory/sessions/raw"
KNOWLEDGE_DIR="${WORKSPACE_DIR}/knowledge"
PROCESSED_MARKER="${KNOWLEDGE_DIR}/.extracted_sessions"
TODAY=$(date +%Y-%m-%d)

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
log_info() { echo -e "${GREEN}[EXTRACT]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[EXTRACT]${NC} $1"; }

# 初始化目录和标记文件
init() {
    mkdir -p "${KNOWLEDGE_DIR}/B-practices" "${KNOWLEDGE_DIR}/G-guides" "${KNOWLEDGE_DIR}/R-rules"
    touch "${PROCESSED_MARKER}"
}

# 检查session是否已处理
is_processed() {
    local uuid="$1"
    grep -qF "$uuid" "${PROCESSED_MARKER}" 2>/dev/null
}

# 标记session已处理
mark_processed() {
    local uuid="$1"
    echo "$uuid" >> "${PROCESSED_MARKER}"
}

# 生成内容hash（用于去重）
content_hash() {
    echo "$1" | md5sum | cut -d' ' -f1
}

# 从session内容中提取交易实践（B-practices）
extract_practices() {
    local content="$1"
    local uuid="$2"
    local practices_dir="${KNOWLEDGE_DIR}/B-practices"

    # 检测交易记录模式
    local trade_patterns=(
        "入场.*出场"
        "买入.*卖出"
        "盈亏.*%"
        "止损.*触发"
        "平仓"
        "开仓"
        "LONG.*SHORT"
        "做多.*做空"
        "止盈"
        "亏损.*反思"
    )

    local has_trade=false
    for pattern in "${trade_patterns[@]}"; do
        if echo "$content" | grep -qP "$pattern" 2>/dev/null; then
            has_trade=true
            break
        fi
    done

    if [[ "$has_trade" == "false" ]]; then
        return
    fi

    # 提取包含交易信息的段落
    local extracted=""
    local in_trade_section=false
    local section_buffer=""

    while IFS= read -r line; do
        # 检测交易相关段落开始
        if echo "$line" | grep -qP '(交易记录|交易分析|入场|出场|盈亏|止损|平仓|买入|卖出|LONG|SHORT|做多|做空)' 2>/dev/null; then
            in_trade_section=true
            section_buffer="${line}"
            continue
        fi

        if [[ "$in_trade_section" == "true" ]]; then
            # 空行或新段落标记结束
            if [[ -z "$line" ]] || echo "$line" | grep -qP '^#{1,3}\s' 2>/dev/null; then
                if [[ ${#section_buffer} -gt 30 ]]; then
                    extracted="${extracted}\n${section_buffer}\n"
                fi
                section_buffer=""
                in_trade_section=false
            else
                section_buffer="${section_buffer}\n${line}"
            fi
        fi
    done <<< "$content"

    # 最后一段
    if [[ "$in_trade_section" == "true" && ${#section_buffer} -gt 30 ]]; then
        extracted="${extracted}\n${section_buffer}\n"
    fi

    if [[ -n "$extracted" ]]; then
        local hash=$(content_hash "$extracted")
        local outfile="${practices_dir}/session_${uuid:0:8}_${hash:0:8}.md"

        if [[ ! -f "$outfile" ]]; then
            log_info "  → B-practices: ${outfile##*/}"
            {
                echo "# Session 提取 - 交易实践"
                echo ""
                echo "- **来源 Session:** ${uuid}"
                echo "- **提取日期:** ${TODAY}"
                echo "- **类型:** 实战记录"
                echo ""
                echo "---"
                echo ""
                echo -e "$extracted"
                echo ""
                echo "---"
                echo "*自动提取 by knowledge-extract.sh*"
            } > "$outfile"
        fi
    fi
}

# 从session内容中提取规则（R-rules）
extract_rules() {
    local content="$1"
    local uuid="$2"
    local rules_dir="${KNOWLEDGE_DIR}/R-rules"

    local rule_patterns=(
        "规则.*:"
        "必须.*"
        "禁止.*"
        "不允许.*"
        "风控.*:"
        "止损.*规则"
        "条件.*:"
        "如果.*则.*"
        "当.*时.*"
        "限制.*:"
    )

    local has_rules=false
    for pattern in "${rule_patterns[@]}"; do
        if echo "$content" | grep -qP "$pattern" 2>/dev/null; then
            has_rules=true
            break
        fi
    done

    if [[ "$has_rules" == "false" ]]; then
        return
    fi

    # 提取规则性内容
    local extracted=""
    while IFS= read -r line; do
        if echo "$line" | grep -qP '(规则|必须|禁止|不允许|风控|止损.*条件|限制|当.*时|如果.*则|不超过|大于|小于|触发条件)' 2>/dev/null; then
            if [[ ${#line} -gt 10 && ${#line} -lt 500 ]]; then
                extracted="${extracted}\n- ${line}"
            fi
        fi
    done <<< "$content"

    if [[ -n "$extracted" ]]; then
        local hash=$(content_hash "$extracted")
        local outfile="${rules_dir}/session_${uuid:0:8}_${hash:0:8}.md"

        if [[ ! -f "$outfile" ]]; then
            log_info "  → R-rules: ${outfile##*/}"
            {
                echo "# Session 提取 - 交易规则"
                echo ""
                echo "- **来源 Session:** ${uuid}"
                echo "- **提取日期:** ${TODAY}"
                echo "- **类型:** 规则提取"
                echo ""
                echo "---"
                echo ""
                echo "## 提取的规则"
                echo ""
                echo -e "$extracted"
                echo ""
                echo "---"
                echo "*自动提取 by knowledge-extract.sh*"
            } > "$outfile"
        fi
    fi
}

# 从session内容中提取指南/洞察（G-guides）
extract_guides() {
    local content="$1"
    local uuid="$2"
    local guides_dir="${KNOWLEDGE_DIR}/G-guides"

    local guide_patterns=(
        "策略.*:"
        "方法.*:"
        "框架.*:"
        "SOP"
        "流程.*:"
        "步骤.*:"
        "建议.*:"
        "最佳实践"
        "优化.*方案"
        "改进.*措施"
        "学到.*"
        "经验.*:"
        "洞察.*:"
        "发现.*:"
    )

    local has_guides=false
    for pattern in "${guide_patterns[@]}"; do
        if echo "$content" | grep -qP "$pattern" 2>/dev/null; then
            has_guides=true
            break
        fi
    done

    if [[ "$has_guides" == "false" ]]; then
        return
    fi

    # 提取指南性内容
    local extracted=""
    local in_guide=false
    local section_buffer=""

    while IFS= read -r line; do
        if echo "$line" | grep -qP '(策略|方法|框架|SOP|流程|步骤|建议|最佳实践|优化|改进|学到|经验|洞察|发现|分析方法|判断标准)' 2>/dev/null; then
            in_guide=true
            section_buffer="${line}"
            continue
        fi

        if [[ "$in_guide" == "true" ]]; then
            if [[ -z "$line" ]] || echo "$line" | grep -qP '^#{1,3}\s' 2>/dev/null; then
                if [[ ${#section_buffer} -gt 20 ]]; then
                    extracted="${extracted}\n${section_buffer}\n"
                fi
                section_buffer=""
                in_guide=false
            else
                section_buffer="${section_buffer}\n${line}"
            fi
        fi
    done <<< "$content"

    if [[ "$in_guide" == "true" && ${#section_buffer} -gt 20 ]]; then
        extracted="${extracted}\n${section_buffer}\n"
    fi

    if [[ -n "$extracted" ]]; then
        local hash=$(content_hash "$extracted")
        local outfile="${guides_dir}/session_${uuid:0:8}_${hash:0:8}.md"

        if [[ ! -f "$outfile" ]]; then
            log_info "  → G-guides: ${outfile##*/}"
            {
                echo "# Session 提取 - 技术洞察"
                echo ""
                echo "- **来源 Session:** ${uuid}"
                echo "- **提取日期:** ${TODAY}"
                echo "- **类型:** 方法论/洞察"
                echo ""
                echo "---"
                echo ""
                echo -e "$extracted"
                echo ""
                echo "---"
                echo "*自动提取 by knowledge-extract.sh*"
            } > "$outfile"
        fi
    fi
}

# 处理单个session文件
process_session() {
    local file="$1"
    local uuid=$(basename "$file" .md)

    if is_processed "$uuid"; then
        return
    fi

    log_info "处理: ${uuid:0:12}..."

    local content=$(cat "$file")

    # 跳过太短的session（可能是空的或只有heartbeat）
    local content_len=${#content}
    if [[ $content_len -lt 200 ]]; then
        mark_processed "$uuid"
        return
    fi

    # 跳过纯heartbeat session
    if echo "$content" | grep -qP 'HEARTBEAT_OK' 2>/dev/null; then
        local non_heartbeat=$(echo "$content" | grep -vP '(HEARTBEAT|heartbeat)' | wc -c)
        if [[ $non_heartbeat -lt 200 ]]; then
            mark_processed "$uuid"
            return
        fi
    fi

    extract_practices "$content" "$uuid"
    extract_rules "$content" "$uuid"
    extract_guides "$content" "$uuid"

    mark_processed "$uuid"
}

# 主函数
main() {
    log_info "======================================"
    log_info "Session → 知识提取 v1.0"
    log_info "时间: $(date)"
    log_info "======================================"

    init

    local total=0
    local extracted=0

    if [[ ! -d "${RAW_SESSIONS}" ]]; then
        log_warn "Session目录不存在: ${RAW_SESSIONS}"
        return
    fi

    for session_file in "${RAW_SESSIONS}"/*.md; do
        [[ -f "$session_file" ]] || continue
        total=$((total + 1))
        local uuid=$(basename "$session_file" .md)
        if ! is_processed "$uuid"; then
            process_session "$session_file"
            extracted=$((extracted + 1))
        fi
    done

    log_info "======================================"
    log_info "扫描: ${total} 个session | 新提取: ${extracted} 个"
    log_info "知识库统计:"
    log_info "  B-practices: $(find "${KNOWLEDGE_DIR}/B-practices" -name "*.md" -type f 2>/dev/null | wc -l) 个文件"
    log_info "  G-guides:    $(find "${KNOWLEDGE_DIR}/G-guides" -name "*.md" -type f 2>/dev/null | wc -l) 个文件"
    log_info "  R-rules:     $(find "${KNOWLEDGE_DIR}/R-rules" -name "*.md" -type f 2>/dev/null | wc -l) 个文件"
    log_info "✅ 知识提取完成"
}

main "$@"
