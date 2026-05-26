# 笔划分精确规则 - czsc v0.10.12 API 映射

## 基本定义

**笔 (Bi)**：连接两个相邻分型的线段，是缠论最基本的分析单位。

## czsc v0.10.12 API

| 操作 | API | 返回类型 |
|------|-----|----------|
| 获取笔列表 | `ka.bi_list` | `List[Bi]` |
| 获取分型列表 | `ka.fx_list` | `List[Fx]` |
| 获取最后一笔 | `ka.bi_list[-1]` | `Bi` |

## 笔的划分规则

### 1. 顶分型 → 底分型 = 向下笔
- 顶分型中间K线高点 > 两侧K线高点
- 底分型中间K线低点 < 两侧K线低点
- 顶分型后必须有底分型

### 2. 底分型 → 顶分型 = 向上笔
- 底分型中间K线低点 < 两侧K线低点
- 顶分型中间K线高点 > 两侧K线高点
- 底分型后必须有顶分型

### 3. K线包含处理
- 上涨中：取高高（两根K线中取较高的高点和较高的低点）
- 下跌中：取低低（两根K线中取较低的高点和较低的低点）

## 分型过滤规则（李小军风格）

### 放量分型优先
- 分型中间K线成交量 > 前一根K线成交量 × 1.5
- 放量分型的可靠性更高

### 验证分型确认
- 底分型确认：分型后一根K线收盘价 > 底分型中间K线最高价
- 顶分型确认：分型后一根K线收盘价 < 顶分型中间K线最低价

### 低量过滤
- 成交量 < 20日均量的50% → 分型降级处理
- 低量分型不作为主要交易信号

## Bi 对象属性

```python
class Bi:
    index: int          # 笔序号
    fx: Fx              # 起始分型
    bi_direction: str   # 笔方向: "up" / "down"
    high: float         # 笔最高点
    low: float          # 笔最低点
    start_dt: datetime  # 开始时间
    end_dt: datetime    # 结束时间
    bars: int           # 包含K线数量
```

## 使用示例

```python
from czsc import CZSC

ka = CZSC(bars)
for bi in ka.bi_list:
    print(f"笔{bi.index}: {bi.bi_direction} [{bi.low:.2f}, {bi.high:.2f}]")
```
