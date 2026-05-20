# 路由协议 (Routing Protocol)

> 说明智能路由的规则、降级机制和自定义配置方式

## 概览

FinanceFetcher 内置智能路由系统，自动选择最优数据源并在故障时切换到降级链路。

```
┌─────────────────────────────────────────────────────────────┐
│                      FinanceFetcher                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Router Layer                      │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────┐  │   │
│  │  │  iTick  │→ │Binance  │→ │Polygon  │→ │AKShare│  │   │
│  │  │ (优先)  │  │  (CC)   │  │  (备)   │  │ (备)  │  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └───────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 路由优先级算法

### 优先级定义

每个数据源有 1-5 的优先级（数字越小优先级越高）：

| 优先级 | 数值 | 说明 |
|--------|------|------|
| CRITICAL | 1 | 核心数据源，必须可用 |
| HIGH | 2 | 主要数据源 |
| MEDIUM | 3 | 备选数据源 |
| LOW | 4 | 补充数据源 |
| FALLBACK | 5 | 最终降级 |

### 默认优先级配置

```json
{
  "sources": {
    "itick": {
      "priority": 1,
      "markets": ["US", "HK", "SH", "SZ", "GB"],
      "status": "active"
    },
    "binance": {
      "priority": 1,
      "markets": ["CC"],
      "status": "active"
    },
    "polygon": {
      "priority": 2,
      "markets": ["US", "GB", "CC"],
      "status": "active"
    },
    "akshare": {
      "priority": 3,
      "markets": ["SH", "SZ"],
      "status": "active"
    },
    "fred": {
      "priority": 2,
      "markets": ["MACRO"],
      "status": "active"
    }
  }
}
```

### 路由选择流程

```
1. 解析请求（code + region）
2. 查找支持该市场的数据源列表
3. 按优先级排序
4. 尝试最高优先级源
   ├── 成功 → 返回数据
   └── 失败 → 记录失败次数，尝试下一优先级
5. 所有源失败 → 返回 None 或缓存数据
```

---

## 降级触发条件

### 自动降级阈值

| 条件 | 阈值 | 动作 |
|------|------|------|
| 连续失败 | 3次 | 降级该数据源 |
| 成功率 | < 50% | 降级该数据源 |
| 响应时间 | > 5000ms | 记录警告 |
| 超时 | 10s | 降级该数据源 |

### 降级状态

```python
class SourceStatus(Enum):
    ACTIVE = "active"      # 正常
    DEGRADED = "degraded"  # 降级（可用但慢）
    RETRYING = "retrying"  # 重试中
    RETIRED = "retired"    # 淘汰（不可用）
```

### 降级示例

```
请求: get_quote("AAPL", "US")

尝试顺序:
1. iTick (priority=1)
   └── 失败: 限流（RateLimitExceeded）
       ↓ 记录失败
2. Polygon (priority=2)
   └── 成功: 返回数据
       ↓ 记录成功

最终: 使用 Polygon 数据
```

---

## 自动恢复机制

### 恢复检测

| 条件 | 检测方式 | 恢复时间 |
|------|----------|----------|
| 降级后恢复 | 连续成功3次 | 10-30秒 |
| Key过期 | 检查 expires 字段 | 每日检查 |
| 限流解除 | 等待周期结束 | 最长60秒 |

### 恢复流程

```
降级状态 (DEGRADED)
    ↓ (每30秒检测一次)
检测: 发送轻量请求
    ├── 成功 → 连续成功计数器+1
    │         └── 达到3次 → 恢复 ACTIVE
    └── 失败 → 重置计数器，保持 DEGRADED
```

### 手动恢复

```python
# 强制恢复指定数据源
fetcher.force_recover("itick")

# 重置所有数据源状态
fetcher.reset_all_sources()

# 查看详细状态
status = fetcher.get_source_status()
print(status)
```

---

## 自定义路由配置

### 修改单个源优先级

```python
# 运行时配置
fetcher.set_priority("itick", priority=1)
fetcher.set_priority("polygon", priority=2)

# 或通过配置文件
# sources_config.json
{
  "sources": {
    "itick": {"priority": 1, "status": "active"},
    "polygon": {"priority": 1}  # 提升Polygon优先级
  }
}
```

### 禁用/启用数据源

```python
# 临时禁用
fetcher.disable_source("itick")

# 重新启用
fetcher.enable_source("itick")

# 查看启用的源
enabled = fetcher.get_enabled_sources()
```

### 自定义降级链路

```python
# 为特定市场指定降级链路
fetcher.set_fallback_chain("US", ["polygon", "akshare", "cache"])
fetcher.set_fallback_chain("CC", ["binance", "polygon", "cache"])

# 查看当前链路
chains = fetcher.get_fallback_chains()
```

### 负载均衡

当多个同优先级源可用时，使用轮询负载均衡：

```python
# 启用负载均衡
fetcher.enable_load_balancing("polygon")

# 配置权重
fetcher.set_weight("polygon_v1", weight=0.3)
fetcher.set_weight("polygon_v2", weight=0.7)

# 查看权重配置
weights = fetcher.get_weights()
```

---

## 缓存策略

### 缓存层级

| 层级 | 存储 | TTL | 用途 |
|------|------|-----|------|
| L1 | 内存 | 30-60秒 | 实时行情 |
| L2 | 磁盘 | 5-15分钟 | K线数据 |
| L3 | 归档 | 1-24小时 | 历史数据 |

### 缓存配置

```python
# 手动设置缓存
fetcher.set_cache_ttl("quote", 60)      # 行情60秒
fetcher.set_cache_ttl("kline_1m", 30)  # 1分钟K线30秒
fetcher.set_cache_ttl("kline_1d", 3600) # 日K线1小时

# 清除缓存
fetcher.clear_cache()
fetcher.clear_cache("itick")  # 清除特定源缓存

# 查看缓存统计
stats = fetcher.get_cache_stats()
```

---

## 健康检查

### 自动健康检查

```python
# 获取所有源健康状态
health = fetcher.health_check()
# {'itick': True, 'binance': True, 'polygon': False, 'akshare': True}

# 获取详细状态报告
report = fetcher.get_status_report()
print(report)
```

### 报告格式示例

```markdown
# 金融数据源状态报告

生成时间: 2026-04-21 10:30:00

## 数据源状态

| 数据源 | 状态 | 成功率 | 延迟 | 最后成功 |
|--------|------|--------|------|----------|
| iTick | ✅ ACTIVE | 98.5% | 120ms | 10:29:58 |
| Binance | ✅ ACTIVE | 99.9% | 45ms | 10:29:59 |
| Polygon | ⚠️ DEGRADED | 65.0% | 3200ms | 10:25:00 |
| AKShare | ✅ ACTIVE | 95.0% | 200ms | 10:29:55 |

## 告警

⚠️ Polygon.io 响应时间超过 3000ms，建议检查 API Key 或降级配置
```

### 定时健康检查

可通过 `health_daemon.py` 脚本定期检查：

```bash
# 添加到 crontab 每15分钟检查一次
*/15 * * * * python scripts/health_daemon.py

# 检查并输出报告
python scripts/health_daemon.py --report
```

---

## 限流管理

### 限流器配置

```python
# 查看当前限流状态
limiters = fetcher.get_rate_limiters()

# 调整限流参数
fetcher.set_rate_limit("itick", max_calls=5, period=60)  # 5次/分钟
fetcher.set_rate_limit("polygon", max_calls=5, period=60)

# 临时放宽限制（用于批量操作）
fetcher.temporarily_relax_limits("binance", factor=2, duration=300)
```

### 限流响应

```python
try:
    quote = fetcher.get_quote("AAPL", "US")
except RateLimitExceeded:
    print("请求过于频繁，等待后重试")
    time.sleep(60)
    quote = fetcher.get_quote("AAPL", "US")
```

---

## 错误处理

### 错误类型

| 错误类型 | 说明 | 处理方式 |
|----------|------|----------|
| `SourceUnavailable` | 数据源不可用 | 降级到备源 |
| `RateLimitExceeded` | 请求被限流 | 等待后重试 |
| `InvalidSymbol` | 标的代码无效 | 返回 None |
| `NetworkError` | 网络错误 | 自动重试3次 |
| `AuthenticationError` | 认证失败 | 检查 API Key |
| `KeyExpired` | Key已过期 | 提示更新 |

### 全局错误处理

```python
from finance_fetcher import FinanceFetcher, SourceUnavailable

fetcher = FinanceFetcher()

try:
    quote = fetcher.get_quote("AAPL", "US")
except SourceUnavailable as e:
    print(f"所有数据源不可用: {e}")
    # 使用缓存或返回错误
except RateLimitExceeded as e:
    print(f"限流: 等待 {e.retry_after} 秒")
except Exception as e:
    print(f"未知错误: {e}")
```
