#!/bin/bash
# wav_to_ogg.sh - 将WAV文件转换为OGG OPUS格式（飞书语音消息）
# 用法: bash wav_to_ogg.sh input.wav [output.ogg]

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "用法: $0 input.wav [output.ogg]"
    echo "示例: $0 voice.wav voice.ogg"
    exit 1
fi

INPUT="$1"
OUTPUT="${2:-${INPUT%.wav}.ogg}"

if [ ! -f "$INPUT" ]; then
    echo "错误: 输入文件不存在: $INPUT"
    exit 1
fi

# 检查ffmpeg是否可用
if ! command -v ffmpeg &> /dev/null; then
    echo "错误: ffmpeg未安装"
    echo "请运行: apt-get install -y ffmpeg"
    exit 1
fi

# 转换为OGG OPUS
ffmpeg -y -i "$INPUT" -c:a libopus -b:a 32k "$OUTPUT" 2>/dev/null

if [ $? -eq 0 ]; then
    FILE_SIZE=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null)
    echo "✅ 转换成功: $OUTPUT ($FILE_SIZE bytes)"
else
    echo "错误: 转换失败"
    exit 1
fi
