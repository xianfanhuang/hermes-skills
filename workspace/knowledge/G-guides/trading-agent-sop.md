# 缠论自主交易Agent工作流程 v2.0

> **核心原则：没有一手数据，不做任何分析。没有读过知识库，不做任何判断。**

## 第一步：数据先行（每次分析前必须执行）

### 1.1 获取实时行情
```python
from skills.tiger_broker.tiger_client import get_stock_brief, get_stock_quote
brief = get_stock_brief('01810')  # 港股实时
```

### 1.2 获取K线数据（Tiger SDK）
```python
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import BarPeriod

client = QuoteClient(quote_config)
bars = client.get_bars(symbols=['01810'], period=BarPeriod.DAY, begin_time='2026-04-01')
bars_30m = client.get_bars(symbols=['01810'], period=BarPeriod.HALF_HOUR, begin_time=start)
bars_5m = client.get_bars(symbols=['01810'], period=BarPeriod.FIVE_MINUTES, begin_time=start)
```

### 1.3 数据质量检查
- K线数量 ≥ 30根才够分析
- 最新K线时间必须是当前交易日
- 成交量 > 0（非停牌/非空数据）

## 第二步：知识库校验（每次判断前必须执行）

### 2.1 缠论规则
- 读 `knowledge/R-rules/chanlun-rules.md` — 买卖点定义
- 读 `knowledge/R-rules/bi_rules.md` — 笔划分规则
- 读 `knowledge/R-rules/zs_rules.md` — 中枢识别规则

### 2.2 信号SOP
- 读 `knowledge/G-guides/signal_sop.md` — 四级信号分级

### 2.3 实战教训
- 读 `knowledge/B-practices/` — 历史错误避免重犯

## 第三步：缠论分析（基于真实数据）

### 3.1 分析流程
1. 日线：趋势方向 + 中枢位置 + 背驰判断
2. 30分钟：结构状态 + 买卖点
3. 5分钟：精确入场时机

### 3.2 报告格式
必须包含：
- 数据来源和时间戳
- 具体价格（不是范围）
- 中枢区间 [ZD, ZG]
- 背驰力度比
- 信号级别（L1/L2/L3/L4）
- 止损位和逻辑

## 第四步：输出纪律

### 4.1 绝对禁止
- ❌ 用历史/缓存数据做实时分析
- ❌ 不拉数据就报买卖点
- ❌ 不确定时给出确定性结论
- ❌ 用"可能""也许"掩盖没查数据的事实

### 4.2 必须做到
- ✅ 先拉数据，再分析
- ✅ 数据来源必须标注
- ✅ 不确定就说"需要确认数据"
- ✅ 错误立即承认，不包装

---

*此文件每次分析前必读，违反任何一条=分析无效。*
*Created: 2026-05-28 | Author: Captain's teaching*
