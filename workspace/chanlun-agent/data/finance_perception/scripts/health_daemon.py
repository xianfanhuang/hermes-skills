#!/usr/bin/env python3
"""
Finance Perception Skill - Health Daemon
金融数据源健康巡检脚本，供 Calendar/Cron 定时调用

Usage:
    # 基本用法（使用默认配置路径）
    python health_daemon.py
    
    # 指定配置文件路径
    python health_daemon.py ./skills/global-info-fetcher/sources_config.json
    
    # 指定密钥文件路径
    python health_daemon.py ./skills/global-info-fetcher/sources_config.json ./SECRET.md
    
    # 仅输出JSON格式
    python health_daemon.py --json
    
    # 静默模式（仅返回退出码）
    python health_daemon.py --quiet
    
    # 详细输出
    python health_daemon.py --verbose

Crontab 配置示例:
    # 每15分钟检查一次
    */15 * * * * cd /path/to/project && python skills/finance-perception/scripts/health_daemon.py >> /var/log/finance_health.log 2>&1
    
    # 每天早上9点生成报告
    0 9 * * * cd /path/to/project && python skills/finance-perception/scripts/health_daemon.py --report >> ~/finance_daily_report.txt

Exit Codes:
    0 - 所有数据源正常
    1 - 存在不健康的数据源
    2 - 检查执行失败
"""

import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional

# 添加模块路径
sys.path.insert(0, '../global-info-fetcher')

try:
    from finance_fetcher import FinanceFetcher
except ImportError as e:
    print(f"❌ 导入失败: {e}", file=sys.stderr)
    print("请确保 finance_fetcher.py 在 ../global-info-fetcher/ 目录", file=sys.stderr)
    sys.exit(2)


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="金融数据源健康巡检",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python health_daemon.py                       # 基本检查
  python health_daemon.py --json               # JSON格式输出
  python health_daemon.py --quiet               # 静默模式
  python health_daemon.py --verbose             # 详细输出
  python health_daemon.py --report              # 生成完整报告
        """
    )
    
    parser.add_argument(
        'config_path',
        nargs='?',
        default='../global-info-fetcher/sources_config.json',
        help='数据源配置文件路径 (默认: ../global-info-fetcher/sources_config.json)'
    )
    
    parser.add_argument(
        'secret_path',
        nargs='?',
        default='../../SECRET.md',
        help='密钥文件路径 (默认: ../../SECRET.md)'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='输出JSON格式结果'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='静默模式，仅返回退出码'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细输出模式'
    )
    
    parser.add_argument(
        '--report',
        action='store_true',
        help='生成完整状态报告'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='将报告输出到指定文件'
    )
    
    return parser


def check_sources(fetcher: FinanceFetcher) -> Dict:
    """检查所有数据源状态"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "sources": {},
        "summary": {
            "total": 0,
            "healthy": 0,
            "unhealthy": 0
        }
    }
    
    # 获取健康状态
    health = fetcher.health_check()
    
    for source, status in health.items():
        results["sources"][source] = {
            "healthy": status,
            "message": "正常" if status else "不可用"
        }
        
        results["summary"]["total"] += 1
        if status:
            results["summary"]["healthy"] += 1
        else:
            results["summary"]["unhealthy"] += 1
    
    return results


def format_markdown_report(check_results: Dict, fetcher: FinanceFetcher) -> str:
    """格式化Markdown报告"""
    lines = []
    
    # 标题
    lines.append("# 📊 金融数据源健康巡检报告")
    lines.append("")
    lines.append(f"**检查时间**: {check_results['timestamp']}")
    lines.append("")
    
    # 摘要
    summary = check_results["summary"]
    lines.append("## 📈 摘要")
    lines.append("")
    lines.append(f"- **数据源总数**: {summary['total']}")
    lines.append(f"- **正常**: {summary['healthy']} ✅")
    lines.append(f"- **异常**: {summary['unhealthy']} ❌")
    lines.append("")
    
    # 详细状态
    lines.append("## 🔍 数据源状态")
    lines.append("")
    lines.append("| 数据源 | 状态 | 说明 |")
    lines.append("|--------|------|------|")
    
    for source, info in check_results["sources"].items():
        status_icon = "✅" if info["healthy"] else "❌"
        lines.append(f"| {source} | {status_icon} | {info['message']} |")
    
    lines.append("")
    
    # 详细报告（如果请求）
    lines.append("## 📋 详细状态报告")
    lines.append("")
    try:
        detailed_report = fetcher.get_status_report()
        lines.append(detailed_report)
    except Exception as e:
        lines.append(f"_无法获取详细报告: {e}_")
    
    # 建议
    lines.append("")
    lines.append("## 💡 建议")
    lines.append("")
    
    if summary["unhealthy"] > 0:
        unhealthy_sources = [
            s for s, info in check_results["sources"].items() 
            if not info["healthy"]
        ]
        lines.append(f"⚠️ 以下数据源不可用，请检查:")
        for source in unhealthy_sources:
            lines.append(f"   - {source}")
        lines.append("")
        lines.append("**可能的原因**:")
        lines.append("1. API Key 过期或无效")
        lines.append("2. 请求频率超出限制")
        lines.append("3. 网络连接问题")
        lines.append("4. 数据源服务端故障")
        lines.append("")
        lines.append("**建议操作**:")
        lines.append("1. 检查 SECRET.md 中的 API Key")
        lines.append("2. 等待限流恢复")
        lines.append("3. 查看数据源官方状态页面")
    else:
        lines.append("✅ 所有数据源运行正常")
        lines.append("")
        lines.append("**持续监控建议**:")
        lines.append("- 保持定期健康检查")
        lines.append("- 关注 API Key 过期时间")
        lines.append("- 监控响应时间变化")
    
    return "\n".join(lines)


def format_json_output(check_results: Dict, fetcher: FinanceFetcher) -> str:
    """格式化JSON输出"""
    # 添加详细状态
    try:
        status_report = fetcher.get_status_report()
        check_results["detailed_report"] = status_report
    except Exception:
        pass
    
    return json.dumps(check_results, indent=2, ensure_ascii=False)


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 初始化
    if not args.quiet:
        print("🔍 金融数据源健康巡检", file=sys.stderr)
        print(f"   配置: {args.config_path}", file=sys.stderr)
        print(f"   密钥: {args.secret_path}", file=sys.stderr)
    
    try:
        fetcher = FinanceFetcher(args.config_path, args.secret_path)
    except Exception as e:
        print(f"❌ 初始化失败: {e}", file=sys.stderr)
        sys.exit(2)
    
    # 执行检查
    try:
        check_results = check_sources(fetcher)
    except Exception as e:
        print(f"❌ 检查执行失败: {e}", file=sys.stderr)
        sys.exit(2)
    
    # 格式化输出
    if args.json:
        output = format_json_output(check_results, fetcher)
        print(output)
    elif args.report:
        output = format_markdown_report(check_results, fetcher)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            if not args.quiet:
                print(f"报告已保存到: {args.output}")
        else:
            print(output)
    else:
        # 默认简洁输出
        if args.verbose:
            output = format_markdown_report(check_results, fetcher)
            print(output)
        else:
            # 简洁输出
            print(f"\n检查时间: {check_results['timestamp']}")
            print(f"正常: {check_results['summary']['healthy']}/{check_results['summary']['total']}")
            
            unhealthy = [
                s for s, info in check_results['sources'].items()
                if not info['healthy']
            ]
            
            if unhealthy:
                print(f"⚠️ 不健康数据源: {', '.join(unhealthy)}")
    
    # 返回退出码
    if check_results['summary']['unhealthy'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
