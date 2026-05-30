# Voice Assistant Skill

中英双语语音消息生成与识别，基于小米MIMO TTS引擎。

## 快速开始

### TTS 引擎选择

| 引擎 | 说明 | 默认 |
|------|------|------|
| **MIMO** | 小米MIMO TTS，中英双语自然 | ✅ 默认 |
| **Coze** | 扣子TTS，中文音色丰富 | 备用 |

### 1. 生成语音（MIMO默认）

```bash
# 列出可用音色
python3 scripts/mimo_tts.py --list-voices

# 生成语音文件
python3 scripts/mimo_tts.py --text "你好，我是AI助手" --voice Milo --output voice.wav

# 转换为飞书语音格式
bash scripts/wav_to_ogg.sh voice.wav voice.ogg
```

### 1. 生成语音（Coze备用）

```bash
# 使用coze-voice-gen技能
npx ts-node ../coze-voice-gen/scripts/tts.ts --text "你好" --speaker zh_male_taocheng_uranus_bigtts --format ogg_opus
```

### 2. 发送飞书语音消息

使用 OpenClaw message tool:
```json
{
  "action": "send",
  "asVoice": true,
  "media": "/path/to/voice.ogg",
  "message": "语音消息"
}
```

## 可用音色

### 中文音色
- **冰糖**: 女声，中文标准
- **茉莉**: 女声，中文自然
- **苏打**: 男声，中文标准
- **白桦**: 男声，中文沉稳
- **mimo_default**: 默认，中性

### 中英双语音色（推荐）
- **Mia**: 女声，英文流畅
- **Chloe**: 女声，中文自然
- **Milo**: 男声，中英双语最佳（推荐）
- **Dean**: 男声，英文沉稳

## 归档特性

- **上下文**: 语音转录后以文字形式存入，不额外膨胀
- **Session归档**: 只存转录文字，不存音频源文件
- **搜索**: 转录文字可搜索，音频文件不可搜索
- **存储**: 音频文件可能被清理，重要内容及时转录

## 文件结构

```
voice-assistant/
├── SKILL.md                 # 技能说明
├── README.md               # 本文件
├── scripts/
│   ├── mimo_tts.py        # MIMO TTS脚本
│   └── wav_to_ogg.sh      # WAV转OGG脚本
└── references/
    ├── voice-options.md    # 音色选项详解
    └── archival-guide.md   # 归档特性指南
```

## 技术参数

### MIMO TTS（默认）
- **模型**: mimo-v2.5-tts
- **API**: OpenAI兼容 (chat/completions)
- **音频格式**: WAV → OGG OPUS
- **采样率**: 24kHz
- **飞书格式**: OGG OPUS (asVoice=true)

### Coze TTS（备用）
- **模型**: coze-coding-dev-sdk
- **API**: 扣子TTS API
- **音频格式**: OGG OPUS直接输出
- **采样率**: 24kHz
- **飞书格式**: OGG OPUS (asVoice=true)

## 注意事项

1. MIMO TTS API需要assistant角色消息
2. 飞书语音消息必须是OGG OPUS格式
3. 长语音建议分段发送
4. 音频文件可能被清理，重要内容及时转录

## 团队使用

1. 安装依赖: `apt-get install -y ffmpeg`
2. 配置MIMO API Key (OpenClaw配置文件)
3. 使用脚本生成和发送语音消息
4. 参考references/目录了解详细用法
