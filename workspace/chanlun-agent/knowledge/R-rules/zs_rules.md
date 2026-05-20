# 中枢识别精确规则 - czsc v0.10.12 API 映射

## 基本定义

**中枢 (ZS)**：至少三笔重叠区间形成的盘整区域。

## czsc v0.10.12 API

| 操作 | API | 返回类型 |
|------|-----|----------|
| 中枢列表 | `ka.zs_list` | `List[ZS]` |
| 最后一个中枢 | `ka.zs_list[-1]` | `ZS` |

## 中枢构成规则

### 连续三笔重叠
- 取连续三笔的重叠区间
- ZG = min(三笔的高点) — 中枢上沿
- ZD = max(三笔的低点) — 中枢下沿
- GG = max(三笔的高点) — 中枢最高点
- DD = min(三笔的低点) — 中枢最低点

### 中枢成立条件
- ZG > ZD（上沿必须高于下沿）
- 至少包含三笔

## 中枢扩展

### 中枢扩展条件
- 后续笔的高低点与中枢有重叠
- 扩展不改变 ZG/ZD，只扩展中枢区间

### 中枢升级
- 中枢扩展超过9笔 → 可能形成更大级别中枢

## ZS 对象属性

```python
class ZS:
    index: int          # 中枢序号
    zg: float           # 中枢上沿
    zd: float           # 中枢下沿
    gg: float           # 最高点
    dd: float           # 最低点
    direction: str      # 中枢方向
    bis: List[Bi]       # 包含的笔列表
```

## 使用示例

```python
from czsc import CZSC

ka = CZSC(bars)
for zs in ka.zs_list:
    print(f"中枢{zs.index}: [{zs.zd:.2f}, {zs.zg:.2f}]")
```
