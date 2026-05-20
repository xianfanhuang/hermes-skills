---
name: chanlun-agent
description: 缠论交易Agent - 提供缠论技术分析、信号检测、持仓管理、交易反思。当用户提到"缠论分析"、"分析某股票"、"持仓"、"信号"、"交易反思"、"日报"时激活此技能。
---

# ChanlunAgent Skill

缠论交易分析Agent，基于 czsc v0.10.12 引擎，提供完整的缠论分析和交易管理能力。

## 核心功能

| 指令 | 功能 | 示例 |
|------|------|------|
| 分析 | 缠论结构分析（笔/中枢/背驰） | `分析 CRCL` |
| 持仓 | 查询当前持仓 | `持仓` |
| 信号 | 查看最近信号 | `信号` |
| 平仓 | 平仓指定品种 | `平仓 CRCL` |
| 反思 | 生成交易反思 | `反思` |
| 日报 | 生成交易日报 | `日报` |
| 状态 | 系统运行状态 | `状态` |

## 使用方式

运行 ChanlunAgent：
```bash
cd /workspace/projects/workspace/chanlun-agent
python3 ChanlunAgent.py -c <指令> -a <参数>
```

### 示例

```bash
# 分析 CRCL
python3 ChanlunAgent.py -c 分析 -a CRCL

# 查询持仓
python3 ChanlunAgent.py -c 持仓

# 查看信号
python3 ChanlunAgent.py -c 信号

# 生成日报
python3 ChanlunAgent.py -c 日报

# 系统状态
python3 ChanlunAgent.py -c 状态
```

## 缠论分析输出格式

分析结果包含：
- **趋势**: up/down/neutral
- **笔数**: 已完成的笔数量
- **中枢数**: 已识别的中枢数量
- **中枢区间**: [ZD, ZG]
- **背驰**: 是否存在背驰信号

## 信号分级

| 级别 | 条件 | 建议 |
|------|------|------|
| L1 | 单级别背驰 | 观望 |
| L2 | 两级共振 | 准备 |
| L3 | 三级共振+分型确认 | 行动 |
| L4 | 三级共振+放量 | 重仓 |

## 注意事项

- 所有分析仅供参考，不构成投资建议
- 决策权在 Captain 手中
- czsc 版本固定 v0.10.12，不可升级
- 数据源：Tiger（历史K线）+ Finnhub（实时行情）
