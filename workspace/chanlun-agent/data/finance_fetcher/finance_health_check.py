#!/usr/bin/env python3
"""
金融数据源健康巡检脚本

功能：
- 检查所有已注册数据源的健康状态
- 生成 Markdown 格式的健康报告
- 更新 sources_config.json 的 quality_metrics
- 支持定时任务调用

使用方式：
    python finance_health_check.py                     # 直接运行
    python finance_health_check.py --output report.md  # 保存报告到文件
    python finance_health_check.py --config custom.json # 使用自定义配置

定时任务配置示例（crontab）：
    # 每小时运行一次健康巡检
    0 * * * * cd /path/to/skills/global-info-fetcher && python finance_health_check.py --output /var/log/finance_health_$(date +\%Y\%m\%d\%H).md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FinanceHealthCheck")


def load_json_file(path: Path) -> Optional[Dict]:
    """加载 JSON 文件"""
    try:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {path}: {e}")
    return None


def save_json_file(path: Path, data: Dict) -> bool:
    """保存 JSON 文件"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save {path}: {e}")
        return False


def generate_markdown_report(health_data: Dict, status_report: str) -> str:
    """生成 Markdown 格式的健康报告"""
    lines = [
        "# 金融数据源健康巡检报告",
        "",
        f"**巡检时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**数据源总数**: {len(health_data)}",
        ""
    ]
    
    # 统计概览
    stats = {
        'total': len(health_data),
        'healthy': 0,
        'degraded': 0,
        'unavailable': 0
    }
    
    for name, status in health_data.items():
        state = status.get('state', 'unknown')
        if state == 'active':
            stats['healthy'] += 1
        elif state == 'degraded':
            stats['degraded'] += 1
        else:
            stats['unavailable'] += 1
    
    lines.extend([
        "## 概览",
        "",
        f"- ✅ 正常: {stats['healthy']}",
        f"- ⚠️ 降级: {stats['degraded']}",
        f"- ❌ 不可用: {stats['unavailable']}",
        ""
    ])
    
    # 详细状态表
    lines.extend([
        "## 详细状态",
        "",
        "| 数据源 | 状态 | 健康分 | 成功率 | 延迟(ms) | 测试结果 |",
        "|------|------|--------|--------|----------|----------|"
    ])
    
    for name, status in sorted(health_data.items()):
        state = status.get('state', 'unknown')
        health_score = status.get('health_score', 0)
        success_rate = status.get('success_rate', 0)
        latency = status.get('latency_ms', 0)
        test_result = "✅" if status.get('test_success') else "❌"
        
        state_icon = {
            'active': '✅ 活跃',
            'degraded': '⚠️ 降级',
            'retired': '🚫 退休',
            'uninitialized': '⏳ 未初始化'
        }.get(state, state)
        
        lines.append(
            f"| {name} | {state_icon} | "
            f"{health_score:.2f} | {success_rate:.1%} | "
            f"{latency:.0f} | {test_result} |"
        )
    
    lines.extend(["", "---", ""])
    
    # 原始状态报告
    lines.extend([
        "## 完整状态报告",
        "",
        "```",
        status_report,
        "```"
    ])
    
    # 建议
    lines.extend(["", "---", ""])
    lines.extend([
        "## 建议",
        ""
    ])
    
    if stats['degraded'] > 0:
        lines.append(f"- 有 {stats['degraded']} 个数据源处于降级状态，建议检查网络连接或 API 配额")
    
    if stats['unavailable'] > 0:
        lines.append(f"- 有 {stats['unavailable']} 个数据源不可用，请检查配置或 API Key")
    
    if stats['healthy'] == stats['total']:
        lines.append("- 所有数据源状态正常 ✅")
    
    return '\n'.join(lines)


def update_source_metrics(config: Dict, provider_name: str, status: Dict) -> Dict:
    """更新 sources_config.json 中的 quality_metrics"""
    # 映射 provider 名称到 config 中的 source 名称
    source_mapping = {
        'polygon': 'itick_stock',  # 使用已有的配置条目
        'itick': 'itick_stock',
        'binance': 'binance',
        'akshare': 'akshare',
        'fred': 'fred'  # 需要在 config 中添加
    }
    
    config_key = source_mapping.get(provider_name, provider_name)
    
    if 'sources' in config and config_key in config['sources']:
        source = config['sources'][config_key]
        
        # 更新 quality_metrics
        source['quality_metrics'] = {
            'success_rate': status.get('success_rate', 0),
            'avg_response_time_ms': status.get('latency_ms', 0),
            'health_score': status.get('health_score', 0)
        }
        
        # 更新状态
        state = status.get('state', 'unknown')
        source['status'] = 'active' if state == 'active' else 'degraded' if state == 'degraded' else 'inactive'
        source['last_evaluated'] = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Updated metrics for {config_key}")
    
    return config


def run_health_check(config_path: str = "./skills/global-info-fetcher/sources_config.json",
                     secret_path: str = "./SECRET.md",
                     output_path: str = None,
                     update_config: bool = False) -> str:
    """
    运行健康巡检
    
    Args:
        config_path: 数据源配置文件路径
        secret_path: 密钥文件路径
        output_path: 输出报告路径（可选）
        update_config: 是否更新 config 文件
        
    Returns:
        str: 健康报告内容
    """
    logger.info("Starting health check...")
    
    # 导入 Finance Fetcher
    sys.path.insert(0, str(Path(__file__).parent))
    from finance_fetcher import FinanceFetcher
    
    # 创建 FinanceFetcher 实例
    config_file = Path(config_path)
    secret_file = Path(secret_path)
    
    # 加载现有配置
    config = load_json_file(config_file) or {}
    
    # 运行健康检查
    fetcher = FinanceFetcher(config_path=config_path, secret_path=secret_path)
    
    # 获取健康数据
    health = fetcher.health_check()
    status_report = fetcher.get_status_report()
    
    # 转换为详细格式
    detailed_health = fetcher.router.health_check()
    
    # 生成报告
    report = generate_markdown_report(detailed_health, status_report)
    
    # 保存报告
    if output_path:
        output_file = Path(output_path)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Report saved to {output_path}")
    
    # 更新配置文件
    if update_config:
        for provider_name, status in detailed_health.items():
            config = update_source_metrics(config, provider_name, status)
        
        if save_json_file(config_file, config):
            logger.info(f"Updated {config_path}")
    
    return report


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description='金融数据源健康巡检工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python finance_health_check.py
  python finance_health_check.py --output report.md
  python finance_health_check.py --update-config
  python finance_health_check.py --config ./my_config.json --output ./reports/health.md

定时任务配置:
  # 每小时运行
  0 * * * * python /path/to/finance_health_check.py --output /var/log/health_$(date +\%Y\%m\%d\%H).md
  
  # 每天早上9点运行并更新配置
  0 9 * * * python /path/to/finance_health_check.py --update-config
"""
    )
    
    parser.add_argument('--config', default='./skills/global-info-fetcher/sources_config.json',
                        help='数据源配置文件路径 (默认: ./skills/global-info-fetcher/sources_config.json)')
    parser.add_argument('--secret', default='./SECRET.md',
                        help='密钥文件路径 (默认: ./SECRET.md)')
    parser.add_argument('--output', '-o',
                        help='输出报告路径 (可选，不指定则只打印到stdout)')
    parser.add_argument('--update-config', '-u', action='store_true',
                        help='更新 sources_config.json 的 quality_metrics')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        report = run_health_check(
            config_path=args.config,
            secret_path=args.secret,
            output_path=args.output,
            update_config=args.update_config
        )
        
        # 打印报告到 stdout
        print(report)
        
        logger.info("Health check completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
