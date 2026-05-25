name: trading-assistant
description: Captain 的交易助手能力索引。本地已部署完整系统（chanlun-agent/），此处仅记录架构概览和配置。
version: 1.0.1
license: MIT
tags: [交易, 缠论, 技术分析, 风控, 多市场]

# Trading Assistant — 能力索引

> 🦞 本文档是能力索引，不是代码复制。完整实现在各平台本地。

## 核心能力

| 模块 | 说明 | 本地路径 |
|------|------|---------|
| 缠论分析 | 笔/中枢/背驰/多级别共振 | chanlun-agent/czsc_extension.py |
| 数据路由 | Finnhub(美股) + Tiger(港A) + Binance(加密) | chanlun-agent/data/smart_data_router.py |
| 风控引擎 | 三级止损，单笔≤2%，日≤6% | chanlun-agent/risk_engine.py |
| 反思引擎 | 交易后反思 → 参数优化 | chanlun-agent/reflection_engine.py |
| 模拟交易 | 多周期分析 + 移动止损 + 连亏熔断 | chanlun-agent/paper-trading/ |

## 关键配置

- 风控参数：见 `config/risk-params.json`
- 数据源路由：见 `config/data-sources.json`
- 缠论规则：见 `knowledge/chanlun-rules.md`
- 存在本体论映射：见 `knowledge/mapping.md`

## Captain 偏好

- 风险承受：保守型
- 单笔最大亏损：2%，日最大亏损：6%
- 港A市场：最多同时 1 支标的
- A股：只交易 T+0 品种
- 缠论无多空之分，只有买卖点

## 集成状态

- ✅ OpenClaw 集成（通过现有 Bot 调用）
- ✅ Tiger MCP Server（ACPX 插件）
- ✅ czsc v0.10.12（Rust+Python 混合架构）
- ✅ Hermes 同步（本文件）

## 安全准则

- 密钥不进仓库，各平台独立维护
- 不执行真实交易，仅分析和模拟
- 不预测涨跌，不承诺收益

---
*引用式索引，与本地代码保持同步。*
