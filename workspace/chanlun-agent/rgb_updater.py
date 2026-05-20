#!/usr/bin/env python3
"""
RGB Knowledge Updater - RGB 知识库自动更新引擎

功能：
1. 交易反思 → 自动提取规则/指南/最佳实践
2. 连续模式识别 → 生成新规则
3. 失败案例 → 生成风险提示
4. 成功案例 → 强化有效模式
5. 反思记录 → 自动写入 B-practices

Author: Trading Assistant
Version: 1.0.0
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("RGBUpdater")

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


class RGBUpdater:
    """RGB 知识库自动更新"""

    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir
        self.r_dir = knowledge_dir / "R-rules"
        self.g_dir = knowledge_dir / "G-guides"
        self.b_dir = knowledge_dir / "B-practices"
        self._ensure_dirs()

        # 模式计数器
        self._pattern_stats = {}

    def _ensure_dirs(self):
        for d in [self.r_dir, self.g_dir, self.b_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # ==================== B-最佳实践：交易反思写入 ====================

    def record_trade_reflection(self, trade: Dict, analysis: Dict,
                                 reflection: str = "") -> str:
        """
        记录交易反思到 B-practices

        Args:
            trade: 交易记录 {symbol, direction, entry_price, exit_price, pnl, pnl_pct, reason}
            analysis: 分析结果
            reflection: 反思文本（可选，为空则自动生成）

        Returns:
            写入的文件路径
        """
        symbol = trade.get('symbol', 'N/A')
        direction = trade.get('direction', 'N/A')
        entry = trade.get('entry_price', 0)
        exit_ = trade.get('exit_price', 0)
        pnl = trade.get('pnl', 0)
        pnl_pct = trade.get('pnl_pct', 0)
        reason = trade.get('reason', 'N/A')
        is_win = pnl > 0

        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}_{symbol}_{direction}_{('win' if is_win else 'loss')}.md"
        filepath = self.b_dir / filename

        # 自动生成反思
        if not reflection:
            reflection = self._auto_reflect(trade, analysis)

        content = f"""# {date_str} {symbol} {direction.upper()} {'盈利' if is_win else '亏损'} {pnl_pct:+.2f}%

## 交易记录
- 入场: ${entry:.2f} → 出场: ${exit_:.2f}
- 盈亏: ${pnl:.2f} ({pnl_pct:+.2f}%)
- 信号来源: {reason}

## 反思
{reflection}

## 学到的经验
{self._extract_lessons(trade, analysis)}

---
*自动记录 by RGBUpdater*
"""
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"✅ 反思已记录: {filepath.name}")

        # 更新模式统计
        self._update_pattern_stats(trade, analysis)

        # 检查是否需要生成新规则
        self._check_rule_generation()

        return str(filepath)

    def _auto_reflect(self, trade: Dict, analysis: Dict) -> str:
        """自动生成反思"""
        pnl = trade.get('pnl', 0)
        reason = trade.get('reason', '')
        signal_type = trade.get('signal_type', '')

        if pnl > 0:
            return f"""### 盈利归因
- 信号类型: {signal_type}
- 市场结构判断准确，{reason}
- 执行纪律良好，按计划止损/止盈

### 优化空间
- 止盈设置是否过早？检查是否错过更多利润
- 仓位是否可以更大？信号强度是否支持加仓"""
        else:
            return f"""### 亏损归因
- 信号类型: {signal_type}
- {reason}
- 需要检查：是信号质量问题还是市场环境变化？

### 改进措施
- 止损设置是否合理？
- 信号过滤是否需要加强？
- 入场时机是否需要等待更多确认？"""

    def _extract_lessons(self, trade: Dict, analysis: Dict) -> str:
        """提取教训"""
        pnl = trade.get('pnl', 0)
        signal_type = trade.get('signal_type', '')

        lessons = []

        if pnl > 0:
            lessons.append(f"- ✅ {signal_type} 信号在当前环境下有效")
            lessons.append("- ✅ 风险控制到位，止损/止盈按计划执行")
        else:
            lessons.append(f"- ❌ {signal_type} 信号在此环境下失败，需加强过滤条件")
            lessons.append("- ❌ 可能需要更多级别确认")

        # 检查是否有特殊形态
        special_forms = analysis.get('czsc', {}).get('results', {})
        for tf, data in special_forms.items():
            for form in data.get('special_forms', []):
                lessons.append(f"- 📐 {tf}: {form['description']} → {form['implication']}")

        return '\n'.join(lessons) if lessons else "- 无特殊教训"

    # ==================== 模式统计与规则生成 ====================

    def _update_pattern_stats(self, trade: Dict, analysis: Dict):
        """更新模式统计"""
        signal_type = trade.get('signal_type', 'unknown')
        is_win = trade.get('pnl', 0) > 0

        if signal_type not in self._pattern_stats:
            self._pattern_stats[signal_type] = {'wins': 0, 'losses': 0, 'total_pnl': 0}

        stats = self._pattern_stats[signal_type]
        if is_win:
            stats['wins'] += 1
        else:
            stats['losses'] += 1
        stats['total_pnl'] += trade.get('pnl', 0)

    def _check_rule_generation(self):
        """检查是否需要生成新规则"""
        for signal_type, stats in self._pattern_stats.items():
            total = stats['wins'] + stats['losses']
            if total >= 5:  # 至少5次交易样本
                win_rate = stats['wins'] / total
                if win_rate >= 0.7:
                    self._generate_positive_rule(signal_type, stats)
                elif win_rate <= 0.3:
                    self._generate_warning_rule(signal_type, stats)

    def _generate_positive_rule(self, signal_type: str, stats: Dict):
        """生成正面规则"""
        win_rate = stats['wins'] / (stats['wins'] + stats['losses'])
        rule_content = f"""# {signal_type} 有效性规则

> **自动生成:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **样本数:** {stats['wins'] + stats['losses']}笔 | **胜率:** {win_rate:.0%}
> **累计盈亏:** ${stats['total_pnl']:.2f}

## 结论
{signal_type} 信号在当前市场环境下有效（胜率 {win_rate:.0%}）

## 建议
- 可适当增加此信号的仓位权重
- 保持当前过滤条件
- 继续跟踪表现

---
*自动生成 by RGBUpdater*
"""
        filepath = self.r_dir / f"{signal_type}_effective.md"
        filepath.write_text(rule_content, encoding='utf-8')
        logger.info(f"📈 正面规则已生成: {filepath.name}")

    def _generate_warning_rule(self, signal_type: str, stats: Dict):
        """生成风险提示规则"""
        win_rate = stats['wins'] / (stats['wins'] + stats['losses'])
        rule_content = f"""# {signal_type} 风险提示

> **自动生成:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **样本数:** {stats['wins'] + stats['losses']}笔 | **胜率:** {win_rate:.0%}
> **累计盈亏:** ${stats['total_pnl']:.2f}

## 警告
{signal_type} 信号在当前市场环境下表现不佳（胜率仅 {win_rate:.0%}）

## 建议
- 降低此信号的仓位权重
- 增加更多确认条件（成交量、多级别共振）
- 考虑暂停使用此信号，直到市场环境变化

---
*自动生成 by RGBUpdater*
"""
        filepath = self.r_dir / f"{signal_type}_warning.md"
        filepath.write_text(rule_content, encoding='utf-8')
        logger.warning(f"⚠️ 风险提示已生成: {filepath.name}")

    # ==================== G-指南更新 ====================

    def update_signal_sop(self, signal_type: str, improvement: str):
        """
        更新信号执行 SOP

        Args:
            signal_type: 信号类型
            improvement: 改进建议
        """
        sop_file = self.g_dir / "signal_sop.md"
        if not sop_file.exists():
            return

        content = sop_file.read_text(encoding='utf-8')
        append_text = f"\n\n### {signal_type} 改进 ({datetime.now().strftime('%Y-%m-%d')})\n{improvement}\n"
        sop_file.write_text(content + append_text, encoding='utf-8')
        logger.info(f"📋 SOP 已更新: {signal_type}")

    # ==================== 统计查询 ====================

    def get_stats(self) -> Dict:
        """获取知识库统计"""
        stats = {
            'rules': len(list(self.r_dir.glob('*.md'))),
            'guides': len(list(self.g_dir.glob('*.md'))),
            'practices': len(list(self.b_dir.glob('*.md'))),
            'pattern_stats': self._pattern_stats,
        }
        return stats

    def get_reflection_history(self, limit: int = 10) -> List[Dict]:
        """获取最近的反思记录"""
        files = sorted(self.b_dir.glob('*.md'), reverse=True)[:limit]
        history = []
        for f in files:
            history.append({
                'file': f.name,
                'date': f.stem[:10],
                'content': f.read_text(encoding='utf-500'),
            })
        return history


# ==================== CLI 测试 ====================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    updater = RGBUpdater()

    # 测试：模拟记录一次亏损交易
    trade = {
        'symbol': 'CRCL',
        'direction': 'long',
        'entry_price': 111.03,
        'exit_price': 108.50,
        'pnl': -253.0,
        'pnl_pct': -2.28,
        'reason': '底背驰信号触发，但市场继续下跌',
        'signal_type': 'bottom_divergence',
    }

    analysis = {
        'czsc': {
            'results': {
                'daily': {
                    'special_forms': [
                        {'type': 'triangle_converge', 'description': '三角形收敛', 'implication': '变盘在即'},
                    ]
                }
            }
        }
    }

    # 记录反思
    path = updater.record_trade_reflection(trade, analysis)
    print(f"反思已写入: {path}")

    # 获取统计
    stats = updater.get_stats()
    print(f"\n知识库统计:")
    print(f"  R-规则: {stats['rules']}个")
    print(f"  G-指南: {stats['guides']}个")
    print(f"  B-实践: {stats['practices']}个")
