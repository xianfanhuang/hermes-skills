#!/usr/bin/env python3
"""
Smart Data Router v1.0 - 智能金融数据路由器

根据 品种/任务/需求 自动选择最优数据源

数据源:
- Tiger:     港股/A股实时(L2), 美股历史K线, 交易下单
- Finnhub:   美股实时行情, 外汇, 加密
- iTick:     跨市场行情(降级备用)
- Binance:   加密货币实时+历史
- Polygon:   美股主力(备用)

路由逻辑:
1. 按品种(stock/crypto/forex)筛选可用源
2. 按任务(realtime/kline/trade)筛选能力
3. 按健康分+延迟排序选最优
4. 失败自动降级到下一源

Author: Trading Assistant
Version: 1.0.0
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import urllib.request
import urllib.error

logger = logging.getLogger("SmartDataRouter")


# ============ 枚举定义 ============

class AssetType(Enum):
    US_STOCK = "us_stock"       # 美股
    HK_STOCK = "hk_stock"       # 港股
    A_STOCK = "a_stock"         # A股
    CRYPTO = "crypto"           # 加密货币
    FOREX = "forex"             # 外汇
    FUTURES = "futures"         # 期货
    INDEX = "index"             # 指数


class TaskType(Enum):
    REALTIME_QUOTE = "realtime"    # 实时报价
    KLINE = "kline"                # K线数据
    TRADE = "trade"                # 交易下单
    DEPTH = "depth"                # 盘口深度
    SNAPSHOT = "snapshot"          # 快照


class Provider(Enum):
    TIGER = "tiger"
    FINNHUB = "finnhub"
    ITICK = "itick"
    BINANCE = "binance"
    POLYGON = "polygon"


@dataclass
class QuoteData:
    """统一报价数据"""
    symbol: str
    price: float
    prev_close: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: int = 0
    change: float = 0.0
    change_pct: float = 0.0
    timestamp: str = ""
    provider: str = ""
    is_realtime: bool = False


@dataclass
class KlineBar:
    """统一K线数据"""
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: int = 0


@dataclass
class ProviderHealth:
    """数据源健康状态"""
    provider: Provider
    is_available: bool = True
    health_score: float = 1.0
    avg_latency_ms: float = 0.0
    success_count: int = 0
    fail_count: int = 0
    last_error: str = ""
    last_check: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 1.0

    def record_success(self, latency_ms: float):
        self.success_count += 1
        if self.avg_latency_ms > 0:
            self.avg_latency_ms = 0.7 * self.avg_latency_ms + 0.3 * latency_ms
        else:
            self.avg_latency_ms = latency_ms
        self._update_health()

    def record_failure(self, error: str):
        self.fail_count += 1
        self.last_error = error
        self._update_health()

    def _update_health(self):
        self.health_score = self.success_rate * 0.7 + (1.0 if self.avg_latency_ms < 500 else 0.5) * 0.3
        if self.health_score < 0.3:
            self.is_available = False


# ============ 路由规则 ============

# 每种资产类型的最优源排序
ROUTE_RULES: Dict[AssetType, Dict[TaskType, List[Provider]]] = {
    AssetType.US_STOCK: {
        TaskType.REALTIME_QUOTE: [Provider.FINNHUB, Provider.ITICK, Provider.POLYGON],
        TaskType.KLINE:          [Provider.TIGER, Provider.POLYGON, Provider.FINNHUB],
        TaskType.TRADE:          [Provider.TIGER],
        TaskType.SNAPSHOT:       [Provider.FINNHUB, Provider.TIGER],
    },
    AssetType.HK_STOCK: {
        TaskType.REALTIME_QUOTE: [Provider.TIGER, Provider.ITICK],
        TaskType.KLINE:          [Provider.TIGER, Provider.ITICK],
        TaskType.TRADE:          [Provider.TIGER],
        TaskType.SNAPSHOT:       [Provider.TIGER],
    },
    AssetType.A_STOCK: {
        TaskType.REALTIME_QUOTE: [Provider.TIGER, Provider.ITICK],
        TaskType.KLINE:          [Provider.TIGER, Provider.ITICK],
        TaskType.TRADE:          [Provider.TIGER],
    },
    AssetType.CRYPTO: {
        TaskType.REALTIME_QUOTE: [Provider.BINANCE, Provider.FINNHUB],
        TaskType.KLINE:          [Provider.BINANCE, Provider.FINNHUB],
        TaskType.TRADE:          [Provider.BINANCE],
    },
    AssetType.FOREX: {
        TaskType.REALTIME_QUOTE: [Provider.FINNHUB, Provider.ITICK],
        TaskType.KLINE:          [Provider.FINNHUB, Provider.ITICK],
    },
}


# ============ 源适配器 ============

class TigerAdapter:
    """Tiger API 适配器"""

    def __init__(self, secrets: Dict):
        self._client = None
        self._trade_client = None
        self._secrets = secrets

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from tigeropen.quote.quote_client import QuoteClient
            from tigeropen.trade.trade_client import TradeClient
            from tigeropen.tiger_open_config import TigerOpenClientConfig
            from tigeropen.common.consts import Language

            config = TigerOpenClientConfig(sandbox_debug=False)
            config.tiger_id = self._secrets.get('TIGER_ID', '20159412')
            config.private_key = self._secrets.get('TIGER_PRIVATE_KEY', '')
            config.language = Language.zh_CN
            config.account = self._secrets.get('TIGER_SIM_ACCOUNT', '21409378833585169')

            self._client = QuoteClient(config)
            self._trade_client = TradeClient(config)
            logger.info("🐯 Tiger adapter initialized")
        except Exception as e:
            logger.error(f"Tiger init failed: {e}")
            raise

    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """获取报价(通过最新K线收盘价，非实时)"""
        self._ensure_client()
        try:
            bars = self._client.get_bars([symbol], period="day", limit=2)
            if bars is None or len(bars) == 0:
                return None
            df = bars
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            price = float(last['close'])
            prev_close = float(prev['close'])
            return QuoteData(
                symbol=symbol,
                price=price,
                prev_close=prev_close,
                open=float(last.get('open', price)),
                high=float(last.get('high', price)),
                low=float(last.get('low', price)),
                volume=int(last.get('volume', 0)),
                change=price - prev_close,
                change_pct=(price - prev_close) / prev_close * 100 if prev_close else 0,
                timestamp=str(last.get('time', '')),
                provider="tiger",
                is_realtime=False,  # Tiger 美股不是实时
            )
        except Exception as e:
            logger.error(f"Tiger get_quote({symbol}): {e}")
            return None

    def get_quote_hk(self, symbol: str) -> Optional[QuoteData]:
        """港股实时报价 (Tiger 免费 L2)"""
        self._ensure_client()
        # Tiger 港股用纯数字代码，去掉 .HK 后缀
        code = symbol.replace('.HK', '').replace('.hk', '')
        if code.isdigit() and len(code) < 5:
            code = code.zfill(5)  # 0700 → 00700
        try:
            briefs = self._client.get_briefs([code])
            if briefs is None or len(briefs) == 0:
                return None
            b = briefs.iloc[0] if hasattr(briefs, 'iloc') else briefs[0]
            price = float(b.get('latestPrice', b.get('last', 0)))
            prev_close = float(b.get('preClose', 0))
            return QuoteData(
                symbol=symbol,
                price=price,
                prev_close=prev_close,
                open=float(b.get('open', 0)),
                high=float(b.get('high', 0)),
                low=float(b.get('low', 0)),
                volume=int(b.get('volume', 0)),
                change=price - prev_close if prev_close else 0,
                change_pct=(price - prev_close) / prev_close * 100 if prev_close else 0,
                timestamp=datetime.now().isoformat(),
                provider="tiger",
                is_realtime=True,
            )
        except Exception as e:
            logger.error(f"Tiger get_quote_hk({symbol}): {e}")
            return None

    def get_kline(self, symbol: str, period: str = "day", limit: int = 100,
                  asset_type: AssetType = AssetType.US_STOCK) -> List[KlineBar]:
        """获取K线数据"""
        self._ensure_client()
        # 港股代码转换
        code = symbol
        if asset_type == AssetType.HK_STOCK:
            code = symbol.replace('.HK', '').replace('.hk', '')
            if code.isdigit() and len(code) < 5:
                code = code.zfill(5)
        try:
            bars = self._client.get_bars([code], period=period, limit=limit)
            if bars is None or len(bars) == 0:
                return []
            result = []
            for _, row in bars.iterrows():
                result.append(KlineBar(
                    time=str(row.get('time', '')),
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row.get('volume', 0)),
                ))
            return result
        except Exception as e:
            logger.error(f"Tiger get_kline({symbol}, {period}): {e}")
            return []

    def place_order(self, symbol: str, action: str, quantity: int,
                    order_type: str = "MKT", price: float = 0) -> Optional[Dict]:
        """下单 (模拟盘)"""
        self._ensure_client()
        try:
            from tigeropen.common.consts import OrderType as TigerOrderType
            ot = TigerOrderType.MKT if order_type == "MKT" else TigerOrderType.LMT
            order = self._trade_client.create_order(
                account=self._secrets.get('TIGER_SIM_ACCOUNT', '21409378833585169'),
                symbol=symbol,
                action=action,
                order_type=ot,
                quantity=quantity,
                limit_price=price if order_type == "LMT" else None,
            )
            result = self._trade_client.place_order(order)
            return {'order_id': order.id, 'status': 'submitted', 'result': result}
        except Exception as e:
            logger.error(f"Tiger place_order: {e}")
            return None


class FinnhubAdapter:
    """Finnhub API 适配器"""

    def __init__(self, secrets: Dict):
        self._keys = []
        self._key_idx = 0
        # 收集所有 Finnhub keys
        for i in range(1, 6):
            key = secrets.get(f'FINNHUB_KEY_{i}', '')
            if key:
                self._keys.append(key)
        if not self._keys:
            # 尝试单一key格式
            key = secrets.get('FINNHUB_API_KEY', '')
            if key:
                self._keys.append(key)

    def _get_key(self) -> str:
        if not self._keys:
            raise ValueError("No Finnhub API keys configured")
        key = self._keys[self._key_idx % len(self._keys)]
        self._key_idx += 1
        return key

    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """获取美股实时报价"""
        try:
            key = self._get_key()
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={key}"
            req = urllib.request.Request(url, headers={"User-Agent": "SmartDataRouter/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            price = data.get('c', 0)
            prev_close = data.get('pc', 0)
            return QuoteData(
                symbol=symbol,
                price=price,
                prev_close=prev_close,
                open=data.get('o', 0),
                high=data.get('h', 0),
                low=data.get('l', 0),
                volume=int(data.get('v', 0)),
                change=price - prev_close if prev_close else 0,
                change_pct=data.get('dp', 0),
                timestamp=datetime.fromtimestamp(data.get('t', 0)).isoformat() if data.get('t') else '',
                provider="finnhub",
                is_realtime=True,
            )
        except Exception as e:
            logger.error(f"Finnhub get_quote({symbol}): {e}")
            return None

    def get_kline(self, symbol: str, resolution: str = "D", count: int = 100) -> List[KlineBar]:
        """获取K线 (Finnhub candle)"""
        try:
            key = self._get_key()
            # Finnhub 用 from/to 时间戳
            now = int(time.time())
            resolution_map = {"1": 60, "5": 300, "15": 900, "30": 1800, "60": 3600, "D": 86400, "W": 604800}
            interval = resolution_map.get(resolution, 86400)
            from_ts = now - interval * count
            url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution={resolution}&from={from_ts}&to={now}&token={key}"
            req = urllib.request.Request(url, headers={"User-Agent": "SmartDataRouter/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            if data.get('s') != 'ok':
                return []
            result = []
            for i in range(len(data.get('t', []))):
                result.append(KlineBar(
                    time=datetime.fromtimestamp(data['t'][i]).strftime('%Y-%m-%d'),
                    open=data['o'][i],
                    high=data['h'][i],
                    low=data['l'][i],
                    close=data['c'][i],
                    volume=int(data['v'][i]),
                    timestamp=data['t'][i],
                ))
            return result
        except Exception as e:
            logger.error(f"Finnhub get_kline({symbol}): {e}")
            return []


class BinanceAdapter:
    """Binance API 适配器 (免费，无需key)"""

    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """获取加密货币实时报价"""
        try:
            # symbol 格式: BTCUSDT, ETHUSDT
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "SmartDataRouter/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            price = float(data.get('lastPrice', 0))
            prev = float(data.get('prevClosePrice', 0))
            return QuoteData(
                symbol=symbol,
                price=price,
                prev_close=prev,
                open=float(data.get('openPrice', 0)),
                high=float(data.get('highPrice', 0)),
                low=float(data.get('lowPrice', 0)),
                volume=int(float(data.get('volume', 0))),
                change=float(data.get('priceChange', 0)),
                change_pct=float(data.get('priceChangePercent', 0)),
                timestamp=datetime.now().isoformat(),
                provider="binance",
                is_realtime=True,
            )
        except Exception as e:
            logger.error(f"Binance get_quote({symbol}): {e}")
            return None

    def get_kline(self, symbol: str, interval: str = "1d", limit: int = 100) -> List[KlineBar]:
        """获取K线数据"""
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "SmartDataRouter/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            result = []
            for k in data:
                result.append(KlineBar(
                    time=datetime.fromtimestamp(k[0] / 1000).strftime('%Y-%m-%d %H:%M'),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=int(float(k[5])),
                    timestamp=int(k[0] / 1000),
                ))
            return result
        except Exception as e:
            logger.error(f"Binance get_kline({symbol}): {e}")
            return []


class ITickAdapter:
    """iTick API 适配器"""

    def __init__(self, secrets: Dict):
        self._api_key = secrets.get('ITICK_API_KEY', '')

    def get_quote(self, symbol: str, market: str = "US") -> Optional[QuoteData]:
        """获取报价"""
        if not self._api_key:
            return None
        try:
            region_map = {"US": "US", "HK": "HK", "SH": "CN", "SZ": "CN"}
            region = region_map.get(market, "US")
            url = f"https://api.itick.org/quote?region={region}&symbol={symbol}"
            req = urllib.request.Request(url, headers={
                "User-Agent": "SmartDataRouter/1.0",
                "token": self._api_key,
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read()).get('data', {})
            price = float(data.get('last', data.get('close', 0)))
            prev = float(data.get('prevClose', 0))
            return QuoteData(
                symbol=symbol,
                price=price,
                prev_close=prev,
                open=float(data.get('open', 0)),
                high=float(data.get('high', 0)),
                low=float(data.get('low', 0)),
                volume=int(data.get('volume', 0)),
                change=price - prev if prev else 0,
                change_pct=(price - prev) / prev * 100 if prev else 0,
                timestamp=datetime.now().isoformat(),
                provider="itick",
                is_realtime=True,
            )
        except Exception as e:
            logger.error(f"iTick get_quote({symbol}): {e}")
            return None


# ============ 智能路由器核心 ============

class SmartDataRouter:
    """
    智能金融数据路由器

    使用方式:
        router = SmartDataRouter(secrets)
        quote = router.get_quote("AAPL", asset_type=AssetType.US_STOCK, task=TaskType.REALTIME_QUOTE)
        klines = router.get_kline("AAPL", asset_type=AssetType.US_STOCK, period="day", limit=100)
    """

    def __init__(self, secrets: Dict):
        self.secrets = secrets
        self._adapters: Dict[Provider, Any] = {}
        self._health: Dict[Provider, ProviderHealth] = {
            p: ProviderHealth(provider=p) for p in Provider
        }

    def _get_adapter(self, provider: Provider):
        """延迟初始化适配器"""
        if provider not in self._adapters:
            if provider == Provider.TIGER:
                self._adapters[provider] = TigerAdapter(self.secrets)
            elif provider == Provider.FINNHUB:
                self._adapters[provider] = FinnhubAdapter(self.secrets)
            elif provider == Provider.BINANCE:
                self._adapters[provider] = BinanceAdapter()
            elif provider == Provider.ITICK:
                self._adapters[provider] = ITickAdapter(self.secrets)
            elif provider == Provider.POLYGON:
                # Polygon 暂未接入，后续扩展
                return None
        return self._adapters.get(provider)

    def _select_providers(self, asset_type: AssetType, task: TaskType) -> List[Provider]:
        """根据资产类型和任务选择可用源（按健康分排序）"""
        rules = ROUTE_RULES.get(asset_type, {})
        candidates = rules.get(task, [])
        # 按健康分排序
        available = [
            p for p in candidates
            if self._health[p].is_available or self._health[p].fail_count < 5
        ]
        available.sort(key=lambda p: self._health[p].health_score, reverse=True)
        return available

    def get_quote(self, symbol: str, asset_type: AssetType = AssetType.US_STOCK,
                  task: TaskType = TaskType.REALTIME_QUOTE,
                  provider: Optional[Provider] = None) -> Optional[QuoteData]:
        """
        获取报价（智能路由）

        Args:
            symbol: 股票/币种代码
            asset_type: 资产类型
            task: 任务类型
            provider: 指定数据源（可选，不指定则自动路由）
        """
        if provider:
            providers = [provider]
        else:
            providers = self._select_providers(asset_type, task)

        for p in providers:
            adapter = self._get_adapter(p)
            if adapter is None:
                continue
            start = time.time()
            try:
                result = None
                # 港股走 Tiger 专用通道
                if p == Provider.TIGER and asset_type == AssetType.HK_STOCK:
                    result = adapter.get_quote_hk(symbol)
                elif p == Provider.TIGER:
                    result = adapter.get_quote(symbol)
                elif p == Provider.FINNHUB:
                    result = adapter.get_quote(symbol)
                elif p == Provider.BINANCE:
                    result = adapter.get_quote(symbol)
                elif p == Provider.ITICK:
                    market = {"us_stock": "US", "hk_stock": "HK", "a_stock": "SH"}.get(asset_type.value, "US")
                    result = adapter.get_quote(symbol, market=market)

                latency = (time.time() - start) * 1000
                if result:
                    self._health[p].record_success(latency)
                    logger.info(f"✅ {symbol} via {p.value}: ${result.price:.2f} ({latency:.0f}ms)")
                    return result
                else:
                    self._health[p].record_failure("empty result")
            except Exception as e:
                self._health[p].record_failure(str(e))
                logger.warning(f"❌ {symbol} via {p.value} failed: {e}")

        logger.error(f"All providers failed for {symbol} ({asset_type.value}/{task.value})")
        return None

    def get_kline(self, symbol: str, asset_type: AssetType = AssetType.US_STOCK,
                  period: str = "day", limit: int = 100,
                  provider: Optional[Provider] = None) -> List[KlineBar]:
        """
        获取K线数据（智能路由）

        Args:
            symbol: 代码
            asset_type: 资产类型
            period: 周期 (1/5/15/30/60 min, day, week)
            limit: 数量
            provider: 指定数据源
        """
        if provider:
            providers = [provider]
        else:
            providers = self._select_providers(asset_type, TaskType.KLINE)

        for p in providers:
            adapter = self._get_adapter(p)
            if adapter is None:
                continue
            start = time.time()
            try:
                result = None
                if p == Provider.TIGER:
                    result = adapter.get_kline(symbol, period=period, limit=limit, asset_type=asset_type)
                elif p == Provider.FINNHUB:
                    res_map = {"1": "1", "5": "5", "15": "15", "30": "30", "60": "60", "day": "D", "week": "W"}
                    result = adapter.get_kline(symbol, resolution=res_map.get(period, "D"), count=limit)
                elif p == Provider.BINANCE:
                    interval_map = {"1": "1m", "5": "5m", "15": "15m", "30": "30m", "60": "1h", "day": "1d", "week": "1w"}
                    result = adapter.get_kline(symbol, interval=interval_map.get(period, "1d"), limit=limit)

                latency = (time.time() - start) * 1000
                if result and len(result) > 0:
                    self._health[p].record_success(latency)
                    logger.info(f"✅ {symbol} kline({period}) via {p.value}: {len(result)} bars ({latency:.0f}ms)")
                    return result
                else:
                    self._health[p].record_failure("empty result")
            except Exception as e:
                self._health[p].record_failure(str(e))
                logger.warning(f"❌ {symbol} kline via {p.value} failed: {e}")

        return []

    def place_order(self, symbol: str, action: str, quantity: int,
                    order_type: str = "MKT", price: float = 0,
                    asset_type: AssetType = AssetType.US_STOCK) -> Optional[Dict]:
        """
        下单（仅 Tiger 模拟盘）

        Args:
            symbol: 代码
            action: BUY/SELL
            quantity: 数量
            order_type: MKT/LMT
            price: 限价（LMT 时必填）
            asset_type: 资产类型
        """
        adapter = self._get_adapter(Provider.TIGER)
        if adapter is None:
            logger.error("Tiger adapter not available for trading")
            return None
        return adapter.place_order(symbol, action, quantity, order_type, price)

    def get_health_report(self) -> Dict:
        """获取所有数据源健康状态"""
        return {
            p.value: {
                'available': h.is_available,
                'health_score': round(h.health_score, 3),
                'success_rate': round(h.success_rate, 3),
                'avg_latency_ms': round(h.avg_latency_ms, 1),
                'success': h.success_count,
                'fail': h.fail_count,
                'last_error': h.last_error,
            }
            for p, h in self._health.items()
            if h.success_count > 0 or h.fail_count > 0
        }

    def smart_quote(self, symbol: str, market_hint: str = "auto") -> Optional[QuoteData]:
        """
        智能报价 - 自动判断资产类型

        Args:
            symbol: 代码，如 AAPL, 0700.HK, BTCUSDT
            market_hint: auto/US/HK/CN/CRYPTO
        """
        asset_type = self._detect_asset_type(symbol, market_hint)
        task = TaskType.REALTIME_QUOTE if asset_type != AssetType.US_STOCK else TaskType.SNAPSHOT
        return self.get_quote(symbol, asset_type=asset_type, task=task)

    def _detect_asset_type(self, symbol: str, hint: str = "auto") -> AssetType:
        """自动检测资产类型"""
        if hint != "auto":
            mapping = {"US": AssetType.US_STOCK, "HK": AssetType.HK_STOCK, "CN": AssetType.A_STOCK, "CRYPTO": AssetType.CRYPTO}
            return mapping.get(hint, AssetType.US_STOCK)

        s = symbol.upper()
        # 加密货币
        if any(s.endswith(suffix) for suffix in ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH']):
            return AssetType.CRYPTO
        if s in ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'MATIC']:
            return AssetType.CRYPTO
        # 港股 (带 .HK 后缀，或 4-5位数字)
        if '.HK' in s or s.endswith('HK'):
            return AssetType.HK_STOCK
        # A股 (带 .SH/.SZ 后缀)
        if '.SH' in s or '.SZ' in s:
            return AssetType.A_STOCK
        # 纯数字判断
        clean = s.replace('.', '').replace('-', '')
        if clean.isdigit():
            if len(clean) in [4, 5]:
                return AssetType.HK_STOCK
            if len(clean) == 6:
                return AssetType.A_STOCK
        # 默认美股
        return AssetType.US_STOCK

    def get_route_info(self, symbol: str, asset_type: AssetType, task: TaskType) -> Dict:
        """查看路由信息（调试用）"""
        providers = self._select_providers(asset_type, task)
        return {
            'symbol': symbol,
            'asset_type': asset_type.value,
            'task': task.value,
            'providers': [p.value for p in providers],
            'health': {p.value: round(self._health[p].health_score, 3) for p in providers},
        }


# ============ 便捷函数 ============

def create_router(secrets_path: str = None) -> SmartDataRouter:
    """创建路由器实例"""
    if secrets_path is None:
        secrets_path = str(Path(__file__).parent.parent.parent / "SECRET.md")

    secrets = {}
    path = Path(secrets_path)
    if path.exists():
        content = path.read_text()
        import re

        # Finnhub keys - 格式: 1. `key`  或  - **API Key**: key
        finnhub_section = False
        for line in content.split('\n'):
            if 'Finnhub' in line:
                finnhub_section = True
                continue
            if finnhub_section and line.startswith('##'):
                finnhub_section = False
                continue
            if finnhub_section:
                # 匹配 `key` 格式
                match = re.search(r'`([a-z0-9]{30,})`', line)
                if match:
                    secrets[f'FINNHUB_KEY_{len([k for k in secrets if k.startswith("FINNHUB_KEY_")]) + 1}'] = match.group(1)

        # iTick API Key
        match = re.search(r'API Key.*?:\s*\*{0,2}([a-f0-9]{40,})\*{0,2}', content)
        if match:
            secrets['ITICK_API_KEY'] = match.group(1)

        # Tiger 配置
        for key_name, pattern in [
            ('TIGER_ID', r'TIGER_ID.*?:\s*\*{0,2}(\d+)\*{0,2}'),
            ('TIGER_SIM_ACCOUNT', r'TIGER_SIMULATION_ACCOUNT.*?:\s*\*{0,2}(\d+)\*{0,2}'),
            ('TIGER_LIVE_ACCOUNT', r'TIGER_LIVE_ACCOUNT.*?:\s*\*{0,2}(\d+)\*{0,2}'),
        ]:
            match = re.search(pattern, content)
            if match:
                secrets[key_name] = match.group(1)

        # Tiger Private Key (多行 base64)
        match = re.search(r'TIGER_PRIVATE_KEY.*?:\s*\*{0,2}(MIIC[a-zA-Z0-9+/=\s]+?)\*{0,2}(?:\n\n|\n##|\Z)', content, re.DOTALL)
        if match:
            pk = match.group(1).strip().replace('\n', '').replace(' ', '')
            secrets['TIGER_PRIVATE_KEY'] = pk

        logger.info(f"Loaded secrets: {[k for k in secrets.keys()]}")
    return SmartDataRouter(secrets)


# ============ CLI 测试 ============

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    router = create_router()

    # 测试路由
    test_cases = [
        ("AAPL", "auto", "美股自动路由"),
        ("0700.HK", "auto", "港股自动路由"),
        ("BTCUSDT", "auto", "加密货币自动路由"),
        ("CRCL", "US", "CRCL 美股"),
    ]

    print("\n📊 Smart Data Router v1.0 测试")
    print("=" * 60)

    for symbol, hint, desc in test_cases:
        asset_type = router._detect_asset_type(symbol, hint)
        print(f"\n🔍 {desc} ({symbol}):")
        for task in [TaskType.REALTIME_QUOTE, TaskType.KLINE]:
            info = router.get_route_info(symbol, asset_type, task)
            print(f"  {task.value}: {' → '.join(info['providers'])}")

    print("\n📊 健康报告:")
    report = router.get_health_report()
    if report:
        for name, info in report.items():
            print(f"  {name}: score={info['health_score']}, latency={info['avg_latency_ms']}ms")
    else:
        print("  (暂无数据)")

    # 如果传了参数，实际测试
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
        print(f"\n🚀 实际测试: {symbol}")
        quote = router.smart_quote(symbol)
        if quote:
            print(f"  价格: ${quote.price:.2f}")
            print(f"  涨跌: {quote.change_pct:+.2f}%")
            print(f"  来源: {quote.provider} (实时={quote.is_realtime})")
        else:
            print("  获取失败")
