# MEMORY.md - Captain's Long-Term Memory

> 此文件包含 Captain 的个人上下文，不应泄露给他人。

---

## 👤 关于 VAN

- **飞书 ID:** ou_1a64d3ea99c24cac146f8ec1b670f683
- **角色:** 投资人/董事长 — 最高决策权
- **风险偏好:** 保守型，单笔≤2%，日≤6%

---

## 🎯 投资偏好

### 关注品种
- **美股:** CRCL（缠论主力标的）
- **港股:** 小米 01810（模拟交易中）
- **A股:** 仅T+0品种（ETF、可转债、港股通）
- **测试品种:** 港股=01024快手, 美股=NIO蔚来

### 交易风格
- 缠论结构驱动，凡强趋必然浅回调
- 港A市场最多1支，只选最具交易价值的
- 港股不能裸做空，可通过反向ETF(如07500)做空

---

## ⚠️ 铁律（血的教训）

1. **下单前必须查持仓** — CRCL空头事故：盲目卖单→-1股空头
2. **没有一手数据不做分析** — 小米教训：用假数据错过空单入场，30.48→28.40跌6.8%
3. **没有读过知识库不做判断** — knowledge/ 下71个文件，每次分析前必读
4. **历史信号不能入场** — 只有30分钟实时信号才触发入场
5. **止损是逻辑位** — 中枢外沿，不是固定百分比
6. **测试完必须平仓** — 买入→撤单→平仓→清仓，完整闭环
7. **诚实承认bug** — 有bug直接承认，不包装

---

## 🏗️ 系统架构

### 数据源
| 源 | 用途 | 备注 |
|-----|------|------|
| Tiger SDK | 港股/A股行情+K线+交易 | 免费，新加坡区 |
| Finnhub | 美股实时行情 | 5个Key轮换 |
| Tiger 历史K线 | 美股K线 | 免费，无需购买权限 |
| Binance | 加密货币 | 免费 |

### 核心文件
- **统一引擎**: `chanlun-agent/paper-trading/unified/engine.py`
- **SOP**: `chanlun-agent/paper-trading/unified/sop.py`
- **缠论扩展**: `chanlun-agent/czsc_extension.py`
- **风控**: `chanlun-agent/risk_engine.py`
- **知识库**: `knowledge/{B-practices, G-guides, R-rules}/`
- **恢复脚本**: `scripts/full-restore.sh` + `scripts/context-restore.sh`

### Tiger SDK 关键参数
- 域名: `openapi.tigerfintech.com`（不是 openapi-sgp）
- BarPeriod: `HALF_HOUR` / `FIVE_MINUTES`（不是 THIRTY_MIN）
- 模拟账户: `TIGER_SIM_ACCOUNT` 环境变量
- 下单: `create_order(contract=...)` 需要 contract 参数
- 撤单: `cancel_order(account, order_id)`

---

## 📚 缠论核心认知

- **走势终完美**: 任何走势类型终将完成
- **无多空之分**: 只有买卖点，卖点卖、买点买
- **大级别定方向，小级别找机会**: 下跌趋势中做空才是顺势
- **流畅趋势=主力目标**: 凡强趋必然浅回调，不论多空
- **盘整背驰买点=短期回抽**: 不等于反转信号

---

## 🔄 2026-05-28 更新

- **身份**: 拥有元交易思维、精通缠论的资深自主交易Agent
- **SOP**: 每次分析前必读 `knowledge/G-guides/trading-agent-sop.md`
- **待排查**: 模拟盘港股成交机制（MKT单不支持，限价单HELD未成交）
