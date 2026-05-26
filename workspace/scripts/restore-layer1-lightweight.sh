#!/bin/bash
# restore-layer1-lightweight.sh - 轻量恢复层
# 用途: 在无运行环境的客户端（如豆包、ChatGPT等）上恢复知识库和记忆
# 方式: 通过GitHub raw URL fetch，无需git/ssh
# 使用: curl -sL https://raw.githubusercontent.com/xianfanhuang/ai-trading-sync/main/scripts/restore-layer1-lightweight.sh | bash

set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/xianfanhuang/ai-trading-sync/main"
OUTPUT_DIR="${1:-./ai-trading-sync}"

echo "======================================="
echo "🔄 轻量恢复层 - Layer 1"
echo "用途: 无运行环境客户端恢复"
echo "输出: $OUTPUT_DIR"
echo "======================================="

mkdir -p "$OUTPUT_DIR"

# 核心文件列表（最小可用集）
LIGHTWEIGHT_FILES=(
    "MEMORY.md"
    "USER.md"
    "IDENTITY.md"
    "SOUL.md"
    "AGENTS.md"
    "TOOLS.md"
    "RESTORE.md"
    "knowledge/INDEX.md"
)

# 知识库索引（精简版，只下载索引）
KNOWLEDGE_INDEX="knowledge/INDEX.md"

# 记忆文件（最近7天）
echo ""
echo "📦 下载核心文件..."

for file in "${LIGHTWEIGHT_FILES[@]}"; do
    echo -n "  $file ... "
    dir=$(dirname "$OUTPUT_DIR/$file")
    mkdir -p "$dir"
    curl -sL "$REPO_RAW/$file" -o "$OUTPUT_DIR/$file" 2>/dev/null && echo "✅" || echo "❌"
done

# 生成上下文摘要（供AI客户端使用）
echo ""
echo "📝 生成上下文摘要..."

cat > "$OUTPUT_DIR/CONTEXT.md" << 'CONTEXT_EOF'
# 🦞 Trading Assistant - 上下文摘要

> 此文件由轻量恢复层自动生成，供无运行环境的AI客户端使用

## 身份
- **团队**: Meta-Sensory Intelligence Ltd
- **角色**: First Mate (大副) + 自主交易项目负责人
- **签名Emoji**: 🦞
- **汇报对象**: Captain (VAN)

## 核心交易哲学
> 凡强趋必然浅回调，不论多空。

- 流畅趋势 = 小级别长时间延续 = 主力目标
- 缠论无多空之分，只有买卖点
- 结构状态驱动，非波动率驱动

## 风控规则
- 单笔最大亏损: 2%
- 日最大亏损: 6%
- 连亏熔断: 3连亏暂停
- 技术止损: 中枢外沿

## 分析框架
1. 日线大趋势定方向
2. 有没有反转
3. 买卖点是什么性质
4. 当下该做什么

## 知识库结构
- **B-practices/**: 实战记录（交易案例）
- **G-guides/**: 指南（缠论体系、SOP）
- **R-rules/**: 规则（笔、中枢、背驰规则）

## 如何获取完整知识
1. 查看 knowledge/INDEX.md 了解所有知识文件
2. 使用 GitHub 链接获取完整内容:
   https://github.com/xianfanhuang/ai-trading-sync/blob/main/knowledge/{分类}/{文件名}.md
CONTEXT_EOF

echo "  ✅ CONTEXT.md 已生成"

# 生成知识库快速查询表
echo ""
echo "📚 生成知识库快速查询表..."

if [ -f "$OUTPUT_DIR/knowledge/INDEX.md" ]; then
    # 提取所有知识文件的GitHub链接
    cat > "$OUTPUT_DIR/KNOWLEDGE_LINKS.md" << 'LINKS_EOF'
# 📚 知识库快速查询

> 点击链接直接查看完整内容

## 实战记录 (B-practices)
LINKS_EOF
    
    # 提取B-practices文件
    grep -oP "B-practices/[a-zA-Z0-9_-]+\.md" "$OUTPUT_DIR/knowledge/INDEX.md" 2>/dev/null | while read f; do
        echo "- [$f](https://github.com/xianfanhuang/ai-trading-sync/blob/main/$f)" >> "$OUTPUT_DIR/KNOWLEDGE_LINKS.md"
    done
    
    echo "" >> "$OUTPUT_DIR/KNOWLEDGE_LINKS.md"
    echo "## 指南 (G-guides)" >> "$OUTPUT_DIR/KNOWLEDGE_LINKS.md"
    grep -oP "G-guides/[a-zA-Z0-9_-]+\.md" "$OUTPUT_DIR/knowledge/INDEX.md" 2>/dev/null | while read f; do
        echo "- [$f](https://github.com/xianfanhuang/ai-trading-sync/blob/main/$f)" >> "$OUTPUT_DIR/KNOWLEDGE_LINKS.md"
    done
    
    echo "" >> "$OUTPUT_DIR/KNOWLEDGE_LINKS.md"
    echo "## 规则 (R-rules)" >> "$OUTPUT_DIR/KNOWLEDGE_LINKS.md"
    grep -oP "R-rules/[a-zA-Z0-9_-]+\.md" "$OUTPUT_DIR/knowledge/INDEX.md" 2>/dev/null | while read f; do
        echo "- [$f](https://github.com/xianfanhuang/ai-trading-sync/blob/main/$f)" >> "$OUTPUT_DIR/KNOWLEDGE_LINKS.md"
    done
    
    echo "  ✅ KNOWLEDGE_LINKS.md 已生成"
fi

# 生成使用说明
echo ""
echo "======================================="
echo "✅ 轻量恢复完成！"
echo ""
echo "📁 输出目录: $OUTPUT_DIR"
echo ""
echo "📋 文件列表:"
ls -la "$OUTPUT_DIR/"
echo ""
echo "💡 使用方式:"
echo "  1. 将 CONTEXT.md 内容粘贴到AI客户端作为系统提示"
echo "  2. 查看 KNOWLEDGE_LINKS.md 获取知识库链接"
echo "  3. 点击链接查看完整知识内容"
echo ""
echo "⚠️  注意: 此模式仅用于讨论/规划，不支持自动执行"
echo "======================================="
