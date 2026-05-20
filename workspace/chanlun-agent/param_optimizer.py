#!/usr/bin/env python3
"""
ParamOptimizer - 参数自动优化引擎

功能：
1. 定义参数搜索空间
2. 网格搜索参数组合
3. 回测评分（胜率/盈亏比/最大回撤/夏普）
4. 输出最优参数组合

Author: Trading Assistant
Version: 1.0.0
"""

import json
import logging
import itertools
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("ParamOptimizer")

PROJECT_DIR = Path(__file__).parent
REPORTS_DIR = PROJECT_DIR / "reports" / "optimization"


@dataclass
class ParamSpace:
    """参数搜索空间"""
    # czsc 扩展层参数
    divergence_threshold: List[float] = field(default_factory=lambda: [0.7, 0.8, 0.9])
    like_second_buy_zs_tolerance: List[float] = field(default_factory=lambda: [0.01, 0.02, 0.03])
    shock_point_zs_tolerance: List[float] = field(default_factory=lambda: [0.02, 0.03, 0.05])
    volume_filter_ratio: List[float] = field(default_factory=lambda: [1.2, 1.5, 2.0])

    # 风控参数
    stop_loss_pct: List[float] = field(default_factory=lambda: [0.02, 0.03, 0.05])
    time_stop_bars: List[int] = field(default_factory=lambda: [8, 12, 20])
    max_single_loss_pct: List[float] = field(default_factory=lambda: [0.02, 0.03, 0.05])
    max_daily_loss_pct: List[float] = field(default_factory=lambda: [0.06, 0.08, 0.10])
    consecutive_loss_limit: List[int] = field(default_factory=lambda: [2, 3, 5])

    # 信号过滤
    min_signal_strength: List[float] = field(default_factory=lambda: [0.3, 0.5, 0.7])
    resonance_required: List[int] = field(default_factory=lambda: [1, 2, 3])

    def to_dict(self) -> Dict:
        return asdict(self)

    def get_combinations(self) -> List[Dict]:
        """生成所有参数组合"""
        keys = list(self.to_dict().keys())
        values = [getattr(self, k) for k in keys]
        combos = []
        for combo in itertools.product(*values):
            combos.append(dict(zip(keys, combo)))
        return combos


@dataclass
class OptimizationResult:
    """单次优化结果"""
    params: Dict
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    avg_pnl: float
    total_pnl: float
    score: float  # 综合评分

    def to_dict(self) -> Dict:
        return asdict(self)


class ParamOptimizer:
    """参数自动优化引擎"""

    def __init__(self, param_space: Optional[ParamSpace] = None):
        self.param_space = param_space or ParamSpace()
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def optimize(self, symbol: str, bars_list: list,
                 max_combos: int = 100) -> Dict:
        """
        运行参数优化

        Args:
            symbol: 品种代码
            bars_list: RawBar 列表
            max_combos: 最大测试组合数

        Returns:
            {best_params, best_score, all_results, summary}
        """
        from backtest_engine import BacktestEngine

        combos = self.param_space.get_combinations()
        if len(combos) > max_combos:
            # 随机采样
            import random
            random.seed(42)
            combos = random.sample(combos, max_combos)

        logger.info(f"🔍 开始参数优化: {symbol} | {len(combos)} 个组合")

        results = []
        for i, params in enumerate(combos):
            if (i + 1) % 10 == 0:
                logger.info(f"  进度: {i+1}/{len(combos)}")

            # 运行回测
            engine = BacktestEngine(
                initial_capital=10000,
                risk_per_trade=params.get('max_single_loss_pct', 0.03)
            )

            try:
                result = engine.run_backtest(symbol, bars_list)
                score = self._calculate_score(result, params)

                opt_result = OptimizationResult(
                    params=params,
                    total_trades=result.total_trades,
                    win_rate=result.win_rate,
                    profit_factor=result.profit_factor,
                    max_drawdown=result.max_drawdown,
                    sharpe_ratio=getattr(result, 'sharpe_ratio', 0),
                    avg_pnl=(result.avg_win + result.avg_loss) / 2 if result.avg_win else 0,
                    total_pnl=result.final_capital - result.initial_capital,
                    score=score,
                )
                results.append(opt_result)
            except Exception as e:
                logger.warning(f"  组合 {i+1} 失败: {e}")
                continue

        if not results:
            return {'error': '所有参数组合都失败了'}

        # 排序
        results.sort(key=lambda r: r.score, reverse=True)

        # 保存报告
        report = self._generate_report(symbol, results)
        report_path = REPORTS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{symbol}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

        return {
            'best_params': results[0].params,
            'best_score': results[0].score,
            'best_result': results[0].to_dict(),
            'top_5': [r.to_dict() for r in results[:5]],
            'total_tested': len(results),
            'report_path': str(report_path),
            'summary': self._generate_summary(results),
        }

    def _calculate_score(self, result, params: Dict) -> float:
        """
        计算综合评分

        评分公式:
        score = (win_rate × 0.3 + profit_factor × 0.3 + sharpe × 0.2 + (1-max_dd) × 0.2)
                × trade_count_factor
        """
        # 基础指标
        win_rate = result.win_rate
        pf = min(result.profit_factor, 5.0) / 5.0  # 归一化到 0-1
        sharpe = min(getattr(result, 'sharpe_ratio', 0), 3.0) / 3.0  # 归一化
        dd_penalty = 1 - result.max_drawdown  # 回撤越小越好

        # 交易次数因子（太少不可靠，太多成本高）
        trade_count = result.total_trades
        if trade_count < 3:
            tc_factor = 0.3  # 太少
        elif trade_count < 10:
            tc_factor = 0.7
        elif trade_count <= 50:
            tc_factor = 1.0
        else:
            tc_factor = 0.9  # 太多

        # 加权评分
        score = (
            win_rate * 0.3 +
            pf * 0.3 +
            sharpe * 0.2 +
            dd_penalty * 0.2
        ) * tc_factor

        # 额外惩罚
        if result.max_drawdown > 0.20:  # 回撤超20%
            score *= 0.5
        if result.total_trades > 0 and result.win_rate < 0.3:  # 胜率低于30%
            score *= 0.7

        return round(score, 4)

    def _generate_report(self, symbol: str, results: List[OptimizationResult]) -> Dict:
        """生成优化报告"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'total_tested': len(results),
            'best': results[0].to_dict() if results else None,
            'top_10': [r.to_dict() for r in results[:10]],
            'param_space': self.param_space.to_dict(),
            'statistics': {
                'avg_score': sum(r.score for r in results) / len(results) if results else 0,
                'avg_win_rate': sum(r.win_rate for r in results) / len(results) if results else 0,
                'avg_pf': sum(r.profit_factor for r in results) / len(results) if results else 0,
                'best_score': results[0].score if results else 0,
                'worst_score': results[-1].score if results else 0,
            }
        }

    def _generate_summary(self, results: List[OptimizationResult]) -> str:
        """生成优化摘要"""
        if not results:
            return "❌ 无有效结果"

        best = results[0]
        avg_score = sum(r.score for r in results) / len(results)

        return f"""📊 参数优化完成

测试组合: {len(results)}个
最优评分: {best.score:.4f}
平均评分: {avg_score:.4f}

最优参数:
{json.dumps(best.params, indent=2, ensure_ascii=False)}

最优表现:
  交易次数: {best.total_trades}
  胜率: {best.win_rate*100:.1f}%
  盈利因子: {best.profit_factor:.2f}
  最大回撤: {best.max_drawdown*100:.2f}%
  总盈亏: ${best.total_pnl:.2f}

{'🟢 优秀' if best.score > 0.7 else '🟡 合格' if best.score > 0.5 else '🔴 需改进'}
"""


# ==================== CLI ====================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(PROJECT_DIR / "data"))
    from czsc import RawBar, Freq
    import numpy as np
    import pandas as pd

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    # 生成测试数据
    np.random.seed(42)
    n = 300
    dates = pd.date_range('2025-01-01', periods=n, freq='D')
    trend = np.sin(np.arange(n) / 30) * 15
    noise = np.cumsum(np.random.randn(n) * 1.5)
    close = 100 + trend + noise
    high = close + np.abs(np.random.randn(n)) * 1.5
    low = close - np.abs(np.random.randn(n)) * 1.5
    open_ = close + np.random.randn(n) * 0.5
    vol = (5000 + np.abs(noise) * 200 + np.random.randint(0, 3000, n)).astype(int)

    bars = [RawBar(symbol='TEST', dt=dates[i], freq=Freq.D,
        open=float(open_[i]), high=float(high[i]),
        low=float(low[i]), close=float(close[i]),
        vol=float(vol[i]), amount=float(vol[i]*close[i])) for i in range(n)]

    # 缩小搜索空间用于测试
    space = ParamSpace(
        divergence_threshold=[0.7, 0.8],
        stop_loss_pct=[0.02, 0.03],
        min_signal_strength=[0.3, 0.5],
    )

    optimizer = ParamOptimizer(space)
    result = optimizer.optimize('TEST', bars, max_combos=20)

    print(result.get('summary', '无结果'))
