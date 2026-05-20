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
