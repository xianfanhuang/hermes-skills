# ChanlunAgent - 缠论交易助手

飞书 @Bot 交互的缠论交易系统。支持持仓查询、缠论分析、信号监控、自动反思。

## 指令列表

| 指令 | 功能 | 示例 |
|------|------|------|
| `持仓` | 查询当前持仓 | `持仓` |
| `分析 [品种]` | 缠论多级别分析 | `分析 CRCL` |
| `信号` | 查看最近信号 | `信号` |
| `平仓 [品种]` | 平仓操作 | `平仓 CRCL` |
| `反思` | 生成最近交易反思 | `反思` |
| `日报` | 生成每日交易报告 | `日报` |
| `状态` | 系统状态检查 | `状态` |
| `帮助` | 显示帮助 | `帮助` |

## 使用方式

在飞书中 @Bot 并发送指令即可：
- `@Bot 分析 CRCL` — 获取 CRCL 缠论分析
- `@Bot 持仓` — 查看当前持仓
- `@Bot 信号` — 查看最近交易信号

## 系统架构

```
用户 @Bot → OpenClaw → ChanlunAgent Skill → czsc 分析 → 风控检查 → 信号生成
                                                    ↓
                                            反思引擎 → RGB知识库更新
```

## 依赖

- czsc v0.10.12
- Tiger Broker SDK
- Finnhub API
- OpenClaw 飞书集成

## 文件位置

- 主程序: `/workspace/projects/workspace/chanlun-agent/ChanlunAgent.py`
- czsc 扩展层: `/workspace/projects/workspace/chanlun-agent/data/czsc_extension.py`
- 风控引擎: `/workspace/projects/workspace/chanlun-agent/risk_engine.py`
- 反思引擎: `/workspace/projects/workspace/chanlun-agent/reflection_engine.py`
- RGB更新: `/workspace/projects/workspace/chanlun-agent/rgb_updater.py`
- 回测引擎: `/workspace/projects/workspace/chanlun-agent/backtest_engine.py`
