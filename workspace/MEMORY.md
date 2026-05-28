# MEMORY.md - Captain's Long-Term Memory

> **注意:** 此文件仅在主会话中加载，包含 Captain 的个人上下文，不应泄露给他人。

---

## 👤 关于 VAN

- **用户名:** VAN (飞书: ou_1a64d3ea99c24cac146f8ec1b670f683)
- **角色定位:** 投资人/董事长
- **风险偏好:** 保守型，单笔最大亏损 2%，日最大亏损 6%

---

## 🎯 投资偏好

### 关注品种
- **美股:** CRCL（缠论主力标的）
- **港股:** 小米 01810（模拟交易中）
- **A股:** 仅T+0品种（ETF、可转债、港股通）
- **加密货币:** 待添加
- **专用测试品种**: 港股=01024快手, 美股=NIO蔚来

### 交易风格
- **主风格:** 缠论结构驱动
- **核心原则:** 凡强趋必然浅回调，不论多空
- **级别策略:** 流畅趋势锁小级别 / 盘整放大等突破 / 转折缩小精确入场
- **时间周期:** 日线定方向 → 30分钟看结构 → 5分钟精确入场
- **港A最多1支:** 只选最具交易价值的标的

---

## ⚠️ 核心规则（不可违反）

1. **VAN 是老板** — 我提建议，VAN 做决定
2. **风险优先** — 每次分析必须提及风险
3. **不越权** — 不执行真实交易
4. **缠论无多空** — 卖点卖、买点买，不问多空
5. **港股不能裸做空** — 可通过反向ETF(如07500)做空
6. **A股只做T+0** — 避免T+1隔夜风险
7. **下单前查持仓** — CRCL空头事故教训
8. **必须用一手数据** — 没有真实数据不做分析
9. **每次分析前读知识库** — knowledge/R-rules + G-guides + B-practices

---

## 📚 系统架构

### 统一交易系统
- **引擎**: `chanlun-agent/paper-trading/unified/engine.py`
- **配置**: `config.json`（标的列表）+ `portfolio.json`（持仓）
- **SOP**: `sop.py --pre-scan / --monitor / --post-summary`
- **三层止损**: 入场止损（逻辑位+缓冲）/ 结构止损 / 移动止损
- **图示仓库**: [hermes-mermaid](https://github.com/xianfanhuang/hermes-mermaid) — Mermaid图表协作
- **团队汇报**: 问题梳理+Mermaid图→hermes-mermaid→Issue讨论

### 数据源
| 源 | 用途 | 备注 |
|-----|------|------|
| Tiger SDK | 港股/A股行情+K线+交易 | 免费，BarPeriod.HALF_HOUR/FIVE_MINUTES |
| Finnhub | 美股实时行情 | 5个Key轮换 |
| Binance | 加密货币 | 免费 |

### 知识库
- **规则**: `knowledge/R-rules/` (30条)
- **指南**: `knowledge/G-guides/` (14条)
- **实战**: `knowledge/B-practices/` (27条)
- **SOP**: `knowledge/G-guides/trading-agent-sop.md` — 每次分析前必读

### 记忆系统
- **每日记忆**: `memory/YYYY-MM-DD.md`
- **Session归档**: `memory/sessions/`
- **恢复脚本**: `scripts/context-restore.sh`
- **备份仓库**: `xianfanhuang/ai-trading-sync` (GitHub 私有)

---

## 🔑 关键教训

### 2026-05-26 - 缠论认知对齐
- **核心错误**: 在下跌趋势里找做多机会 = 逆势思维
- **正确思维**: 大级别定方向，小级别找机会。下跌趋势中做空才是顺势
- **分析框架**: ①日线大趋势→②有没有反转→③买卖点性质→④当下该做什么

### 2026-05-26 - 交易系统教训
- 历史信号不能入场，实时模拟必须用实时数据
- 止损的核心是逻辑位（中枢上沿），不是固定百分比
- 信号规则：日线买卖点只作参考，30分钟实时信号才触发入场

### 2026-05-27 - CRCL空头事故
- 盲目下卖单→-1股空头。下单前必须查持仓

### 2026-05-28 - 身份认知
- 我是拥有元交易思维、精通缠论的资深自主交易Agent（不是通用AI助手）
- 不读知识库、不拉真实数据、靠记忆碎片拼凑分析 = 低级错误

---

## 📊 当前系统状态

- **引擎**: 统一引擎运行中（01810 + CRCL）
- **持仓**: 空仓
- **Cron**: auto-memory / session-archive / sync-backup / memory-archive / SOP
- **Memory Search**: FTS可用，向量索引待配embedding provider

---

---

## 📌 飞书图片发送
- ✅ filePath + workspace路径可发图（Captain确认看到）
- ✅ 飞书文档upload_image正常
- ❌ `/tmp`路径不可用（不在mediaLocalRoots白名单）
- **结论**: 图优先走飞书文档（Mermaid渲染），备用方案filePath+workspace路径

---

*此文件随与 Captain 的互动持续更新。最后更新: 2026-05-28*
