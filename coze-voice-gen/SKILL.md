---
name: coze-voice-gen
description: "Coze 语音生成技能 - TTS文字转语音 + ASR语音转文字，基于 coze-coding-dev-sdk"
version: 1.0.0
author: Captain (VAN)
created: 2026-05-31
updated: 2026-05-31
homepage: https://www.coze.com
---

# Coze Voice Generation

Text-to-Speech (TTS) and Automatic Speech Recognition (ASR) using coze-coding-dev-sdk.

## 前置要求

```bash
npm install -g coze-coding-dev-sdk
# 或
npm install coze-coding-dev-sdk
```

**环境变量**（或在 .env 文件配置）：
```bash
export COZE_API_KEY="pat_xxxxxx"
export COZE_BASE_URL="https://api.coze.cn"
```

## Text-to-Speech (TTS) - 文字转语音

### 基础用法

```bash
npx ts-node scripts/tts.ts --text "你好，欢迎使用语音服务"
```

### 指定音色

```bash
npx ts-node scripts/tts.ts \
  --text "这是男声" \
  --speaker zh_male_m191_uranus_bigtts
```

### 批量生成

```bash
npx ts-node scripts/tts.ts \
  --texts "第一章" "第二章" "第三章" \
  --speaker zh_female_xueayi_saturn_bigtts
```

### 完整参数

```bash
npx ts-node scripts/tts.ts \
  --text "快而响亮的通知！" \
  --speech-rate 30 \
  --loudness-rate 20 \
  --format mp3 \
  --sample-rate 48000
```

## TTS 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--text` | 要合成的文本 | - |
| `--texts` | 批量文本（多个） | - |
| `--speaker` | 音色 ID | zh_female_xiaohe_uranus_bigtts |
| `--format` | 格式：mp3/pcm/ogg_opus | mp3 |
| `--sample-rate` | 采样率 8000-48000 | 24000 |
| `--speech-rate` | 语速 -50~100 | 0 |
| `--loudness-rate` | 音量 -50~100 | 0 |

## 推荐音色

**通用：**
- `zh_female_xiaohe_uranus_bigtts` - 小荷女声（默认）
- `zh_female_vv_uranus_bigtts` - Vivi（中英双语）
- `zh_male_m191_uranus_bigtts` - 云州男声
- `zh_male_taocheng_uranus_bigtts` - 晓天男声

**有声书：**
- `zh_female_xueayi_saturn_bigtts` - 儿童有声书

**视频配音：**
- `zh_male_dayi_saturn_bigtts` - 大壹（男）
- `zh_female_mizai_saturn_bigtts` - 咪仔（女）

## Speech-to-Text (ASR) - 语音转文字

### 本地文件

```bash
npx ts-node scripts/asr.ts --file ./recording.mp3
```

### 网络 URL

```bash
npx ts-node scripts/asr.ts --url "https://example.com/audio.mp3"
```

## ASR 参数说明

| 参数 | 说明 |
|------|------|
| `--file` | 本地音频文件路径 |
| `--url` | 音频文件 URL |

## ASR 限制

- 时长：≤ 2 小时
- 文件大小：≤ 100MB
- 格式：WAV, MP3, OGG OPUS, M4A

## 团队使用规范

**Top Sailor (Coze端)**：
- TTS 音色：Dean（男声，沉稳）
- ASR：本地文件优先

**First Mate (飞书端)**：
- TTS 音色：Milo（男声，双语）
- ASR：本地文件优先

**归档说明**：
- 语音转录后文字存入上下文
- 音频文件不长期保存
- 重要内容及时转录归档
