#!/usr/bin/env python3
"""
MIMO TTS 语音合成脚本
用法: python3 mimo_tts.py --text "要说的话" --voice Milo --output output.wav
"""

import argparse
import json
import base64
import os
import sys
import urllib.request


def get_api_key():
    """从OpenClaw配置文件读取MIMO API Key"""
    config_path = os.path.expanduser("/workspace/projects/openclaw.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
        return config['models']['providers']['xiaomimimo']['apiKey']
    except (FileNotFoundError, KeyError):
        print("错误: 无法读取MIMO API Key", file=sys.stderr)
        sys.exit(1)


def list_voices():
    """列出所有可用音色"""
    voices = {
        "中文音色": {
            "冰糖": "女声，中文标准",
            "茉莉": "女声，中文自然", 
            "苏打": "男声，中文标准",
            "白桦": "男声，中文沉稳",
            "mimo_default": "默认，中性"
        },
        "中英双语音色": {
            "Mia": "女声，英文流畅",
            "Chloe": "女声，中文自然",
            "Milo": "男声，中英双语最佳（推荐）",
            "Dean": "男声，英文沉稳"
        }
    }
    
    print("=== 可用音色 ===")
    for category, voice_list in voices.items():
        print(f"\n{category}:")
        for name, desc in voice_list.items():
            print(f"  {name}: {desc}")
    print()


def synthesize(text, voice="Milo", output="output.wav"):
    """调用MIMO TTS API合成语音"""
    api_key = get_api_key()
    
    payload = {
        "model": "mimo-v2.5-tts",
        "messages": [
            {"role": "user", "content": "请用语音回复"},
            {"role": "assistant", "content": text}
        ],
        "modalities": ["text", "audio"],
        "audio": {"voice": voice, "format": "wav"}
    }
    
    req = urllib.request.Request(
        "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        
        if 'error' in data:
            print(f"API错误: {data['error']['message']}", file=sys.stderr)
            sys.exit(1)
        
        audio_data = data['choices'][0]['message']['audio']['data']
        
        with open(output, 'wb') as f:
            f.write(base64.b64decode(audio_data))
        
        file_size = os.path.getsize(output)
        print(f"✅ 语音合成成功: {output} ({file_size} bytes)")
        return True
        
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="MIMO TTS 语音合成")
    parser.add_argument("--text", "-t", help="要合成的文字")
    parser.add_argument("--voice", "-v", default="Milo", help="音色名称 (默认: Milo)")
    parser.add_argument("--output", "-o", default="output.wav", help="输出文件路径")
    parser.add_argument("--list-voices", "-l", action="store_true", help="列出可用音色")
    
    args = parser.parse_args()
    
    if args.list_voices:
        list_voices()
        return
    
    if not args.text:
        parser.error("需要指定 --text 参数")
    
    synthesize(args.text, args.voice, args.output)


if __name__ == "__main__":
    main()
