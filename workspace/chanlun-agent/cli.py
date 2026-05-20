#!/usr/bin/env python3
"""
ChanlunAgent CLI - OpenClaw Skill 接口

用法:
    python3 cli.py <command> [args]

命令:
    持仓        查询当前持仓
    分析 [品种]  缠论分析
    信号        查看最近信号
    平仓 [品种]  平仓操作
    反思        生成反思
    日报        生成日报
    状态        系统状态
    帮助        显示帮助
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ChanlunAgent import ChanlunAgent, load_config


def main():
    if len(sys.argv) < 2:
        print("用法: python3 cli.py <command> [args]")
        print("命令: 持仓/分析/信号/平仓/反思/日报/状态/帮助")
        sys.exit(1)

    command = sys.argv[1]
    args = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    try:
        config = load_config()
        agent = ChanlunAgent(config)
        result = agent.handle_command(command, args)
        print(result)
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
