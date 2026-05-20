#!/usr/bin/env python3
"""
Finance Fetcher v2.0 - 金融数据感知基础设施
支持: Polygon/iTick/AKShare/Binance/FRED

核心功能：
- 跨市场实时行情（美股/港股/A股/外汇/期货/加密货币）
- 技术指标数据（K线）
- 市场异常信号检测
- 宏观经济数据监控
- 智能路由：基于源健康度/延迟/可用性自动选最优源
- 按需激活：只在需要时才连接数据源
- 源生命周期管理：注册→活跃→降级→退休

Author: AI Agent
Version: 2.0.0
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import urllib.request
import urllib.error
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FinanceFetcher")

# ============ Enums and Config ============
class Market(Enum):
    """市场类型枚举"""
    US = "US"       # 美股
    HK = "HK"       # 港股
    SH = "SH"       # 上海（A股）
    SZ = "SZ"       # 深圳（A股）
    GB = "GB"       # 外汇
    CC = "CC"       # 加密货币（iTick不支持，Binance专用）
    FUTURES = "FUTURES"  # 期货
    MACRO = "MACRO"  # 宏观经济


class ProviderState(Enum):
    """数据源状态"""
    UNINITIALIZED = "uninitialized"  # 未初始化（按需激活）
    ACTIVE = "active"                # 活跃
    DEGRADED = "degraded"            # 降级（失败率高/延迟大）
    RETIRED = "retired"              # 退休（持续不可用）


@dataclass
class ProviderProfile:
    """数据源画像"""
    name: str
    markets: List[str]               # 支持的市场
    capabilities: List[str]          # 能力（quote, kline, forex, crypto, macro）
    state: ProviderState
    priority: int                    # 优先级（1=最高）
    health_score: float = 1.0       # 0-1，综合健康分
    latency_ms: float = 0.0         # 最近平均延迟
    success_rate: float = 1.0       # 最近成功率
    last_check: Optional[datetime] = None   # 上次健康检查
    consecutive_failures: int = 0    # 连续失败次数
    total_requests: int = 0          # 总请求数
    failed_requests: int = 0        # 失败请求数
    fetcher: Optional[Any] = None   # 实际fetcher实例（按需创建）
    fetcher_class: Optional[Any] = None  # fetcher类
    init_params: Optional[Dict] = None  # 初始化参数
    
    def __post_init__(self):
        # 确保 state 是 ProviderState 枚举
        if isinstance(self.state, str):
            self.state = ProviderState(self.state)
    
    def update_health_on_success(self, latency_ms: float):
        """成功调用后更新健康指标"""
        self.total_requests += 1
        self.success_rate = (self.total_requests - self.failed_requests) / self.total_requests
        # 指数移动平均更新延迟
        if self.latency_ms > 0:
            self.latency_ms = 0.7 * self.latency_ms + 0.3 * latency_ms
        else:
            self.latency_ms = latency_ms
        self.consecutive_failures = 0
        self._recalculate_health_score()
    
    def update_health_on_failure(self, error: str):
        """失败调用后更新健康指标"""
        self.total_requests += 1
        self.failed_requests += 1
        self.success_rate = (self.total_requests - self.failed_requests) / self.total_requests
        self.consecutive_failures += 1
        self._recalculate_health_score()
    
    def _recalculate_health_score(self):
        """重新计算健康分"""
        # 综合考虑：成功率、延迟、连续失败
        base_score = self.success_rate * 0.5
        
        # 延迟惩罚（假设 500ms 为基准）
        latency_factor = max(0, 1 - (self.latency_ms / 2000))
        latency_score = latency_factor * 0.3
        
        # 连续失败惩罚
        if self.consecutive_failures >= 3:
            fail_penalty = 0.2
        else:
            fail_penalty = 0
        
        self.health_score = max(0, base_score + latency_score - fail_penalty)
        self.last_check = datetime.now()


class SmartRouter:
    """
    智能路由器
    
    功能：
    - 按需激活数据源（lazy init）
    - 智能路由选择最优源
    - 健康度跟踪与自动降级
    - Fallback 链管理
    """
    
    # 降级/退休阈值
    CONSECUTIVE_FAILURES_DEGRADE = 3
    RETIRED_GRACE_PERIOD_HOURS = 24
    RETRY_RETIRED_AFTER_DAYS = 7
    
    def __init__(self, config: Dict, secrets: Dict):
        self.providers: Dict[str, ProviderProfile] = {}
        self.config = config
        self.secrets = secrets
        self._register_providers()
    
    def _register_providers(self):
        """注册所有数据源（但不初始化fetcher）"""
        # Polygon.io
        polygon_v1_key = self.secrets.get('POLYGON_V1_KEY')
        polygon_v2_key = self.secrets.get('POLYGON_V2_KEY')
        if polygon_v1_key or polygon_v2_key:
            init_params = {'api_key_v1': polygon_v1_key, 'api_key_v2': polygon_v2_key}
            self.providers['polygon'] = ProviderProfile(
                name='polygon',
                markets=['US', 'GB', 'CC'],
                capabilities=['quote', 'kline', 'forex', 'crypto'],
                state=ProviderState.UNINITIALIZED,
                priority=2,  # 免费版无实时报价，降为备用（K线历史数据优先）
                fetcher_class=PolygonFetcher,
                init_params=init_params
            )
        
        # iTick（实时行情首选）
        itick_key = self.secrets.get('ITICK_API_KEY')
        if itick_key:
            # iTick 限流器
            rate_limiter = RateLimiter(max_calls=5, period_seconds=60)
            init_params = {'api_key': itick_key, 'rate_limiter': rate_limiter}
            self.providers['itick'] = ProviderProfile(
                name='itick',
                markets=['US', 'HK', 'SH', 'SZ', 'GB'],
                capabilities=['quote', 'kline', 'forex'],
                state=ProviderState.UNINITIALIZED,
                priority=1,  # 实时行情首选（Polygon免费版无实时报价）
                fetcher_class=ITickFetcher,
                init_params=init_params
            )
        
        # Binance
        self.providers['binance'] = ProviderProfile(
            name='binance',
            markets=['CC'],
            capabilities=['quote', 'kline'],
            state=ProviderState.UNINITIALIZED,
            priority=1,
            fetcher_class=BinanceFetcher,
            init_params={}
        )
        
        # AKShare
        self.providers['akshare'] = ProviderProfile(
            name='akshare',
            markets=['SH', 'SZ'],
            capabilities=['quote', 'kline', 'macro'],
            state=ProviderState.UNINITIALIZED,
            priority=1,
            fetcher_class=AKShareFetcher,
            init_params={}
        )
        
        # FRED
        fred_key = self.secrets.get('FRED_API_KEY')
        init_params = {'api_key': fred_key} if fred_key else {}
        self.providers['fred'] = ProviderProfile(
            name='fred',
            markets=['MACRO'],
            capabilities=['macro'],
            state=ProviderState.UNINITIALIZED,
            priority=2,
            fetcher_class=FREDFetcher,
            init_params=init_params
        )
        
        logger.info(f"Registered {len(self.providers)} providers")
    
    def _activate_provider(self, name: str) -> bool:
        """按需激活数据源（创建fetcher实例）"""
        if name not in self.providers:
            logger.warning(f"Unknown provider: {name}")
            return False
        
        profile = self.providers[name]
        
        # 只有 UNINITIALIZED 状态才激活
        if profile.state != ProviderState.UNINITIALIZED:
            return profile.state == ProviderState.ACTIVE
        
        # 检查是否需要密钥
        if profile.fetcher_class in [PolygonFetcher, ITickFetcher, FREDFetcher]:
            if not profile.init_params.get('api_key') and not profile.init_params.get('api_key_v1'):
                logger.warning(f"Provider {name} requires API key but none configured")
                return False
        
        try:
            # 创建 fetcher 实例
            profile.fetcher = profile.fetcher_class(**profile.init_params)
            profile.state = ProviderState.ACTIVE
            profile.last_check = datetime.now()
            logger.info(f"Activated provider: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to activate provider {name}: {e}")
            return False
    
    def get_fetcher(self, name: str) -> Optional[Any]:
        """获取 fetcher 实例（自动激活）"""
        if name not in self.providers:
            return None
        
        profile = self.providers[name]
        
        # 未初始化时尝试激活
        if profile.state == ProviderState.UNINITIALIZED:
            if not self._activate_provider(name):
                return None
        
        # 退休状态尝试重新激活
        if profile.state == ProviderState.RETIRED:
            if profile.last_check:
                days_since_retired = (datetime.now() - profile.last_check).days
                if days_since_retired >= self.RETRY_RETIRED_AFTER_DAYS:
                    logger.info(f"Retrying retired provider: {name}")
                    if self._activate_provider(name):
                        profile.state = ProviderState.ACTIVE
        
        return profile.fetcher
    
    def route(self, market: str, capability: str = "quote") -> Optional[str]:
        """智能路由：选择最优数据源"""
        candidates = self._get_candidates(market, capability)
        if not candidates:
            return None
        
        # 按优先级、健康分、延迟排序
        candidates.sort(key=lambda p: (
            p.priority,
            -p.health_score,
            p.latency_ms if p.latency_ms > 0 else float('inf')
        ))
        
        # 返回最优候选
        return candidates[0].name
    
    def _get_candidates(self, market: str, capability: str) -> List[ProviderProfile]:
        """获取符合条件的候选源"""
        candidates = []
        
        for name, profile in self.providers.items():
            # 检查市场支持
            if market not in profile.markets:
                continue
            
            # 检查能力支持
            if capability not in profile.capabilities:
                continue
            
            # 排除退休的源
            if profile.state == ProviderState.RETIRED:
                # 检查是否应该重新尝试
                if profile.last_check:
                    days_since = (datetime.now() - profile.last_check).days
                    if days_since < self.RETRY_RETIRED_AFTER_DAYS:
                        continue
                # 尝试重新激活
                if self._activate_provider(name):
                    profile.state = ProviderState.ACTIVE
                else:
                    continue
            
            # 降级源仍可用但不优先
            candidates.append(profile)
        
        return candidates
    
    def route_with_fallback(self, market: str, capability: str = "quote") -> List[str]:
        """返回优先级排序的源列表（含fallback链）"""
        candidates = self._get_candidates(market, capability)
        
        # 排序：DEGRADED 排在最后
        def sort_key(p):
            if p.state == ProviderState.DEGRADED:
                # 降级源仍可用，但优先级最低
                return (p.priority + 10, -p.health_score, p.latency_ms if p.latency_ms > 0 else float('inf'))
            return (p.priority, -p.health_score, p.latency_ms if p.latency_ms > 0 else float('inf'))
        
        candidates.sort(key=sort_key)
        return [p.name for p in candidates]
    
    def report_success(self, provider_name: str, latency_ms: float):
        """报告成功调用，更新健康指标"""
        if provider_name in self.providers:
            self.providers[provider_name].update_health_on_success(latency_ms)
            self.update_provider_state(provider_name)
    
    def report_failure(self, provider_name: str, error: str):
        """报告失败调用，更新健康指标，可能触发降级"""
        if provider_name in self.providers:
            self.providers[provider_name].update_health_on_failure(error)
            self.update_provider_state(provider_name)
    
    def update_provider_state(self, name: str):
        """根据健康指标自动调整源状态"""
        if name not in self.providers:
            return
        
        profile = self.providers[name]
        
        # 连续失败3次 → DEGRADED
        if profile.state == ProviderState.ACTIVE:
            if profile.consecutive_failures >= self.CONSECUTIVE_FAILURES_DEGRADE:
                profile.state = ProviderState.DEGRADED
                logger.warning(f"Provider {name} degraded due to consecutive failures")
        
        # DEGRADED + 成功率<50% → RETIRED
        elif profile.state == ProviderState.DEGRADED:
            if profile.success_rate < 0.5:
                profile.state = ProviderState.RETIRED
                logger.warning(f"Provider {name} retired due to low success rate: {profile.success_rate:.2%}")
        
        # ACTIVE + 成功率恢复 → 保持 ACTIVE
        elif profile.state == ProviderState.DEGRADED:
            if profile.success_rate >= 0.8 and profile.consecutive_failures == 0:
                profile.state = ProviderState.ACTIVE
                logger.info(f"Provider {name} recovered to active")
    
    def health_check(self, provider_name: str = None) -> Dict:
        """
        健康巡检
        
        Args:
            provider_name: 指定检查某个源，为None则检查所有已激活的源
            
        Returns:
            Dict: 健康报告 {provider_name: status_dict}
        """
        result = {}
        
        providers_to_check = []
        if provider_name:
            if provider_name in self.providers:
                providers_to_check = [provider_name]
        else:
            providers_to_check = [n for n, p in self.providers.items() 
                                 if p.state in [ProviderState.ACTIVE, ProviderState.DEGRADED]]
        
        for name in providers_to_check:
            profile = self.providers[name]
            fetcher = self.get_fetcher(name)
            
            status = {
                'state': profile.state.value,
                'health_score': profile.health_score,
                'success_rate': profile.success_rate,
                'latency_ms': profile.latency_ms,
                'total_requests': profile.total_requests,
                'failed_requests': profile.failed_requests,
                'consecutive_failures': profile.consecutive_failures,
                'last_check': profile.last_check.isoformat() if profile.last_check else None,
                'available': fetcher is not None
            }
            
            # 尝试实际调用检测
            if fetcher:
                try:
                    if name == 'polygon':
                        test_result = fetcher.get_quote("AAPL")
                    elif name == 'itick':
                        test_result = fetcher.get_quote("AAPL", "US")
                    elif name == 'binance':
                        test_result = fetcher.get_ticker("BTCUSDT")
                    elif name == 'akshare':
                        test_result = fetcher.available
                    elif name == 'fred':
                        test_result = fetcher.is_configured()
                    status['test_success'] = test_result is not None if test_result is not True else True
                except Exception as e:
                    status['test_success'] = False
                    status['test_error'] = str(e)
            
            result[name] = status
        
        return result
    
    def get_provider_status_report(self) -> str:
        """生成数据源状态报告（Markdown）"""
        lines = [
            "# 金融数据源状态报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**数据源总数**: {len(self.providers)}",
            ""
        ]
        
        # 统计
        state_counts = {}
        for profile in self.providers.values():
            state = profile.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        lines.extend([
            "## 概览",
            "",
            "| 状态 | 数量 |",
            "|------|------|"
        ])
        for state, count in state_counts.items():
            lines.append(f"| {state} | {count} |")
        
        lines.extend(["", "---", ""])
        
        # 详细状态表
        lines.extend([
            "## 数据源详情",
            "",
            "| 数据源 | 状态 | 健康分 | 成功率 | 延迟(ms) | 市场 |",
            "|------|------|--------|--------|----------|------|"
        ])
        
        for name, profile in sorted(self.providers.items()):
            lines.append(
                f"| {name} | {profile.state.value} | "
                f"{profile.health_score:.2f} | {profile.success_rate:.1%} | "
                f"{profile.latency_ms:.0f} | {','.join(profile.markets)} |"
            )
        
        lines.extend(["", "---", ""])
        
        # 能力矩阵
        lines.extend([
            "## 能力矩阵",
            "",
            "| 数据源 | quote | kline | forex | crypto | macro |",
            "|------|-------|-------|-------|--------|-------|"
        ])
        
        capabilities = ['quote', 'kline', 'forex', 'crypto', 'macro']
        for name, profile in sorted(self.providers.items()):
            cells = [name]
            for cap in capabilities:
                if cap in profile.capabilities:
                    cells.append('✅')
                else:
                    cells.append('-')
            lines.append('| ' + ' | '.join(cells) + ' |')
        
        return '\n'.join(lines)
    
    def deactivate_provider(self, name: str):
        """停用某个数据源（释放资源）"""
        if name not in self.providers:
            return
        
        profile = self.providers[name]
        profile.fetcher = None
        profile.state = ProviderState.UNINITIALIZED
        logger.info(f"Deactivated provider: {name}")
    
    def get_all_providers(self) -> Dict[str, ProviderProfile]:
        """获取所有provider信息"""
        return self.providers.copy()


class KlineInterval(Enum):
    """K线周期枚举"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    D1 = "1d"
    W1 = "1w"
    MN = "1M"

# iTick映射（不能放在Enum内，否则被当作枚举成员）
ITICK_KLINE_MAP = {
    "1m": "1", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "1d": "101", "1w": "102", "1M": "103"
}

class FinanceSignalType(Enum):
    """金融信号类型枚举（扩展现有SignalType）"""
    MARKET_SIGNAL = "market_signal"        # 已有：市场信号
    FINANCIAL_ANOMALY = "financial_anomaly"  # 新增：金融异常
    PRICE_BREAKOUT = "price_breakout"     # 价格突破
    VOLUME_SPIKE = "volume_spike"         # 成交量突增
    MACRO_EVENT = "macro_event"           # 宏观事件

@dataclass
class Quote:
    """标准行情数据"""
    symbol: str           # 股票代码
    market: str           # 市场（US/HK/SH/SZ/GB/CC）
    name: str             # 名称
    price: float          # 最新价
    change: float          # 涨跌额
    change_pct: float     # 涨跌幅（%）
    volume: int           # 成交量
    amount: float         # 成交额
    high: float           # 最高
    low: float            # 最低
    open: float           # 开盘
    prev_close: float     # 昨收
    timestamp: str        # 数据时间
    source: str           # 数据来源
    
    # 扩展字段
    bid: Optional[float] = None   # 买价
    ask: Optional[float] = None   # 卖价
    turnover_rate: Optional[float] = None  # 换手率（A股）
    market_cap: Optional[float] = None  # 市值
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        trend = "📈" if self.change_pct > 0 else "📉" if self.change_pct < 0 else "➡️"
        return f"| {trend} {self.symbol} | {self.name} | ${self.price:.2f} | {self.change_pct:+.2f}% | {self.volume:,} |"

@dataclass
class KlineBar:
    """K线数据"""
    symbol: str
    market: str
    timestamp: str        # K线时间
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: str         # 周期
    source: str
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class FinancePerceptionSignal:
    """
    金融感知信号 - 继承自PerceptionSignal概念
    
    用于标记市场异常、交易机会等金融相关事件
    """
    signal_type: str              # FinanceSignalType.value
    source: str                   # 数据来源
    title: str                    # 信号标题
    symbol: str                   # 关联标的
    severity: str = "info"        # critical/high/medium/low/info
    summary: Optional[str] = None # 摘要
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 行情数据
    quote_data: Optional[Quote] = None
    
    def to_dict(self) -> dict:
        return {
            'signal_type': self.signal_type,
            'source': self.source,
            'title': self.title,
            'symbol': self.symbol,
            'severity': self.severity,
            'summary': self.summary,
            'timestamp': self.timestamp,
            'metadata': self.metadata,
            'quote_data': self.quote_data.to_dict() if self.quote_data else None
        }
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "⚡",
            "low": "📝",
            "info": "ℹ️"
        }.get(self.severity, "ℹ️")
        
        lines = [
            f"### {severity_emoji} {self.title}",
            "",
            f"| 属性 | 值 |",
            f"|------|-----|",
            f"| **信号类型** | {self.signal_type} |",
            f"| **标的** | {self.symbol} |",
            f"| **来源** | {self.source} |",
            f"| **严重程度** | {self.severity} |",
        ]
        if self.summary:
            lines.append(f"| **摘要** | {self.summary} |")
        if self.timestamp:
            lines.append(f"| **时间** | {self.timestamp} |")
        
        return "\n".join(lines)


# ============ Rate Limiter ============
class RateLimiter:
    """通用限流器"""
    
    def __init__(self, max_calls: int, period_seconds: float):
        """
        Args:
            max_calls: 最大调用次数
            period_seconds: 时间周期（秒）
        """
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls = []
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """尝试获取令牌，非阻塞"""
        with self._lock:
            now = time.time()
            # 清理过期记录
            self.calls = [t for t in self.calls if now - t < self.period]
            
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            return False
    
    def wait_if_needed(self):
        """等待直到可以执行"""
        while True:
            with self._lock:
                now = time.time()
                self.calls = [t for t in self.calls if now - t < self.period]
                
                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return
                
                # 计算等待时间
                oldest = min(self.calls)
                wait_time = self.period - (now - oldest) + 0.1
            
            logger.debug(f"Rate limited, waiting {wait_time:.2f}s...")
            time.sleep(wait_time)


# ============ Cache Manager ============
class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}  # (data, expiry_time)
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key in self._cache:
                data, expiry = self._cache[key]
                if time.time() < expiry:
                    return data
                else:
                    del self._cache[key]
        return None
    
    def set(self, key: str, data: Any, ttl_seconds: float):
        """设置缓存"""
        with self._lock:
            self._cache[key] = (data, time.time() + ttl_seconds)
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()


# ============ iTick Fetcher ============
class ITickFetcher:
    """
    iTick 金融数据API
    
    Base URL: https://api0.itick.org (注意：api-free.itick.org不可用)
    限制：
    - REST API: 5次/分钟
    - 每次K线最多500条
    - 免费版不含加密货币(CC)
    """
    
    BASE_URL = "https://api0.itick.org"
    
    def __init__(self, api_key: str, rate_limiter: RateLimiter):
        self.api_key = api_key
        self.rate_limiter = rate_limiter
        self.session_config = {
            'timeout': 10,
            'max_retries': 2
        }
        self.cache = CacheManager()
        
        # API Key过期检查
        self.key_expires = datetime(2026, 5, 25)
        self._check_key_expiry()
    
    def _check_key_expiry(self):
        """检查Key是否即将过期"""
        days_left = (self.key_expires - datetime.now()).days
        if days_left <= 14:
            logger.warning(f"⚠️ iTick API Key将在 {self.key_expires.date()} 过期，剩余 {days_left} 天")
        if days_left <= 0:
            logger.error("❌ iTick API Key已过期，请更新！")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """发送HTTP请求"""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}/{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; FinanceFetcher/1.0)',
            'Accept': 'application/json',
            'token': self.api_key
        }
        
        for attempt in range(self.session_config['max_retries']):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.session_config['timeout']) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get('code') == 0 or data.get('success'):
                        return data.get('data', data)
                    else:
                        logger.warning(f"iTick API error: {data.get('msg', 'Unknown error')}")
                        return None
            except Exception as e:
                logger.warning(f"iTick request failed (attempt {attempt + 1}): {e}")
                if attempt < self.session_config['max_retries'] - 1:
                    time.sleep(2)
        
        return None
    
    def get_quote(self, code: str, region: str) -> Optional[Quote]:
        """
        获取实时报价
        
        Args:
            code: 股票代码，如 "AAPL"
            region: 市场区域，如 "US", "HK", "SH", "SZ"
            
        Returns:
            Quote对象
        """
        # 检查缓存（实时行情缓存60秒）
        cache_key = f"itick_quote_{region}_{code}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request("stock/quote", {"region": region, "code": code})
        if not data:
            return None
        
        # 解析响应
        try:
            quote = Quote(
                symbol=code,
                market=region,
                name=data.get('name', data.get('n', code)),
                price=float(data.get('last', data.get('ld', 0))),
                change=float(data.get('change', data.get('ch', 0))),
                change_pct=float(data.get('chp', data.get('chp', 0))),
                volume=int(data.get('volume', data.get('v', 0))),
                amount=float(data.get('amount', data.get('a', 0))),
                high=float(data.get('high', data.get('h', 0))),
                low=float(data.get('low', data.get('l', 0))),
                open=float(data.get('open', data.get('o', 0))),
                prev_close=float(data.get('prevClose', data.get('pc', 0))),
                timestamp=data.get('timestamp', datetime.now().isoformat()),
                source="iTick"
            )
            
            self.cache.set(cache_key, quote, 60)
            return quote
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to parse iTick quote: {e}")
            return None
    
    def get_kline(self, code: str, region: str, k_type: str = "101", limit: int = 100) -> List[KlineBar]:
        """
        获取K线数据
        
        Args:
            code: 股票代码
            region: 市场区域
            k_type: K线类型 (1=1分钟, 5=5分钟, 15=15分钟, 30=30分钟, 60=1小时, 101=日线, 102=周线, 103=月线)
            limit: 返回数量
            
        Returns:
            List[KlineBar]
        """
        # 缓存日线24小时，其他60秒
        is_daily = k_type == "101"
        cache_ttl = 86400 if is_daily else 60
        cache_key = f"itick_kline_{region}_{code}_{k_type}_{limit}"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request("stock/kline", {
            "region": region,
            "code": code,
            "kType": k_type,
            "limit": min(limit, 500)  # 最多500条
        })
        
        if not data:
            return []
        
        bars = []
        try:
            items = data if isinstance(data, list) else data.get('data', [])
            for item in items:
                bar = KlineBar(
                    symbol=code,
                    market=region,
                    timestamp=item.get('t', item.get('timestamp', '')),
                    open=float(item.get('o', 0)),
                    high=float(item.get('h', 0)),
                    low=float(item.get('l', 0)),
                    close=float(item.get('c', item.get('ld', 0))),
                    volume=int(item.get('v', 0)),
                    interval=k_type,
                    source="iTick"
                )
                bars.append(bar)
            
            self.cache.set(cache_key, bars, cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to parse iTick kline: {e}")
        
        return bars
    
    def get_forex_quote(self, code: str) -> Optional[Quote]:
        """获取外汇报价"""
        data = self._make_request("forex/quote", {"region": "GB", "code": code})
        if not data:
            return None
        
        try:
            return Quote(
                symbol=code,
                market="GB",
                name=data.get('name', code),
                price=float(data.get('last', 0)),
                change=float(data.get('change', 0)),
                change_pct=float(data.get('chp', 0)),
                volume=0,
                amount=0,
                high=float(data.get('high', 0)),
                low=float(data.get('low', 0)),
                open=float(data.get('open', 0)),
                prev_close=float(data.get('prevClose', 0)),
                timestamp=data.get('timestamp', datetime.now().isoformat()),
                source="iTick"
            )
        except Exception as e:
            logger.warning(f"Failed to parse forex quote: {e}")
            return None


# ============ Binance Fetcher ============
class BinanceFetcher:
    """
    Binance 加密货币API
    
    REST API: https://api.binance.com
    限制：1200权重/分钟，按接口权重计算
    完全免费，无需API Key
    """
    
    BASE_URL = "https://api.binance.com"
    
    # 权重配置
    WEIGHT_CONFIG = {
        'ticker': 1,
        'klines': 5,
        'depth': 5,
        '24hr': 1
    }
    
    def __init__(self):
        self.rate_limiter = RateLimiter(1200, 60)  # 1200权重/分钟
        self.session_config = {'timeout': 10}
        self.cache = CacheManager()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, weight: int = 1) -> Optional[Dict]:
        """发送请求"""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; FinanceFetcher/1.0)',
            'Accept': 'application/json'
        }
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.session_config['timeout']) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            logger.warning(f"Binance request failed: {e}")
            return None
    
    def wait_if_needed(self):
        """等待直到可以执行"""
        while True:
            now = time.time()
            # 简化实现
            time.sleep(0.1)
            return
    
    def get_ticker(self, symbol: str) -> Optional[Quote]:
        """
        获取24小时ticker
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
        """
        cache_key = f"binance_ticker_{symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request("/api/v3/ticker/24hr", {"symbol": symbol.upper()})
        if not data:
            return None
        
        try:
            quote = Quote(
                symbol=symbol.upper(),
                market="CC",
                name=symbol.upper(),
                price=float(data.get('lastPrice', 0)),
                change=float(data.get('priceChange', 0)),
                change_pct=float(data.get('priceChangePercent', 0)),
                volume=int(float(data.get('volume', 0))),
                amount=float(data.get('quoteVolume', 0)),
                high=float(data.get('highPrice', 0)),
                low=float(data.get('lowPrice', 0)),
                open=float(data.get('openPrice', 0)),
                prev_close=float(data.get('prevClosePrice', 0)),
                timestamp=datetime.now().isoformat(),
                source="Binance"
            )
            
            self.cache.set(cache_key, quote, 30)  # 缓存30秒
            return quote
        except Exception as e:
            logger.warning(f"Failed to parse Binance ticker: {e}")
            return None
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[KlineBar]:
        """
        获取K线数据
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            interval: K线周期，如 "1m", "5m", "1h", "1d"
            limit: 数量
        """
        cache_key = f"binance_kline_{symbol}_{interval}_{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request("/api/v3/klines", {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        })
        
        if not data or not isinstance(data, list):
            return []
        
        bars = []
        for item in data:
            try:
                bar = KlineBar(
                    symbol=symbol.upper(),
                    market="CC",
                    timestamp=datetime.fromtimestamp(item[0] / 1000).isoformat(),
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=int(float(item[5])),
                    interval=interval,
                    source="Binance"
                )
                bars.append(bar)
            except (IndexError, ValueError):
                continue
        
        # 缓存策略
        is_daily = interval in ['1d', '1w', '1M']
        cache_ttl = 86400 if is_daily else 60
        self.cache.set(cache_key, bars, cache_ttl)
        
        return bars
    
    def get_multiple_tickers(self, symbols: List[str]) -> List[Quote]:
        """批量获取ticker"""
        results = []
        for symbol in symbols:
            ticker = self.get_ticker(symbol)
            if ticker:
                results.append(ticker)
            time.sleep(0.1)  # 礼貌延迟
        return results


# ============ Polygon.io Fetcher ============
class PolygonFetcher:
    """
    Polygon.io 美股/外汇/加密货币API
    
    Base URL: https://api.polygon.io
    限制：免费版 5次/分钟（stocks），支持延迟行情
    支持：美股（主要）、外汇、加密货币
    """
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key_v1: str, api_key_v2: str):
        """
        Args:
            api_key_v1: V1 API Key（备用）
            api_key_v2: V2 API Key（优先使用）
        """
        # 优先使用 V2 Key
        self.api_key = api_key_v2 if api_key_v2 else api_key_v1
        self.api_key_v1 = api_key_v1
        self.api_key_v2 = api_key_v2
        self.rate_limiter = RateLimiter(max_calls=5, period_seconds=60)  # 免费版5次/分钟
        self.session_config = {'timeout': 15, 'max_retries': 2}
        self.cache = CacheManager()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """发送HTTP请求"""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}{endpoint}"
        if params:
            params['apiKey'] = self.api_key
        else:
            params = {'apiKey': self.api_key}
        url += "?" + urllib.parse.urlencode(params)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; FinanceFetcher/1.0)',
            'Accept': 'application/json'
        }
        
        for attempt in range(self.session_config['max_retries']):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.session_config['timeout']) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get('status') == 'OK' or 'results' in data or 'tickers' in data:
                        return data
                    elif data.get('status') == 'DELAYED':
                        # 延迟数据仍然有效
                        return data
                    else:
                        logger.warning(f"Polygon API error: {data.get('error', 'Unknown error')}")
                        return None
            except Exception as e:
                logger.warning(f"Polygon request failed (attempt {attempt + 1}): {e}")
                if attempt < self.session_config['max_retries'] - 1:
                    time.sleep(2)
        
        return None
    
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """
        获取实时/延迟报价（上一个交易日OHLCV）
        
        Args:
            symbol: 股票代码，如 "AAPL"
            
        Returns:
            Quote对象
        """
        cache_key = f"polygon_quote_{symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request(f"/v2/aggs/ticker/{symbol}/prev")
        if not data or 'results' not in data or not data['results']:
            return None
        
        try:
            result = data['results'][0]
            # 计算涨跌
            open_price = float(result.get('o', 0))
            close_price = float(result.get('c', 0))
            prev_close = float(result.get('pc', close_price))
            change = close_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            
            quote = Quote(
                symbol=symbol,
                market="US",
                name=symbol,
                price=close_price,
                change=change,
                change_pct=change_pct,
                volume=int(result.get('v', 0)),
                amount=float(result.get('vw', 0)) * int(result.get('v', 0)),  # vw * volume
                high=float(result.get('h', 0)),
                low=float(result.get('l', 0)),
                open=open_price,
                prev_close=prev_close,
                timestamp=datetime.now().isoformat(),
                source="Polygon.io"
            )
            
            self.cache.set(cache_key, quote, 60)  # 缓存60秒
            return quote
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to parse Polygon quote: {e}")
            return None
    
    def get_kline(self, symbol: str, multiplier: int = 1, timespan: str = "day",
                   from_date: str = None, to_date: str = None, limit: int = 100) -> List[KlineBar]:
        """
        获取K线数据（聚合）
        
        Args:
            symbol: 股票代码
            multiplier: 乘数，如 1
            timespan: 时间跨度，如 "minute", "hour", "day", "week", "month", "quarter", "year"
            from_date: 开始日期 (YYYY-MM-DD)
            to_date: 结束日期 (YYYY-MM-DD)
            limit: 数量限制
            
        Returns:
            List[KlineBar]
        """
        # 默认日期范围：最近30天
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        cache_key = f"polygon_kline_{symbol}_{multiplier}_{timespan}_{from_date}_{to_date}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        endpoint = f"/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        params = {'adjusted': 'true', 'sort': 'asc', 'limit': min(limit, 499)}
        
        data = self._make_request(endpoint, params)
        if not data or 'results' not in data or not data['results']:
            return []
        
        bars = []
        try:
            for item in data['results']:
                bar = KlineBar(
                    symbol=symbol,
                    market="US",
                    timestamp=datetime.fromtimestamp(item['t'] / 1000).isoformat(),
                    open=float(item['o']),
                    high=float(item['h']),
                    low=float(item['l']),
                    close=float(item['c']),
                    volume=int(item['v']),
                    interval=f"{multiplier}{timespan[0]}",
                    source="Polygon.io"
                )
                bars.append(bar)
            
            # 缓存策略
            is_daily = timespan in ['day', 'week', 'month', 'quarter', 'year']
            cache_ttl = 86400 if is_daily else 300  # 日线24小时，其他5分钟
            self.cache.set(cache_key, bars, cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to parse Polygon kline: {e}")
        
        return bars
    
    def get_daily_open_close(self, symbol: str, date: str = None) -> Optional[Dict]:
        """
        获取每日开盘收盘数据
        
        Args:
            symbol: 股票代码
            date: 日期 (YYYY-MM-DD)，默认上一个交易日
            
        Returns:
            Dict with open/close data
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        cache_key = f"polygon_daily_{symbol}_{date}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request(f"/v1/open-close/{symbol}/{date}")
        if not data or 'symbol' not in data:
            return None
        
        self.cache.set(cache_key, data, 86400)  # 缓存24小时
        return data
    
    def get_forex_quote(self, from_currency: str, to_currency: str) -> Optional[Quote]:
        """
        获取外汇报价
        
        Args:
            from_currency: 基础货币，如 "USD"
            to_currency: 目标货币，如 "EUR"
            
        Returns:
            Quote对象
        """
        # Polygon外汇格式: C:{FROM}{TO}, 如 C:USDJPY
        symbol = f"C:{from_currency}{to_currency}"
        date = datetime.now().strftime("%Y-%m-%d")
        
        cache_key = f"polygon_forex_{from_currency}_{to_currency}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request(f"/v1/forex/{from_currency}/{to_currency}/{date}")
        if not data:
            return None
        
        try:
            quote = Quote(
                symbol=symbol,
                market="GB",
                name=f"{from_currency}/{to_currency}",
                price=float(data.get('close', 0)),
                change=float(data.get('change', 0)),
                change_pct=float(data.get('changePercent', 0)),
                volume=0,
                amount=0,
                high=float(data.get('high', 0)),
                low=float(data.get('low', 0)),
                open=float(data.get('open', 0)),
                prev_close=float(data.get('open', 0)),  # Polygon外汇不提供prevClose
                timestamp=data.get('date', datetime.now().isoformat()),
                source="Polygon.io"
            )
            
            self.cache.set(cache_key, quote, 300)  # 缓存5分钟
            return quote
        except Exception as e:
            logger.warning(f"Failed to parse Polygon forex quote: {e}")
            return None
    
    def get_crypto_quote(self, from_symbol: str, to_symbol: str) -> Optional[Quote]:
        """
        获取加密货币报价
        
        Args:
            from_symbol: 基础货币，如 "BTC"
            to_symbol: 目标货币，如 "USD"
            
        Returns:
            Quote对象
        """
        # Polygon加密货币格式: X:{FROM}{TO}, 如 X:BTCUSD
        symbol = f"X:{from_symbol}{to_symbol}"
        date = datetime.now().strftime("%Y-%m-%d")
        
        cache_key = f"polygon_crypto_{from_symbol}_{to_symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request(f"/v1/open-close/crypto/{from_symbol}/{to_symbol}/{date}")
        if not data:
            return None
        
        try:
            quote = Quote(
                symbol=symbol,
                market="CC",
                name=f"{from_symbol}/{to_symbol}",
                price=float(data.get('close', 0)),
                change=float(data.get('change', 0)),
                change_pct=float(data.get('changePercent', 0)),
                volume=int(data.get('volume', 0)),
                amount=0,
                high=float(data.get('high', 0)),
                low=float(data.get('low', 0)),
                open=float(data.get('open', 0)),
                prev_close=float(data.get('open', 0)),
                timestamp=data.get('date', datetime.now().isoformat()),
                source="Polygon.io"
            )
            
            self.cache.set(cache_key, quote, 60)  # 缓存1分钟
            return quote
        except Exception as e:
            logger.warning(f"Failed to parse Polygon crypto quote: {e}")
            return None
    
    def search_tickers(self, query: str, limit: int = 10) -> List[Dict]:
        """
        搜索标的
        
        Args:
            query: 搜索关键词
            limit: 返回数量
            
        Returns:
            List of ticker info
        """
        cache_key = f"polygon_search_{query}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        params = {
            'search': query,
            'active': 'true',
            'sort': 'ticker',
            'order': 'asc',
            'limit': limit
        }
        
        data = self._make_request("/v3/reference/tickers", params)
        if not data or 'results' not in data:
            return []
        
        results = data['results']
        self.cache.set(cache_key, results, 3600)  # 缓存1小时
        return results
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return bool(self.api_key)


# ============ AKShare Fetcher (简化实现) ============
class AKShareFetcher:
    """
    AKShare A股/期货数据
    
    注意：AKShare是Python库，本模块通过subprocess调用
    如import失败，降级为无数据
    """
    
    def __init__(self):
        self.cache = CacheManager()
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """检查是否可用"""
        try:
            import subprocess
            result = subprocess.run(
                ['python3', '-c', 'import akshare; print(akshare.__version__)'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_stock_realtime(self, symbol: str, market: str = "sh") -> Optional[Quote]:
        """
        获取A股实时行情
        
        Args:
            symbol: 股票代码，如 "600519"（茅台）
            market: 市场，"sh" 或 "sz"
        """
        if not self.available:
            logger.debug("AKShare not available, skipping")
            return None
        
        cache_key = f"akshare_realtime_{market}_{symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            import subprocess
            cmd = [
                'python3', '-c',
                f'''
import akshare as ak
try:
    df = ak.stock_zh_a_spot_em()
    row = df[df['代码'] == "{symbol}"]
    if not row.empty:
        print(row.iloc[0].to_json(force_ascii=False))
except Exception as e:
    print(f"ERROR: {{e}}")
'''
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0 and not result.stdout.decode().startswith("ERROR"):
                import json
                data = json.loads(result.stdout.decode())
                quote = Quote(
                    symbol=symbol,
                    market=market.upper(),
                    name=data.get('名称', symbol),
                    price=float(data.get('最新价', 0)),
                    change=float(data.get('涨跌额', 0)),
                    change_pct=float(data.get('涨跌幅', 0)),
                    volume=int(data.get('成交量', 0)),
                    amount=float(data.get('成交额', 0)),
                    high=float(data.get('最高', 0)),
                    low=float(data.get('最低', 0)),
                    open=float(data.get('今开', 0)),
                    prev_close=float(data.get('昨收', 0)),
                    timestamp=datetime.now().isoformat(),
                    source="AKShare"
                )
                self.cache.set(cache_key, quote, 30)
                return quote
        except Exception as e:
            logger.warning(f"AKShare fetch failed: {e}")
        
        return None
    
    def get_index_realtime(self, symbol: str = "000001") -> Optional[Quote]:
        """获取指数实时行情"""
        if not self.available:
            return None
        
        cache_key = f"akshare_index_{symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            import subprocess
            cmd = [
                'python3', '-c',
                f'''
import akshare as ak
try:
    if "{symbol}" == "000001":
        df = ak.stock_zh_index_spot_em(symbol="沪深300")
    else:
        df = ak.stock_zh_index_spot_em()
    row = df[df['代码'] == "{symbol}"]
    if not row.empty:
        print(row.iloc[0].to_json(force_ascii=False))
except Exception as e:
    print(f"ERROR: {{e}}")
'''
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0 and not result.stdout.decode().startswith("ERROR"):
                import json
                data = json.loads(result.stdout.decode())
                quote = Quote(
                    symbol=symbol,
                    market="INDEX",
                    name=data.get('名称', symbol),
                    price=float(data.get('最新价', 0)),
                    change=float(data.get('涨跌额', 0)),
                    change_pct=float(data.get('涨跌幅', 0)),
                    volume=int(data.get('成交量', 0)),
                    amount=float(data.get('成交额', 0)),
                    high=float(data.get('最高', 0)),
                    low=float(data.get('最低', 0)),
                    open=float(data.get('今开', 0)),
                    prev_close=float(data.get('昨收', 0)),
                    timestamp=datetime.now().isoformat(),
                    source="AKShare"
                )
                self.cache.set(cache_key, quote, 60)
                return quote
        except Exception as e:
            logger.warning(f"AKShare index fetch failed: {e}")
        
        return None


# ============ FRED Fetcher ============
class FREDFetcher:
    """
    FRED 宏观经济数据
    
    Base URL: https://api.stlouisfed.org/fred
    需要API Key（待配置）
    完全免费
    """
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.cache = CacheManager()
    
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """发送请求"""
        if not self.api_key:
            logger.debug("FRED API key not configured")
            return None
        
        params['api_key'] = self.api_key
        params['file_type'] = 'json'
        
        url = f"{self.BASE_URL}{endpoint}?" + urllib.parse.urlencode(params)
        
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            logger.warning(f"FRED request failed: {e}")
            return None
    
    def get_series_observations(self, series_id: str, limit: int = 100) -> List[Dict]:
        """
        获取经济数据序列
        
        Args:
            series_id: 序列ID，如 "GDP", "CPI", "UNRATE"
            limit: 返回数量
        """
        cache_key = f"fred_{series_id}_{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request("/series/observations", {
            "series_id": series_id,
            "limit": limit,
            "sort_order": "desc"
        })
        
        if not data or 'observations' not in data:
            return []
        
        observations = data['observations']
        self.cache.set(cache_key, observations, 86400)  # 缓存24小时
        return observations
    
    def get_series_search(self, text: str) -> List[Dict]:
        """搜索经济数据序列"""
        if not self.api_key:
            return []
        
        cache_key = f"fred_search_{text}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request("/series/search", {"search_text": text})
        
        if not data or 'seriess' not in data:
            return []
        
        seriess = data['seriess']
        self.cache.set(cache_key, seriess, 86400)
        return seriess
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key)


# ============ Signal Scanner ============
class SignalScanner:
    """
    金融信号扫描器
    
    检测：
    - 价格异动（涨跌幅超阈值）
    - 成交量突增
    - 价格突破关键位
    - 宏观数据发布
    """
    
    def __init__(self):
        # 默认阈值
        self.price_change_threshold = 5.0    # 价格变动阈值（%）
        self.volume_spike_threshold = 2.0     # 成交量突增倍数
        self.breakout_threshold = 3.0         # 突破阈值（%）
    
    def scan_price_anomaly(self, quote: Quote, history: List[KlineBar] = None) -> List[FinancePerceptionSignal]:
        """扫描价格异动"""
        signals = []
        
        # 涨跌幅异动
        if abs(quote.change_pct) >= self.price_change_threshold:
            severity = "high" if abs(quote.change_pct) >= 9 else "medium" if abs(quote.change_pct) >= 5 else "low"
            
            signal = FinancePerceptionSignal(
                signal_type=FinanceSignalType.MARKET_SIGNAL.value,
                source=quote.source,
                title=f"{quote.symbol} 价格异动: {quote.change_pct:+.2f}%",
                symbol=quote.symbol,
                severity=severity,
                summary=f"{quote.name} 涨跌幅 {quote.change_pct:+.2f}%，当前价格 ${quote.price:.2f}",
                timestamp=quote.timestamp,
                quote_data=quote,
                metadata={
                    'change': quote.change,
                    'change_pct': quote.change_pct,
                    'volume': quote.volume,
                    'anomaly_type': 'price_spike'
                }
            )
            signals.append(signal)
        
        return signals
    
    def scan_volume_spike(self, quote: Quote, history: List[KlineBar]) -> List[FinancePerceptionSignal]:
        """扫描成交量突增"""
        if not history or len(history) < 5:
            return []
        
        signals = []
        
        # 计算平均成交量
        recent_volumes = [bar.volume for bar in history[-5:-1]]
        avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        
        if avg_volume > 0:
            volume_ratio = quote.volume / avg_volume
            if volume_ratio >= self.volume_spike_threshold:
                severity = "high" if volume_ratio >= 3 else "medium" if volume_ratio >= 2 else "low"
                
                signal = FinancePerceptionSignal(
                    signal_type=FinanceSignalType.VOLUME_SPIKE.value,
                    source=quote.source,
                    title=f"{quote.symbol} 成交量突增 {volume_ratio:.1f}x",
                    symbol=quote.symbol,
                    severity=severity,
                    summary=f"成交量是近期平均的 {volume_ratio:.1f} 倍，可能有大资金活动",
                    timestamp=quote.timestamp,
                    quote_data=quote,
                    metadata={
                        'volume_ratio': volume_ratio,
                        'current_volume': quote.volume,
                        'avg_volume': avg_volume,
                        'anomaly_type': 'volume_spike'
                    }
                )
                signals.append(signal)
        
        return signals
    
    def scan_price_breakout(self, quote: Quote, history: List[KlineBar]) -> List[FinancePerceptionSignal]:
        """扫描价格突破"""
        if not history or len(history) < 20:
            return []
        
        signals = []
        
        # 使用近20日数据计算关键位
        highs = [bar.high for bar in history[-20:]]
        lows = [bar.low for bar in history[-20:]]
        
        # 当前价格突破20日高点
        if quote.price > max(highs):
            breakout_pct = (quote.price - max(highs)) / max(highs) * 100
            if breakout_pct >= self.breakout_threshold:
                signal = FinancePerceptionSignal(
                    signal_type=FinanceSignalType.PRICE_BREAKOUT.value,
                    source=quote.source,
                    title=f"{quote.symbol} 突破20日高点 ${max(highs):.2f}",
                    symbol=quote.symbol,
                    severity="medium",
                    summary=f"价格突破近期整理区间，当前 ${quote.price:.2f} > 20日高 ${max(highs):.2f}",
                    timestamp=quote.timestamp,
                    quote_data=quote,
                    metadata={
                        'breakout_price': max(highs),
                        'current_price': quote.price,
                        'breakout_pct': breakout_pct,
                        'anomaly_type': 'breakout'
                    }
                )
                signals.append(signal)
        
        # 价格跌破20日低点
        if quote.price < min(lows):
            breakdown_pct = (min(lows) - quote.price) / min(lows) * 100
            if breakdown_pct >= self.breakout_threshold:
                signal = FinancePerceptionSignal(
                    signal_type=FinanceSignalType.PRICE_BREAKOUT.value,
                    source=quote.source,
                    title=f"{quote.symbol} 跌破20日低点 ${min(lows):.2f}",
                    symbol=quote.symbol,
                    severity="medium",
                    summary=f"价格跌破近期支撑，当前 ${quote.price:.2f} < 20日低 ${min(lows):.2f}",
                    timestamp=quote.timestamp,
                    quote_data=quote,
                    metadata={
                        'breakdown_price': min(lows),
                        'current_price': quote.price,
                        'breakdown_pct': breakdown_pct,
                        'anomaly_type': 'breakdown'
                    }
                )
                signals.append(signal)
        
        return signals
    
    def scan_all(self, quote: Quote, history: List[KlineBar]) -> List[FinancePerceptionSignal]:
        """综合扫描"""
        signals = []
        signals.extend(self.scan_price_anomaly(quote, history))
        signals.extend(self.scan_volume_spike(quote, history))
        signals.extend(self.scan_price_breakout(quote, history))
        return signals


# ============ Main Finance Fetcher (v2.0 with SmartRouter) ============
class FinanceFetcher:
    """
    金融数据统一接口 v2.0
    
    整合 Polygon/iTick/AKShare/Binance/FRED
    使用 SmartRouter 实现智能路由和按需激活
    提供统一的数据获取和信号扫描接口
    
    公共接口（向后兼容）：
    - get_quote(symbol, market)
    - get_kline(symbol, market, interval, limit)
    - get_market_snapshot(symbols, market)
    - scan_signals(watchlist)
    - health_check()
    """
    
    # 获取脚本所在目录作为基准路径
    _SCRIPT_DIR = Path(__file__).parent.resolve()
    _PROJECT_ROOT = _SCRIPT_DIR.parent.parent.resolve()  # 假设脚本在 skills/global-info-fetcher/ 下
    
    def __init__(self, config_path: str = None,
                 secret_path: str = None):
        """
        初始化
        
        Args:
            config_path: 数据源配置文件路径（默认: ./skills/global-info-fetcher/sources_config.json）
            secret_path: 密钥文件路径（默认: ./SECRET.md）
        """
        # 使用相对于脚本目录的路径
        if config_path is None:
            config_path = self._SCRIPT_DIR / "sources_config.json"
        if secret_path is None:
            secret_path = self._PROJECT_ROOT / "SECRET.md"
        
        self.config_path = Path(config_path)
        self.secret_path = Path(secret_path)
        
        # 加载配置
        self.config = self._load_config()
        
        # 加载密钥
        self.secrets = self._load_secrets()
        
        # 创建智能路由器（不初始化任何 fetcher）
        self.router = SmartRouter(self.config, self.secrets)
        
        # 信号扫描器
        self.signal_scanner = SignalScanner()
        
        logger.info("Finance Fetcher v2.0 initialized with SmartRouter")
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _load_secrets(self) -> Dict:
        """加载密钥"""
        secrets = {}
        if self.secret_path.exists():
            with open(self.secret_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 解析 Polygon.io section
                in_polygon_section = False
                for line in content.split('\n'):
                    # 检测 Polygon.io section
                    if 'Polygon.io' in line:
                        in_polygon_section = True
                        continue
                    
                    # 如果在 Polygon section 中且是 V1/V2 key
                    if in_polygon_section:
                        if 'V1 API Key' in line and '**' in line:
                            parts = line.split('：')
                            if len(parts) < 2:
                                parts = line.split(':')
                            if len(parts) >= 2:
                                secrets['POLYGON_V1_KEY'] = parts[-1].strip().strip('*').strip()
                            continue
                        elif 'V2 API Key' in line and '**' in line:
                            parts = line.split('：')
                            if len(parts) < 2:
                                parts = line.split(':')
                            if len(parts) >= 2:
                                secrets['POLYGON_V2_KEY'] = parts[-1].strip().strip('*').strip()
                            continue
                        elif line.startswith('## ') or line.startswith('#'):
                            in_polygon_section = False
                    
                    # iTick API Key (格式: - **API Key**: <key>)
                    # iTick section 的多行格式：## iTick ... 后面跟着 - **API Key**: <key>
                    if 'iTick' in line and 'API Key' in line:
                        parts = line.split('**')
                        if len(parts) >= 3:
                            key = parts[-1].strip().strip(':').strip()
                            if key and len(key) > 10:
                                secrets['ITICK_API_KEY'] = key
                    elif 'iTick' in line and '##' in line:
                        # 进入 iTick section，继续检查后续行
                        in_itick_section = True
                        for next_line in content.split('\n')[content.split('\n').index(line)+1:]:
                            if next_line.startswith('## ') or next_line.startswith('#'):
                                break
                            if 'API Key' in next_line and '**' in next_line:
                                parts = next_line.split('**')
                                if len(parts) >= 3:
                                    key = parts[-1].strip().strip(':').strip()
                                    if key and len(key) > 10:
                                        secrets['ITICK_API_KEY'] = key
                                break
                    # FRED API Key
                    elif 'FRED' in line and 'API' in line and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            key = parts[-1].strip().strip('*').strip()
                            if key and len(key) > 10:
                                secrets['FRED_API_KEY'] = key
        return secrets
    
    def get_quote(self, symbol: str, market: str = "US") -> Optional[Quote]:
        """
        获取实时报价（统一接口）
        
        Args:
            symbol: 股票代码
            market: 市场 (US/HK/SH/SZ/CC/GB)
            
        Returns:
            Quote对象
        """
        # 获取路由链（按优先级排序的源列表）
        providers = self.router.route_with_fallback(market, "quote")
        
        for provider_name in providers:
            start_time = time.time()
            fetcher = self.router.get_fetcher(provider_name)
            if not fetcher:
                continue
            
            try:
                result = None
                if provider_name == 'polygon':
                    result = fetcher.get_quote(symbol)
                elif provider_name == 'itick':
                    result = fetcher.get_quote(symbol, market)
                elif provider_name == 'binance':
                    result = fetcher.get_ticker(symbol)
                elif provider_name == 'akshare':
                    market_prefix = "sh" if market == "SH" else "sz"
                    result = fetcher.get_stock_realtime(symbol, market_prefix)
                
                if result:
                    latency_ms = (time.time() - start_time) * 1000
                    self.router.report_success(provider_name, latency_ms)
                    return result
                    
            except Exception as e:
                self.router.report_failure(provider_name, str(e))
                logger.warning(f"Provider {provider_name} failed for {market}:{symbol}: {e}")
                continue
        
        logger.warning(f"No available data source for {market}:{symbol}")
        return None
    
    def get_kline(self, symbol: str, market: str = "US", 
                   interval: str = "1d", limit: int = 100) -> List[KlineBar]:
        """
        获取K线数据（统一接口）
        
        Args:
            symbol: 股票代码
            market: 市场
            interval: 周期 (1m/5m/15m/30m/1h/1d/1w/1M)
            limit: 数量
            
        Returns:
            List[KlineBar]
        """
        # 获取路由链
        providers = self.router.route_with_fallback(market, "kline")
        
        for provider_name in providers:
            start_time = time.time()
            fetcher = self.router.get_fetcher(provider_name)
            if not fetcher:
                continue
            
            try:
                result = None
                if provider_name == 'polygon':
                    # 转换interval到Polygon格式
                    polygon_timespan = {
                        "1m": "minute", "5m": "minute", "15m": "minute", "30m": "minute",
                        "1h": "hour", "1d": "day", "1w": "week", "1M": "month"
                    }.get(interval, "day")
                    
                    multiplier = {
                        "1m": 1, "5m": 5, "15m": 15, "30m": 30,
                        "1h": 1, "1d": 1, "1w": 1, "1M": 1
                    }.get(interval, 1)
                    
                    # 计算日期范围
                    days_back = {"1m": 7, "5m": 7, "15m": 30, "30m": 30, "1h": 60, "1d": 365, "1w": 365*2, "1M": 365*5}.get(interval, 30)
                    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                    to_date = datetime.now().strftime("%Y-%m-%d")
                    
                    result = fetcher.get_kline(symbol, multiplier, polygon_timespan, from_date, to_date, limit)
                    
                elif provider_name == 'itick':
                    k_type = ITICK_KLINE_MAP.get(interval, "101")
                    result = fetcher.get_kline(symbol, market, k_type, limit)
                    
                elif provider_name == 'binance':
                    result = fetcher.get_klines(symbol, interval, limit)
                
                if result and len(result) > 0:
                    latency_ms = (time.time() - start_time) * 1000
                    self.router.report_success(provider_name, latency_ms)
                    return result
                    
            except Exception as e:
                self.router.report_failure(provider_name, str(e))
                logger.warning(f"Provider {provider_name} kline failed for {market}:{symbol}: {e}")
                continue
        
        return []
    
    def get_market_snapshot(self, symbols: List[str], market: str = "US") -> List[Quote]:
        """
        获取市场快照
        
        Args:
            symbols: 股票代码列表
            market: 市场
            
        Returns:
            List[Quote]
        """
        quotes = []
        
        for symbol in symbols:
            quote = self.get_quote(symbol, market)
            if quote:
                quotes.append(quote)
            time.sleep(0.2)  # 礼貌延迟
        
        return quotes
    
    def scan_signals(self, watchlist: Dict[str, List[str]]) -> List[FinancePerceptionSignal]:
        """
        扫描市场信号
        
        Args:
            watchlist: 监控列表，格式 {"US": ["AAPL", "GOOGL"], "CC": ["BTCUSDT"]}
            
        Returns:
            List[FinancePerceptionSignal]
        """
        all_signals = []
        
        for market, symbols in watchlist.items():
            for symbol in symbols:
                # 获取实时报价
                quote = self.get_quote(symbol, market)
                if not quote:
                    continue
                
                # 获取历史K线用于分析
                history = self.get_kline(symbol, market, "1d", 30)
                
                # 扫描信号
                signals = self.signal_scanner.scan_all(quote, history)
                all_signals.extend(signals)
                
                time.sleep(0.3)
        
        # 按严重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        all_signals.sort(key=lambda s: severity_order.get(s.severity, 5))
        
        return all_signals
    
    def health_check(self) -> Dict[str, bool]:
        """
        数据源健康检查（兼容v1.0接口）
        
        Returns:
            Dict[str, bool] - 各数据源状态
        """
        # 使用 router 的健康检查
        health = self.router.health_check()
        
        # 转换为 v1.0 兼容格式
        result = {}
        for name, status in health.items():
            result[name] = status.get('available', False) and status.get('test_success', False)
        
        return result
    
    def get_forex_quote(self, from_currency: str, to_currency: str) -> Optional[Quote]:
        """获取外汇报价"""
        providers = self.router.route_with_fallback("GB", "forex")
        
        for provider_name in providers:
            fetcher = self.router.get_fetcher(provider_name)
            if not fetcher:
                continue
            
            try:
                if provider_name == 'polygon':
                    return fetcher.get_forex_quote(from_currency, to_currency)
                elif provider_name == 'itick':
                    symbol = f"{from_currency}{to_currency}"
                    return fetcher.get_forex_quote(symbol)
            except Exception as e:
                logger.warning(f"Forex quote failed via {provider_name}: {e}")
                continue
        
        return None
    
    def get_crypto_quote(self, from_symbol: str, to_symbol: str = "USDT") -> Optional[Quote]:
        """获取加密货币报价"""
        providers = self.router.route_with_fallback("CC", "crypto")
        
        for provider_name in providers:
            start_time = time.time()
            fetcher = self.router.get_fetcher(provider_name)
            if not fetcher:
                continue
            
            try:
                if provider_name == 'polygon':
                    result = fetcher.get_crypto_quote(from_symbol, to_symbol)
                elif provider_name == 'binance':
                    symbol = f"{from_symbol}{to_symbol}"
                    result = fetcher.get_ticker(symbol)
                
                if result:
                    latency_ms = (time.time() - start_time) * 1000
                    self.router.report_success(provider_name, latency_ms)
                    return result
                    
            except Exception as e:
                self.router.report_failure(provider_name, str(e))
                continue
        
        return None
    
    def get_macro_data(self, series_id: str, limit: int = 100) -> List[Dict]:
        """获取宏观经济数据"""
        fetcher = self.router.get_fetcher('fred')
        if fetcher and fetcher.is_configured():
            return fetcher.get_series_observations(series_id, limit)
        return []
    
    def activate_provider(self, name: str) -> bool:
        """手动激活某个数据源"""
        return self.router._activate_provider(name)
    
    def deactivate_provider(self, name: str):
        """手动停用某个数据源（释放资源）"""
        self.router.deactivate_provider(name)
    
    def get_status_report(self) -> str:
        """获取数据源状态报告"""
        return self.router.get_provider_status_report()
    
    def generate_signal_report(self, signals: List[FinancePerceptionSignal]) -> str:
        """生成信号报告"""
        lines = [
            "# 金融感知信号报告",
            "",
            f"**扫描时间**: {datetime.now().isoformat()}",
            f"**信号总数**: {len(signals)}",
            ""
        ]
        
        if not signals:
            lines.extend([
                "---",
                "",
                "✅ 未检测到异常信号",
                ""
            ])
            return "\n".join(lines)
        
        # 按类型统计
        type_counts = {}
        for sig in signals:
            type_counts[sig.signal_type] = type_counts.get(sig.signal_type, 0) + 1
        
        lines.extend([
            "## 信号统计",
            "",
            "| 类型 | 数量 |",
            "|------|------|"
        ])
        for sig_type, count in type_counts.items():
            lines.append(f"| {sig_type} | {count} |")
        
        lines.extend(["", "---", ""])
        
        # 按类型分组
        current_type = None
        for sig in signals:
            if sig.signal_type != current_type:
                current_type = sig.signal_type
                lines.extend(["", f"## {current_type.upper()}", ""])
            
            lines.append(sig.to_markdown())
            lines.append("")
        
        return "\n".join(lines)


# ============ CLI / Demo ============
async def demo():
    """演示"""
    print("🌐 Finance Fetcher v2.0 - 金融数据感知基础设施（智能路由版）")
    print("=" * 60)
    
    # 初始化
    fetcher = FinanceFetcher()
    
    # 查看数据源状态
    print("\n📊 数据源状态:")
    print(fetcher.get_status_report())
    
    # 健康检查
    print("\n📊 数据源健康检查:")
    health = fetcher.health_check()
    for source, status in health.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {source}: {'正常' if status else '不可用'}")
    
    # 测试获取报价（会触发按需激活）
    print("\n📈 获取实时报价:")
    
    # US 市场测试
    quote = fetcher.get_quote("AAPL", "US")
    if quote:
        print(f"  AAPL: ${quote.price:.2f} ({quote.change_pct:+.2f}%) [来源: {quote.source}]")
    
    # Binance测试（加密货币）
    btc = fetcher.get_quote("BTCUSDT", "CC")
    if btc:
        print(f"  BTCUSDT: ${btc.price:.2f} ({btc.change_pct:+.2f}%) [来源: {btc.source}]")
    
    # Polygon外汇测试
    usd_eur = fetcher.get_forex_quote("USD", "EUR")
    if usd_eur:
        print(f"  USD/EUR: ${usd_eur.price:.4f} [来源: {usd_eur.source}]")
    
    # Polygon K线测试
    print("\n📊 K线数据测试:")
    klines = fetcher.get_kline("AAPL", "US", "1d", 5)
    if klines:
        print(f"  AAPL 最近5日K线:")
        for bar in klines[-5:]:
            print(f"    {bar.timestamp[:10]}: O={bar.open:.2f} H={bar.high:.2f} L={bar.low:.2f} C={bar.close:.2f}")
    
    # 扫描信号
    print("\n🔍 扫描市场信号...")
    watchlist = {
        "US": ["AAPL", "GOOGL", "MSFT"],
        "CC": ["BTCUSDT", "ETHUSDT"]
    }
    
    signals = fetcher.scan_signals(watchlist)
    print(f"\n发现 {len(signals)} 个信号:")
    for sig in signals[:5]:
        print(f"  [{sig.severity.upper()}] {sig.title}")
    
    # 生成报告
    report = fetcher.generate_signal_report(signals)
    print("\n" + report)


def run_cli():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Finance Fetcher v2.0 - 金融数据感知基础设施')
    parser.add_argument('--quote', nargs=2, metavar=('SYMBOL', 'MARKET'),
                        help='获取股票报价，示例: --quote AAPL US')
    parser.add_argument('--kline', nargs=3, metavar=('SYMBOL', 'MARKET', 'INTERVAL'),
                        help='获取K线数据，示例: --kline AAPL US 1d')
    parser.add_argument('--health', action='store_true',
                        help='运行健康巡检')
    parser.add_argument('--status', action='store_true',
                        help='查看数据源状态')
    parser.add_argument('--activate', metavar='PROVIDER',
                        help='激活指定数据源，如 --activate polygon')
    parser.add_argument('--deactivate', metavar='PROVIDER',
                        help='停用指定数据源，如 --deactivate polygon')
    parser.add_argument('--test', action='store_true',
                        help='运行测试套件')
    parser.add_argument('--scan', nargs='+', metavar='SYMBOL',
                        help='扫描信号，示例: --scan AAPL GOOGL')
    
    args = parser.parse_args()
    
    if args.test:
        # 运行测试
        print("运行测试套件...")
        import subprocess
        result = subprocess.run(['python3', '-m', 'pytest', 
                                './skills/global-info-fetcher/test_finance_fetcher.py', 
                                '-v', '--tb=short'], 
                               capture_output=False)
        return
    
    # 初始化 fetcher
    fetcher = FinanceFetcher()
    
    if args.status:
        print(fetcher.get_status_report())
        return
    
    if args.health:
        print("运行健康巡检...")
        print(fetcher.get_status_report())
        return
    
    if args.activate:
        name = args.activate
        print(f"激活数据源: {name}")
        if fetcher.activate_provider(name):
            print(f"✅ {name} 激活成功")
        else:
            print(f"❌ {name} 激活失败")
        return
    
    if args.deactivate:
        name = args.deactivate
        print(f"停用数据源: {name}")
        fetcher.deactivate_provider(name)
        print(f"✅ {name} 已停用")
        return
    
    if args.quote:
        symbol, market = args.quote
        print(f"获取报价: {symbol} ({market})")
        quote = fetcher.get_quote(symbol, market)
        if quote:
            print(f"✅ 价格: ${quote.price:.2f} ({quote.change_pct:+.2f}%)")
            print(f"   来源: {quote.source}")
        else:
            print("❌ 获取失败")
        return
    
    if args.kline:
        symbol, market, interval = args.kline
        print(f"获取K线: {symbol} ({market}) {interval}")
        bars = fetcher.get_kline(symbol, market, interval, 5)
        if bars:
            print(f"✅ 获取到 {len(bars)} 条K线:")
            for bar in bars:
                print(f"   {bar.timestamp[:10]}: O={bar.open:.2f} H={bar.high:.2f} L={bar.low:.2f} C={bar.close:.2f}")
        else:
            print("❌ 获取失败")
        return
    
    if args.scan:
        symbols = args.scan
        print(f"扫描信号: {symbols}")
        watchlist = {"US": symbols}
        signals = fetcher.scan_signals(watchlist)
        print(f"发现 {len(signals)} 个信号:")
        for sig in signals:
            print(f"  [{sig.severity.upper()}] {sig.title}")
        return
    
    # 默认运行演示
    import asyncio
    asyncio.run(demo())


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_cli()
    else:
        import asyncio
        asyncio.run(demo())
