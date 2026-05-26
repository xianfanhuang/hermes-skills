#!/bin/bash
# 记忆搜索脚本 - 支持自动解压搜索

set -e

MEMORY_DIR="/workspace/projects/workspace/memory"
QUERY="$1"

if [ -z "$QUERY" ]; then
    echo "用法: $0 <搜索关键词>"
    echo "示例: $0 缠论"
    exit 1
fi

echo "🔍 搜索记忆: $QUERY"
echo "================================"

# 搜索普通.md文件
echo ""
echo "【普通文件】"
find "$MEMORY_DIR" -name "*.md" -not -path "*/archive/*" -exec grep -l "$QUERY" {} \; 2>/dev/null | while read file; do
    echo "  📄 $file"
    grep -n "$QUERY" "$file" | head -3 | while read line; do
        echo "      $line"
    done
done

# 搜索压缩的.md.gz文件
echo ""
echo "【压缩文件】"
find "$MEMORY_DIR" -name "*.md.gz" -exec zgrep -l "$QUERY" {} \; 2>/dev/null | while read file; do
    echo "  📦 $file"
    zgrep -n "$QUERY" "$file" | head -3 | while read line; do
        echo "      $line"
    done
done

# 搜索sessions目录
echo ""
echo "【Session记录】"
find "$MEMORY_DIR/sessions" -name "*.md" -exec grep -l "$QUERY" {} \; 2>/dev/null | while read file; do
    echo "  💬 $file"
    grep -n "$QUERY" "$file" | head -3 | while read line; do
        echo "      $line"
    done
done

echo ""
echo "================================"
echo "搜索完成"
