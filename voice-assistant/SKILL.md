---
name: voice-assistant
description: "中英双语语音消息生成与识别。MIMO TTS语音合成 + ASR语音转录，支持飞书语音消息格式。"
version: 1.0.0
author: First-Mate-feishu
created: 2026-05-31
updated: 2026-05-31
---

# Voice Assistant

中英双语语音消息生成与识别，基于小米MIMO TTS引擎。

## 核心能力

| 能力 | 说明 |
|------|------|
| **TTS** | 文字→语音（MIMO mimo-v2.5-tts） |
| **ASR** | 语音→文字（coze-voice-gen ASR） |
| **飞书语音** | OGG OPUS格式，可直接播放 |

## TTS 引擎选择

| 引擎 | 说明 | 默认 |
|------|------|------|
| **MIMO** | 小米MIMO TTS，中英双语自然 | ✅ 默认 |
| **Coze** | 扣子TTS，中文音色丰富 | 备用 |

### MIMO TTS（默认）

```bash
# 1. 调用MIMO TTS API生成WAV
python3 scripts/mimo_tts.py --text "要转换的文字" --voice Milo --output /tmp/output.wav

# 2. 转换为OGG OPUS（飞书语音消息格式）
ffmpeg -y -i /tmp/output.wav -c:a libopus -b:a 32k /tmp/output.ogg

# 3. 发送飞书语音消息（Coze端）
# 复制到用户上传目录，用 computer:// 协议引用
cp /tmp/output.ogg ./用户上传/output.ogg
# 发送格式: [描述](computer://用户上传/output.ogg)
```

**Coze 飞书渠道语音消息格式**（2026-05-31验证）：
```markdown
[语音消息](computer://用户上传/filename.ogg)
```
- 文件必须放在 `./用户上传/` 目录下
- 使用 `computer://` 协议引用（不是 `file://`）
- 格式必须是 **OGG OPUS**（24kHz，单声道，32kbps）
- 其他格式（MP3/WAV）会显示为文件附件而非语音卡片

### Coze TTS（备用）

```bash
# 使用coze-voice-gen技能
npx ts-node {baseDir}/../coze-voice-gen/scripts/tts.ts --text "要转换的文字" --speaker zh_male_taocheng_uranus_bigtts --format ogg_opus
```

## ASR 工作流程

```bash
# 使用coze-voice-gen进行语音识别
npx ts-node {baseDir}/../coze-voice-gen/scripts/asr.ts --file /path/to/audio.ogg
```

## 可用音色

### 中文音色

| 音色 | 类型 | 特点 |
|------|------|------|
| 冰糖 | 女声 | 中文标准 |
| 茉莉 | 女声 | 中文自然 |
| 苏打 | 男声 | 中文标准 |
| 白桦 | 男声 | 中文沉稳 |
| mimo_default | 默认 | 中性 |

### 中英双语音色（推荐）

| 音色 | 类型 | 特点 |
|------|------|------|
| Mia | 女声 | 英文流畅 |
| Chloe | 女声 | 中文自然 |
| **Milo** | 男声 | 中英双语最佳（推荐） |
| Dean | 男声 | 英文沉稳 |

## 飞书语音消息格式

| 格式 | 效果 |
|------|------|
| OGG OPUS + asVoice=true | ✅ 语音消息（可直接播放） |
| MP3 | ❌ 变成文件附件 |
| WAV | ❌ 变成文件附件 |

## 归档特性

| 特性 | 说明 |
|------|------|
| **上下文** | 语音转录后以文字形式存入上下文，不额外膨胀 |
| **Session归档** | 只存转录文字，不存音频源文件 |
| **搜索** | 转录文字可搜索，音频文件不可搜索 |
| **存储** | 音频文件存在 media/inbound/，可能被清理 |

## 配置

当前默认配置（2026-05-31 Captain选定）：
- **TTS引擎**: mimo-v2.5-tts
- **默认音色**: Milo（中英双语男声）
- **音频格式**: WAV → OGG OPUS
- **发送方式**: message tool, asVoice=true

## 注意事项

1. MIMO TTS API通过chat/completions端点调用，需要assistant角色消息
2. 音频格式必须为wav/mp3/pcm/pcm16（MIMO不支持ogg_opus直接输出）
3. 飞书语音消息必须是OGG OPUS格式，需要ffmpeg转换
4. 长语音（1分钟+）转录文字多，会占更多上下文，建议分段发
