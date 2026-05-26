#!/bin/bash
# session-to-md.sh — 将 session JSONL 转换为可搜索的 MD 文件
# 用法: bash session-to-md.sh [output_dir]

set -euo pipefail

SESSIONS_DIR="/workspace/projects/agents/main/sessions"
OUTPUT_DIR="${1:-/workspace/projects/workspace/memory/sessions/raw}"
mkdir -p "$OUTPUT_DIR"

echo "📝 转换 Session JSONL → MD"
echo "================================"

count=0
for jsonl in "$SESSIONS_DIR"/*.jsonl*; do
    [ -f "$jsonl" ] || continue
    
    basename=$(basename "$jsonl" | sed 's/\.jsonl.*//')
    outfile="$OUTPUT_DIR/${basename}.md"
    
    # 跳过已转换的（检查文件修改时间）
    if [ -f "$outfile" ] && [ "$outfile" -nt "$jsonl" ]; then
        continue
    fi
    
    echo "  📄 转换: $(basename "$jsonl") → ${basename}.md"
    
    # 提取 User/Assistant 消息，转为可读格式
    python3 -c "
import json, sys, os
from datetime import datetime

input_file = sys.argv[1]
output_file = sys.argv[2]

messages = []
with open(input_file, 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            role = obj.get('role', '')
            content = obj.get('content', '')
            if role in ('user', 'assistant', 'system') and content:
                # 处理 content 可能是 list 的情况
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get('type') == 'text':
                            text_parts.append(part.get('text', ''))
                    content = ' '.join(text_parts)
                if content and len(content) > 5:
                    messages.append((role, content[:2000]))  # 截断过长内容
        except:
            continue

if not messages:
    sys.exit(0)

# 写入 MD
with open(output_file, 'w') as f:
    f.write(f'# Session: {os.path.basename(input_file)}\n\n')
    for role, content in messages:
        emoji = '👤' if role == 'user' else ('🤖' if role == 'assistant' else '⚙️')
        f.write(f'## {emoji} {role.title()}\n\n{content}\n\n---\n\n')

print(f'  ✅ {len(messages)} 条消息')
" "$jsonl" "$outfile" 2>/dev/null || echo "  ⚠️ 跳过: $(basename "$jsonl")"
    
    count=$((count + 1))
done

echo ""
echo "✅ 转换完成: $count 个文件"
echo "📂 输出目录: $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"/*.md 2>/dev/null | wc -l
echo "个 MD 文件"
