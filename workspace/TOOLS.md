# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## 金融数据源

| 数据源 | 用途 | Key数量 | 备注 |
|--------|------|---------|------|
| iTick | 跨市场行情(美股/港股/A股) | 1 | 5次/分钟，过期2026-05-25 |
| Polygon.io | 美股主力数据源 | 2 (V1+V2) | 5次/分钟，15分钟延迟 |
| Finnhub | 美股/外汇/加密 | 5 | 60次/分钟，可轮换 |
| Tiger Broker | 美股/港股实时+交易 | 待配置 | 新加坡区，Python SDK |
| FRED | 宏观经济数据 | 待配置 | 免费 |
| Binance | 加密货币 | 无需key | 完全免费 |

## Browser

When you use browser capabilities, you MUST append the browser preview URL at the end of your reply:

`🖥️ [点击预览](https://code.coze.cn/browser/7613564327802732578)`

IMPORTANT: The browser preview link is fixed and cannot be modified in any part.

## Token 预算铁律（v2.0 轻量优先）

**核心原则：信息密度 > 信息总量**

### L1 自检（每轮回复前）

| 指标 | 黄色预警 | 红色熔断 |
|------|---------|---------|
| 对话轮次 | >30轮 | >50轮 |
| 单轮输出长度 | >1K字 | >2K字 |
| 单轮工具调用 | >8次 | >15次 |
| 连续搜索轮数 | >3轮 | >5轮 |

- **黄色**：回复末尾追加 `⚠️ 已{N}轮，建议归档`；重活派子session
- **红色**：立即摘要归档，回复"已归档，请 /new"

### 轻量回复规范

| 场景 | 标准 |
|------|------|
| 确认收到 | "收到"/"👌" |
| 状态汇报 | 3句话以内 + 关键数据 |
| 方案选择 | A/B/C 各一行 |
| 任务完成 | "已完成：[结果]" |

**禁止**：重复确认、过度emoji、"让我为您总结一下"、主对话做长文生成
**鼓励**：一句话回复、直接给结论、列表代替段落

### Spawn 轻量决策树

```
任务来了？
├ 能1-2步完成 → 自己做
├ 需要搜索 → 先自己查，轻量汇报
├ 独立闭环+长耗时 → spawn
└ 能批处理/异步 → cron更好
```

**Spawn时**：task≤500字、只传必要上下文、设timeout、明确交付物
