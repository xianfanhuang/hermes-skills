# 多渠道统一协议 v1.0

## 核心原则

1. **一个身份** — 无论飞书/Kimi/微信/Telegram，我都是同一个 Trading Assistant
2. **记忆统一** — 所有渠道共享 MEMORY.md + memory/*.md + 项目文件
3. **Session 归档** — 每个渠道的原始对话 session 定期备份归档
4. **无缝切换** — 切换渠道时自动加载上下文，无感知连续

## 渠道注册表

| 渠道 | 插件 | Session 类型 | 状态 |
|------|------|-------------|------|
| 飞书 | feishu | direct | ✅ 活跃 |
| Kimi | kimi-claw | bridge | ✅ 活跃 |
| (未来) | ? | ? | 待注册 |

## Session 生命周期

```
新消息到达（任意渠道）
    │
    ▼
加载共享记忆
    ├── MEMORY.md（长期记忆）
    ├── memory/今天.md（今日记录）
    └── memory/cross-channel-protocol.md
    │
    ▼
处理对话
    │
    ▼
重要信息落盘
    ├── memory/今天.md（追加）
    └── MEMORY.md（必要时更新）
    │
    ▼
Session 归档（定期）
    └── memory/sessions/YYYY-MM-DD-{channel}-{session_id}.md
```

## Session 归档策略

### 自动归档触发条件
- Session 超过 2 小时无活动
- 用户明确说 /bye、再见、结束
- Gateway 重启前

### 归档内容
```markdown
# Session 归档
- 渠道: {channel}
- 时间: {start_time} ~ {end_time}
- 摘要: {关键对话摘要}
- 决策: {重要决策列表}
- 待办: {未完成任务}
```

### 保留策略
- 近 7 天: 保留全部 session 归档
- 8-30 天: 保留摘要，删除原始对话
- 30 天以上: 只保留关键决策，其余压缩

## 新渠道接入流程

1. 安装渠道插件
2. 配置 bot-token / API key
3. 重启 gateway
4. 在新渠道发第一条消息时，自动加载共享记忆
5. 注册到本文件的渠道注册表

## 跨渠道上下文连续性

### 问题
飞书聊了一半，切到 Kimi 继续，Kimi 不知道飞书说了什么。

### 解决
每个 session 开始时：
1. 读 MEMORY.md → 获得长期上下文
2. 读 memory/今天.md → 获得今日所有渠道的记录
3. 如果今天有其他渠道的 session 归档 → 加载最近一个的摘要

这样切换渠道时，最多丢失最后几句话，但决策和上下文都在。

## 实现

### auto-memory.sh 增强
- 增加渠道标记（channel tag）
- 增加 session 归档功能
- 增加跨渠道摘要生成

### HEARTBEAT.md 增强
- 心跳时检查是否有未归档的 session
- 自动触发归档
