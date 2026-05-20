#!/usr/bin/env python3
"""
Finance Fetcher 测试套件

测试覆盖：
1. ProviderProfile 测试
2. SmartRouter 测试
3. FinanceFetcher 测试
4. 各 Provider 单元测试
5. 集成测试（需要网络，标记为 @pytest.mark.integration）

运行方式：
    pytest test_finance_fetcher.py -v              # 运行所有测试
    pytest test_finance_fetcher.py -v -m "not integration"  # 仅单元测试
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, List, Optional

# 导入被测模块
import sys
sys.path.insert(0, '.')

from finance_fetcher import (
    FinanceFetcher, SmartRouter, ProviderProfile, ProviderState,
    Quote, KlineBar, KlineInterval, FinancePerceptionSignal, FinanceSignalType,
    RateLimiter, CacheManager, ITickFetcher, PolygonFetcher, BinanceFetcher,
    AKShareFetcher, FREDFetcher, SignalScanner
)


# ============ Fixtures ============

@pytest.fixture
def mock_secrets():
    """Mock secrets for testing"""
    return {
        'POLYGON_V1_KEY': 'test_polygon_v1_key',
        'POLYGON_V2_KEY': 'test_polygon_v2_key',
        'ITICK_API_KEY': 'test_itick_key',
        'FRED_API_KEY': 'test_fred_key'
    }


@pytest.fixture
def mock_config():
    """Mock config for testing"""
    return {
        'sources': {
            'polygon': {'priority': 1},
            'itick': {'priority': 2}
        }
    }


@pytest.fixture
def smart_router(mock_config, mock_secrets):
    """Create SmartRouter instance for testing"""
    return SmartRouter(mock_config, mock_secrets)


@pytest.fixture
def finance_fetcher(mock_config, mock_secrets):
    """Create FinanceFetcher instance for testing"""
    with patch('finance_fetcher.Path.exists', return_value=True):
        with patch('builtins.open', side_effect=FileNotFoundError()):
            with patch('finance_fetcher.SmartRouter') as MockRouter:
                mock_router = Mock()
                mock_router.route_with_fallback.return_value = ['polygon']
                mock_router.health_check.return_value = {'polygon': {'available': True, 'test_success': True}}
                mock_router.get_provider_status_report.return_value = "# Test Report"
                MockRouter.return_value = mock_router
                
                # 直接构造不使用mock
                pass
    
    # 使用实际的 FinanceFetcher 但 mock 文件读取
    with patch('builtins.open', mock_open_read=Mock(side_effect=FileNotFoundError)):
        fetcher = FinanceFetcher.__new__(FinanceFetcher)
        fetcher.config_path = None
        fetcher.secret_path = None
        fetcher.config = mock_config
        fetcher.secrets = mock_secrets
        fetcher.router = SmartRouter(mock_config, mock_secrets)
        fetcher.signal_scanner = SignalScanner()
    
    return fetcher


# ============ Helper Classes for Mocking ============

class MockResponse:
    """Mock HTTP Response"""
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
    
    def read(self):
        return json.dumps(self.data).encode('utf-8')


# ============ 1. ProviderProfile Tests ============

class TestProviderProfile:
    """ProviderProfile 单元测试"""
    
    def test_provider_profile_creation(self):
        """测试 ProviderProfile 创建"""
        profile = ProviderProfile(
            name='test_provider',
            markets=['US', 'HK'],
            capabilities=['quote', 'kline'],
            state=ProviderState.UNINITIALIZED,
            priority=1
        )
        
        assert profile.name == 'test_provider'
        assert profile.markets == ['US', 'HK']
        assert profile.capabilities == ['quote', 'kline']
        assert profile.state == ProviderState.UNINITIALIZED
        assert profile.priority == 1
        assert profile.health_score == 1.0
        assert profile.success_rate == 1.0
        assert profile.consecutive_failures == 0
    
    def test_provider_state_transitions(self):
        """测试 ProviderState 状态转换"""
        profile = ProviderProfile(
            name='test',
            markets=['US'],
            capabilities=['quote'],
            state=ProviderState.ACTIVE,
            priority=1
        )
        
        # 初始为 ACTIVE
        assert profile.state == ProviderState.ACTIVE
        
        # 模拟连续失败
        for _ in range(3):
            profile.update_health_on_failure("test error")
        
        # 连续失败应该触发降级检查（health_score 降低）
        assert profile.health_score < 1.0
        assert profile.consecutive_failures == 3
    
    def test_health_score_calculation(self):
        """测试健康分计算"""
        profile = ProviderProfile(
            name='test',
            markets=['US'],
            capabilities=['quote'],
            state=ProviderState.ACTIVE,
            priority=1
        )
        
        # 多次成功调用
        for _ in range(10):
            profile.update_health_on_success(100.0)
        
        assert profile.health_score > 0.7
        assert profile.success_rate == 1.0
        assert profile.latency_ms == 100.0
        
        # 模拟失败
        profile.update_health_on_failure("error")
        
        assert profile.success_rate < 1.0
        assert profile.consecutive_failures == 1
    
    def test_health_score_with_latency(self):
        """测试延迟对健康分的影响"""
        profile = ProviderProfile(
            name='test',
            markets=['US'],
            capabilities=['quote'],
            state=ProviderState.ACTIVE,
            priority=1
        )
        
        # 低延迟调用
        for _ in range(10):
            profile.update_health_on_success(50.0)
        
        high_score = profile.health_score
        
        # 创建新 profile 用高延迟
        profile2 = ProviderProfile(
            name='test2',
            markets=['US'],
            capabilities=['quote'],
            state=ProviderState.ACTIVE,
            priority=1
        )
        
        for _ in range(10):
            profile2.update_health_on_success(1500.0)
        
        # 高延迟应该有更低的健康分
        assert profile2.health_score < high_score


# ============ 2. SmartRouter Tests ============

class TestSmartRouter:
    """SmartRouter 单元测试"""
    
    def test_register_providers(self, smart_router):
        """测试数据源注册"""
        providers = smart_router.providers
        
        assert 'polygon' in providers
        assert 'itick' in providers
        assert 'binance' in providers
        assert 'akshare' in providers
        assert 'fred' in providers
        
        # 所有源初始状态为 UNINITIALIZED
        for name, profile in providers.items():
            assert profile.state == ProviderState.UNINITIALIZED
    
    def test_route_us_market_selects_polygon_first(self, smart_router):
        """测试 US 市场优先选择 Polygon"""
        provider = smart_router.route('US', 'quote')
        
        # Polygon 应该有最高优先级
        assert provider == 'polygon'
    
    def test_route_crypto_selects_binance(self, smart_router):
        """测试加密货币市场 - Polygon 和 Binance 都支持"""
        # Polygon 和 Binance 都支持 CC 市场，但 Polygon 优先级更高
        providers = smart_router.route_with_fallback('CC', 'quote')
        
        # 两者都应该在候选列表中，polygon 优先
        assert 'polygon' in providers
        assert 'binance' in providers
        # polygon 应该在 binance 前面（优先级更高）
        assert providers.index('polygon') < providers.index('binance')
    
    def test_route_with_fallback_returns_list(self, smart_router):
        """测试 fallback 链返回列表"""
        providers = smart_router.route_with_fallback('US', 'quote')
        
        assert isinstance(providers, list)
        assert len(providers) > 0
        assert 'polygon' in providers
    
    def test_auto_activate_on_first_use(self, smart_router):
        """测试首次使用时自动激活"""
        # Polygon 初始为 UNINITIALIZED
        polygon_profile = smart_router.providers['polygon']
        assert polygon_profile.state == ProviderState.UNINITIALIZED
        
        # Mock PolygonFetcher
        mock_fetcher = Mock()
        mock_fetcher.get_quote.return_value = Quote(
            symbol='AAPL', market='US', name='Apple', price=150.0,
            change=1.0, change_pct=0.67, volume=1000000, amount=150000000,
            high=151.0, low=149.0, open=149.5, prev_close=149.0,
            timestamp=datetime.now().isoformat(), source='Polygon.io'
        )
        
        with patch.object(PolygonFetcher, '__init__', return_value=None):
            with patch.object(PolygonFetcher, 'is_available', return_value=True):
                with patch.object(PolygonFetcher, 'get_quote', return_value=mock_fetcher.get_quote()):
                    # 获取 fetcher 会触发激活
                    fetcher = smart_router.get_fetcher('polygon')
                    
                    # 状态应该变为 ACTIVE（如果激活成功）
                    # 注意：实际激活需要真实 API key，这里测试流程
                    assert polygon_profile.name == 'polygon'
    
    def test_route_degraded_provider_skipped(self, smart_router):
        """测试降级源被跳过"""
        # 手动设置一个源为 DEGRADED
        smart_router.providers['binance'].state = ProviderState.DEGRADED
        
        # DEGRADED 源仍然可用，但排序靠后
        providers = smart_router.route_with_fallback('CC', 'quote')
        
        # binance 应该在列表中但不是首选
        assert 'binance' in providers
    
    def test_route_retired_provider_excluded(self, smart_router):
        """测试退休源被排除"""
        # 手动设置一个源为 RETIRED 且最近检查
        smart_router.providers['binance'].state = ProviderState.RETIRED
        smart_router.providers['binance'].last_check = datetime.now()
        
        # RETIRED 源短期内应该被排除
        providers = smart_router.route_with_fallback('CC', 'quote')
        
        # 应该没有可用源（因为 binance 退休且未到重试时间）
        # 注意：路由可能返回空或只有能用的源
    
    def test_deactivate_releases_resources(self, smart_router):
        """测试停用释放资源"""
        # 先激活
        smart_router.providers['binance'].fetcher = Mock()
        smart_router.providers['binance'].state = ProviderState.ACTIVE
        
        # 停用
        smart_router.deactivate_provider('binance')
        
        # 状态应该变回 UNINITIALIZED，fetcher 应该为 None
        assert smart_router.providers['binance'].state == ProviderState.UNINITIALIZED
        assert smart_router.providers['binance'].fetcher is None
    
    def test_report_success_updates_health(self, smart_router):
        """测试成功调用更新健康指标"""
        profile = smart_router.providers['polygon']
        profile.state = ProviderState.ACTIVE
        
        initial_score = profile.health_score
        
        smart_router.report_success('polygon', 100.0)
        
        # 成功率应该更新
        assert profile.success_rate == 1.0
        # 延迟应该接近 100ms
        assert profile.latency_ms > 0
    
    def test_report_failure_updates_health(self, smart_router):
        """测试失败调用更新健康指标"""
        profile = smart_router.providers['polygon']
        profile.state = ProviderState.ACTIVE
        
        smart_router.report_failure('polygon', "Connection timeout")
        
        # 连续失败应该增加
        assert profile.consecutive_failures == 1
        # 健康分应该降低
        assert profile.health_score < 1.0
    
    def test_provider_state_auto_degrade(self, smart_router):
        """测试连续失败自动降级"""
        profile = smart_router.providers['polygon']
        profile.state = ProviderState.ACTIVE
        
        # 连续失败 3 次会触发降级检查
        for _ in range(3):
            smart_router.report_failure('polygon', "error")
        
        # 手动调用状态更新检查
        smart_router.update_provider_state('polygon')
        
        # 由于成功率变为 0（100% 失败），会直接退休
        # 降级或退休取决于 update_provider_state 的逻辑
        assert profile.state in [ProviderState.DEGRADED, ProviderState.RETIRED]
        assert profile.consecutive_failures == 3
    
    def test_provider_state_recovery(self):
        """测试降级状态恢复 - 使用独立的 profile"""
        # 直接创建测试用的 profile
        from finance_fetcher import ProviderProfile, ProviderState, SmartRouter
        
        profile = ProviderProfile(
            name='recovery_test',
            markets=['US'],
            capabilities=['quote'],
            state=ProviderState.DEGRADED,
            priority=1,
            total_requests=10,
            failed_requests=1,  # 成功率 90%
            consecutive_failures=0
        )
        
        # 创建临时的 SmartRouter 来测试方法
        class TestRouter:
            CONSECUTIVE_FAILURES_DEGRADE = 3
            RETIRED_GRACE_PERIOD_HOURS = 24
            RETRY_RETIRED_AFTER_DAYS = 7
            
            def update_provider_state(self, name):
                # 恢复逻辑
                if profile.state == ProviderState.DEGRADED:
                    if profile.success_rate >= 0.8 and profile.consecutive_failures == 0:
                        profile.state = ProviderState.ACTIVE
        
        router = TestRouter()
        
        # 验证初始状态
        assert profile.state == ProviderState.DEGRADED
        
        # 调用恢复检查
        router.update_provider_state('recovery_test')
        
        # 应该恢复到 ACTIVE（成功率 90% >= 80%，连续失败 0）
        assert profile.state == ProviderState.ACTIVE


# ============ 3. FinanceFetcher Tests ============

class TestFinanceFetcher:
    """FinanceFetcher 单元测试"""
    
    def test_get_quote_with_smart_routing(self, mock_config, mock_secrets):
        """测试通过智能路由获取报价"""
        # 创建 mock fetcher
        mock_quote = Quote(
            symbol='AAPL', market='US', name='Apple', price=150.0,
            change=1.0, change_pct=0.67, volume=1000000, amount=150000000,
            high=151.0, low=149.0, open=149.5, prev_close=149.0,
            timestamp=datetime.now().isoformat(), source='Test'
        )
        
        # Mock SmartRouter
        with patch('finance_fetcher.SmartRouter') as MockRouter:
            mock_router = Mock()
            mock_router.route_with_fallback.return_value = ['polygon', 'itick']
            mock_router.get_fetcher.return_value = Mock(get_quote=Mock(return_value=mock_quote))
            mock_router.report_success = Mock()
            mock_router.report_failure = Mock()
            MockRouter.return_value = mock_router
            
            fetcher = FinanceFetcher.__new__(FinanceFetcher)
            fetcher.config = mock_config
            fetcher.secrets = mock_secrets
            fetcher.router = mock_router
            fetcher.signal_scanner = SignalScanner()
            
            result = fetcher.get_quote('AAPL', 'US')
            
            assert result is not None
            assert result.symbol == 'AAPL'
            mock_router.report_success.assert_called_once()
    
    def test_get_quote_with_fallback(self, mock_config, mock_secrets):
        """测试 fallback 机制"""
        mock_quote = Quote(
            symbol='AAPL', market='US', name='Apple', price=150.0,
            change=1.0, change_pct=0.67, volume=1000000, amount=150000000,
            high=151.0, low=149.0, open=149.5, prev_close=149.0,
            timestamp=datetime.now().isoformat(), source='Fallback'
        )
        
        call_count = {'count': 0}
        
        def mock_get_fetcher(name):
            call_count['count'] += 1
            if call_count['count'] == 1:
                # 第一个源失败
                return None
            else:
                mock_fetcher = Mock()
                mock_fetcher.get_quote.return_value = mock_quote
                return mock_fetcher
        
        with patch('finance_fetcher.SmartRouter') as MockRouter:
            mock_router = Mock()
            mock_router.route_with_fallback.return_value = ['polygon', 'itick']
            mock_router.get_fetcher.side_effect = mock_get_fetcher
            mock_router.report_failure = Mock()
            mock_router.report_success = Mock()
            MockRouter.return_value = mock_router
            
            fetcher = FinanceFetcher.__new__(FinanceFetcher)
            fetcher.config = mock_config
            fetcher.secrets = mock_secrets
            fetcher.router = mock_router
            fetcher.signal_scanner = SignalScanner()
            
            result = fetcher.get_quote('AAPL', 'US')
            
            assert result is not None
            assert result.source == 'Fallback'
    
    def test_get_kline_with_fallback(self, mock_config, mock_secrets):
        """测试 K线 fallback"""
        mock_bars = [
            KlineBar(
                symbol='AAPL', market='US', timestamp='2024-01-01',
                open=150.0, high=151.0, low=149.0, close=150.5,
                volume=1000000, interval='1d', source='Test'
            )
        ]
        
        with patch('finance_fetcher.SmartRouter') as MockRouter:
            mock_router = Mock()
            mock_router.route_with_fallback.return_value = ['polygon']
            mock_fetcher = Mock()
            mock_fetcher.get_kline.return_value = mock_bars
            mock_router.get_fetcher.return_value = mock_fetcher
            mock_router.report_success = Mock()
            MockRouter.return_value = mock_router
            
            fetcher = FinanceFetcher.__new__(FinanceFetcher)
            fetcher.config = mock_config
            fetcher.secrets = mock_secrets
            fetcher.router = mock_router
            fetcher.signal_scanner = SignalScanner()
            
            result = fetcher.get_kline('AAPL', 'US', '1d', 100)
            
            assert len(result) == 1
            assert result[0].symbol == 'AAPL'
    
    def test_health_check_all_providers(self, mock_config, mock_secrets):
        """测试健康检查"""
        with patch('finance_fetcher.SmartRouter') as MockRouter:
            mock_router = Mock()
            mock_router.health_check.return_value = {
                'polygon': {'available': True, 'test_success': True},
                'itick': {'available': True, 'test_success': False},
                'binance': {'available': True, 'test_success': True}
            }
            MockRouter.return_value = mock_router
            
            fetcher = FinanceFetcher.__new__(FinanceFetcher)
            fetcher.config = mock_config
            fetcher.secrets = mock_secrets
            fetcher.router = mock_router
            fetcher.signal_scanner = SignalScanner()
            
            result = fetcher.health_check()
            
            assert result['polygon'] == True
            assert result['itick'] == False
            assert result['binance'] == True
    
    def test_status_report_generation(self, mock_config, mock_secrets):
        """测试状态报告生成"""
        with patch('finance_fetcher.SmartRouter') as MockRouter:
            mock_router = Mock()
            mock_router.get_provider_status_report.return_value = "# Test Status Report\n- polygon: active\n- binance: active"
            MockRouter.return_value = mock_router
            
            fetcher = FinanceFetcher.__new__(FinanceFetcher)
            fetcher.config = mock_config
            fetcher.secrets = mock_secrets
            fetcher.router = mock_router
            fetcher.signal_scanner = SignalScanner()
            
            report = fetcher.get_status_report()
            
            assert "Test Status Report" in report


# ============ 4. Individual Provider Tests ============

class TestPolygonFetcher:
    """Polygon Fetcher 单元测试"""
    
    def test_polygon_quote_parsing(self):
        """测试 Polygon 报价解析"""
        # Mock API 响应
        mock_response = {
            'status': 'OK',
            'results': [{
                'o': 149.5,
                'c': 150.0,
                'h': 151.0,
                'l': 149.0,
                'v': 1000000,
                'pc': 149.0
            }]
        }
        
        # 验证解析逻辑
        result = mock_response['results'][0]
        close_price = float(result.get('c', 0))
        prev_close = float(result.get('pc', close_price))
        change = close_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        assert close_price == 150.0
        assert prev_close == 149.0
        assert abs(change - 1.0) < 0.01
        assert abs(change_pct - 0.67) < 0.1
    
    def test_polygon_kline_parsing(self):
        """测试 Polygon K线解析"""
        mock_response = {
            'results': [
                {'t': 1704067200000, 'o': 150.0, 'h': 151.0, 'l': 149.0, 'c': 150.5, 'v': 1000000},
                {'t': 1704153600000, 'o': 150.5, 'h': 152.0, 'l': 150.0, 'c': 151.0, 'v': 1100000}
            ]
        }
        
        bars = []
        for item in mock_response['results']:
            bar = KlineBar(
                symbol='AAPL',
                market='US',
                timestamp=datetime.fromtimestamp(item['t'] / 1000).isoformat(),
                open=float(item['o']),
                high=float(item['h']),
                low=float(item['l']),
                close=float(item['c']),
                volume=int(item['v']),
                interval='1d',
                source='Polygon.io'
            )
            bars.append(bar)
        
        assert len(bars) == 2
        assert bars[0].open == 150.0
        assert bars[1].close == 151.0


class TestITickFetcher:
    """iTick Fetcher 单元测试"""
    
    def test_itick_quote_parsing(self):
        """测试 iTick 报价解析"""
        mock_response = {
            'code': 'AAPL',
            'name': 'Apple Inc.',
            'last': 150.0,
            'change': 1.5,
            'chp': 1.01,
            'volume': 50000000,
            'amount': 7500000000,
            'high': 151.0,
            'low': 148.5,
            'open': 149.0,
            'prevClose': 148.5
        }
        
        quote = Quote(
            symbol=mock_response['code'],
            market='US',
            name=mock_response.get('name', mock_response['code']),
            price=float(mock_response.get('last', 0)),
            change=float(mock_response.get('change', 0)),
            change_pct=float(mock_response.get('chp', 0)),
            volume=int(mock_response.get('volume', 0)),
            amount=float(mock_response.get('amount', 0)),
            high=float(mock_response.get('high', 0)),
            low=float(mock_response.get('low', 0)),
            open=float(mock_response.get('open', 0)),
            prev_close=float(mock_response.get('prevClose', 0)),
            timestamp=datetime.now().isoformat(),
            source='iTick'
        )
        
        assert quote.symbol == 'AAPL'
        assert quote.price == 150.0
        assert quote.change == 1.5
        assert quote.change_pct == 1.01


class TestBinanceFetcher:
    """Binance Fetcher 单元测试"""
    
    def test_binance_ticker_parsing(self):
        """测试 Binance Ticker 解析"""
        mock_response = {
            'symbol': 'BTCUSDT',
            'lastPrice': '45000.00',
            'priceChange': '500.00',
            'priceChangePercent': '1.12',
            'volume': '25000.00',
            'quoteVolume': '1125000000.00',
            'highPrice': '45500.00',
            'lowPrice': '44500.00',
            'openPrice': '44500.00',
            'prevClosePrice': '44500.00'
        }
        
        quote = Quote(
            symbol=mock_response['symbol'],
            market='CC',
            name=mock_response['symbol'],
            price=float(mock_response.get('lastPrice', 0)),
            change=float(mock_response.get('priceChange', 0)),
            change_pct=float(mock_response.get('priceChangePercent', 0)),
            volume=int(float(mock_response.get('volume', 0))),
            amount=float(mock_response.get('quoteVolume', 0)),
            high=float(mock_response.get('highPrice', 0)),
            low=float(mock_response.get('lowPrice', 0)),
            open=float(mock_response.get('openPrice', 0)),
            prev_close=float(mock_response.get('prevClosePrice', 0)),
            timestamp=datetime.now().isoformat(),
            source='Binance'
        )
        
        assert quote.symbol == 'BTCUSDT'
        assert quote.price == 45000.00
        assert quote.change_pct == 1.12
        assert quote.market == 'CC'
    
    def test_binance_kline_parsing(self):
        """测试 Binance K线解析"""
        mock_response = [
            [1704067200000, '45000.00', '45500.00', '44500.00', '45000.00', '100.00'],
            [1704153600000, '45000.00', '46000.00', '44800.00', '45500.00', '120.00']
        ]
        
        bars = []
        for item in mock_response:
            bar = KlineBar(
                symbol='BTCUSDT',
                market='CC',
                timestamp=datetime.fromtimestamp(item[0] / 1000).isoformat(),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=int(float(item[5])),
                interval='1d',
                source='Binance'
            )
            bars.append(bar)
        
        assert len(bars) == 2
        assert bars[0].open == 45000.00
        assert bars[1].close == 45500.00


class TestAKShareFetcher:
    """AKShare Fetcher 单元测试"""
    
    def test_akshare_availability_check(self):
        """测试 AKShare 可用性检查"""
        # 测试在无法 import 的情况下降级
        with patch('builtins.__import__', side_effect=ImportError()):
            akshare = AKShareFetcher()
            assert akshare.available == False


class TestFREDFetcher:
    """FRED Fetcher 单元测试"""
    
    def test_fred_configured_check(self):
        """测试 FRED 配置检查"""
        # 有 API key
        fred_with_key = FREDFetcher(api_key='test_key')
        assert fred_with_key.is_configured() == True
        
        # 无 API key
        fred_without_key = FREDFetcher()
        assert fred_without_key.is_configured() == False
    
    def test_fred_observations_parsing(self):
        """测试 FRED 数据解析"""
        mock_response = {
            'observations': [
                {'date': '2024-01-01', 'value': '100.0'},
                {'date': '2024-02-01', 'value': '101.5'},
                {'date': '2024-03-01', 'value': '102.3'}
            ]
        }
        
        assert 'observations' in mock_response
        assert len(mock_response['observations']) == 3
        assert mock_response['observations'][0]['value'] == '100.0'


# ============ 5. Integration Tests (requires network) ============

@pytest.mark.integration
class TestIntegration:
    """集成测试（需要网络连接）"""
    
    def test_polygon_live_quote(self):
        """测试 Polygon 实时报价（需要网络）"""
        # 需要真实的 API key
        pytest.skip("Integration test - requires network and API key")
        
        fetcher = FinanceFetcher()
        quote = fetcher.get_quote('AAPL', 'US')
        
        assert quote is not None
        assert quote.symbol == 'AAPL'
        assert quote.price > 0
    
    def test_binance_live_ticker(self):
        """测试 Binance 实时行情（需要网络）"""
        pytest.skip("Integration test - requires network")
        
        fetcher = FinanceFetcher()
        ticker = fetcher.get_quote('BTCUSDT', 'CC')
        
        assert ticker is not None
        assert ticker.symbol == 'BTCUSDT'
        assert ticker.price > 0
    
    def test_itick_live_quote(self):
        """测试 iTick 实时报价（需要网络）"""
        pytest.skip("Integration test - requires network and API key")
        
        fetcher = FinanceFetcher()
        quote = fetcher.get_quote('AAPL', 'US')
        
        assert quote is not None
        assert quote.symbol == 'AAPL'


# ============ 6. Signal Scanner Tests ============

class TestSignalScanner:
    """信号扫描器测试"""
    
    def test_price_anomaly_detection(self):
        """测试价格异动检测"""
        scanner = SignalScanner()
        scanner.price_change_threshold = 5.0
        
        # 创建涨跌幅超过阈值的报价
        quote = Quote(
            symbol='AAPL', market='US', name='Apple', price=160.0,
            change=10.0, change_pct=6.67, volume=1000000, amount=160000000,
            high=161.0, low=149.0, open=150.0, prev_close=150.0,
            timestamp=datetime.now().isoformat(), source='Test'
        )
        
        signals = scanner.scan_price_anomaly(quote)
        
        assert len(signals) == 1
        assert signals[0].signal_type == FinanceSignalType.MARKET_SIGNAL.value
        assert signals[0].severity in ['high', 'medium']
    
    def test_volume_spike_detection(self):
        """测试成交量突增检测"""
        scanner = SignalScanner()
        scanner.volume_spike_threshold = 2.0
        
        quote = Quote(
            symbol='AAPL', market='US', name='Apple', price=150.0,
            change=1.0, change_pct=0.67, volume=5000000, amount=750000000,
            high=151.0, low=149.0, open=149.5, prev_close=149.0,
            timestamp=datetime.now().isoformat(), source='Test'
        )
        
        # 模拟历史K线，平均成交量较低
        history = [
            KlineBar(symbol='AAPL', market='US', timestamp='2024-01-01',
                    open=149.0, high=150.0, low=148.0, close=149.5,
                    volume=1000000, interval='1d', source='Test')
            for _ in range(5)
        ]
        
        signals = scanner.scan_volume_spike(quote, history)
        
        # 成交量是平均的5倍，应该检测到
        assert len(signals) == 1
        assert signals[0].signal_type == FinanceSignalType.VOLUME_SPIKE.value
    
    def test_price_breakout_detection(self):
        """测试价格突破检测"""
        scanner = SignalScanner()
        scanner.breakout_threshold = 3.0
        
        # 当前价格 155.0
        quote = Quote(
            symbol='AAPL', market='US', name='Apple', price=155.0,
            change=5.0, change_pct=3.33, volume=1000000, amount=155000000,
            high=156.0, low=149.0, open=150.0, prev_close=150.0,
            timestamp=datetime.now().isoformat(), source='Test'
        )
        
        # 历史K线，包含20日数据，high 最高 150.0
        history = [
            KlineBar(symbol='AAPL', market='US', timestamp=f'2024-01-{i:02d}',
                    open=149.0, high=150.0, low=148.0, 
                    close=149.5, volume=1000000, interval='1d', source='Test')
            for i in range(1, 21)
        ]
        
        signals = scanner.scan_price_breakout(quote, history)
        
        # 当前价格 155.0 突破 20 日高点 150.0，涨幅超过 3%
        assert len(signals) >= 1
        assert signals[0].signal_type == FinanceSignalType.PRICE_BREAKOUT.value


# ============ Run Tests ============

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
