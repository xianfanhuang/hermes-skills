#!/bin/bash
# memory-write.sh - 记忆写入工具
# 用途: 供 Agent 在对话中调用的记忆写入工具
# 调用方式: memory-write.sh "类别" "内容"

set -euo pipefail

WORKSPACE_DIR="/workspace/projects/workspace"
MEMORY_DIR="${WORKSPACE_DIR}/memory"
LONG_TERM_MEMORY="${WORKSPACE_DIR}/MEMORY.md"

# 当前日期
TODAY=$(date +%Y-%m-%d)
TODAY_MEMORY="${MEMORY_DIR}/${TODAY}.md"

# 确保目录存在
mkdir -p "${MEMORY_DIR}"

# 初始化今天的记忆文件（如果不存在）
if [[ ! -f "${TODAY_MEMORY}" ]]; then
    cat > "${TODAY_MEMORY}" << EOF
# ${TODAY} 每日记忆

## 📅 基本信息
- 日期: ${TODAY}
- 星期: $(date +%A)
- Agent: Trading Assistant 🦞

---

*自动生成时间: $(date "+%Y-%m-%d %H:%M:%S")*
EOF
fi

# 解析参数
CATEGORY="$1"
CONTENT="$2"

# 验证参数
if [[ -z "${CATEGORY}" ]] || [[ -z "${CONTENT}" ]]; then
    echo "用法: memory-write.sh \"类别\" \"内容\""
    echo ""
    echo "类别选项:"
    echo "  - preference   用户偏好"
    echo "  - decision     重要决策"
    echo "  - knowledge    学到的知识"
    echo "  - error        错误和教训"
    echo "  - observation  市场观察"
    echo "  - conversation 对话记录"
    echo ""
    echo "示例:"
    echo '  memory-write.sh preference "用户喜欢保守型策略，单笔最大亏损2%"'
    echo '  memory-write.sh decision "决定平仓 USO，触发止损 -5%"'
    exit 1
fi

# 根据类别选择标题
case "${CATEGORY}" in
    preference)
        TITLE="### 🎯 用户偏好"
        ;;
    decision)
        TITLE="### 📝 重要决策"
        ;;
    knowledge)
        TITLE="### 📚 学到的知识"
        ;;
    error)
        TITLE="### ⚠️ 错误和教训"
        ;;
    observation)
        TITLE="### 👁️ 市场观察"
        ;;
    conversation)
        TITLE="### 💬 对话记录"
        ;;
    *)
        TITLE="### 📝 ${CATEGORY}"
        ;;
esac

# 写入今天的记忆文件
echo "" >> "${TODAY_MEMORY}"

# 检查标题是否已存在
if ! grep -q "^${TITLE}$" "${TODAY_MEMORY}"; then
    echo "${TITLE}" >> "${TODAY_MEMORY}"
    echo "" >> "${TODAY_MEMORY}"
fi

# 写入内容（带时间戳）
echo "- **$(date "+%H:%M:%S")**: ${CONTENT}" >> "${TODAY_MEMORY}"

# 根据类别决定是否同步到长期记忆
if [[ "${CATEGORY}" == "preference" ]] || [[ "${CATEGORY}" == "knowledge" ]]; then
    # 同步到 MEMORY.md
    if [[ -f "${LONG_TERM_MEMORY}" ]]; then
        echo "" >> "${LONG_TERM_MEMORY}"
        echo "### ${TODAY} - ${CONTENT}" >> "${LONG_TERM_MEMORY}"
    fi
fi

# 输出成功信息
echo "✅ 已写入记忆文件"
echo "   文件: ${TODAY_MEMORY}"
echo "   类别: ${CATEGORY}"
echo "   内容: ${CONTENT}"
