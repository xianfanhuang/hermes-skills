#!/usr/bin/env python3
"""
Token Budget Patrol - 轻量巡检脚本
每日3次由Calendar任务调用，检查token消耗状态
不使用外部依赖，纯标准库

联动机制：
- 黄色预警 → 提醒归档
- 红色熔断 → 自动调用 session_manager checkpoint 强制刷新
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SKILL_DIR, "budget_state.json")
SESSION_MANAGER = os.path.join(SKILL_DIR, "..", "hermes-sync-core", "session_manager.py")
TZ = timezone(timedelta(hours=8))

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_update": "", "daily": {}, "alerts": [], "history": []}

def save_state(state):
    state["last_update"] = datetime.now(TZ).isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def check_archive_freshness(state):
    """检查最近归档时间，如果>2天未归档则预警"""
    last = state.get("daily", {}).get("last_archive_date", "")
    if last:
        try:
            last_dt = datetime.strptime(last, "%Y-%m-%d").replace(tzinfo=TZ)
            days_since = (datetime.now(TZ).replace(hour=0, minute=0, second=0) - last_dt).days
            if days_since > 2:
                return f"⚠️ 已{days_since}天未归档对话，上下文可能膨胀"
        except ValueError:
            pass
    return None

def check_budget_status(state):
    """综合判断预算状态"""
    daily = state.get("daily", {})
    rounds = daily.get("main_chat_rounds", 0)
    tool_calls = daily.get("tool_calls_estimated", 0)
    
    status = "green"
    alerts = []
    
    if rounds > 50:
        status = "red"
        alerts.append(f"🔴 对话{rounds}轮，超红色阈值50，必须归档")
    elif rounds > 30:
        status = "yellow"
        alerts.append(f"🟡 对话{rounds}轮，接近阈值")
    
    if tool_calls > 100:
        status = "red" if status != "red" else status
        alerts.append(f"🔴 今日工具调用{tool_calls}次，超红色阈值")
    elif tool_calls > 50:
        if status == "green":
            status = "yellow"
        alerts.append(f"🟡 今日工具调用{tool_calls}次，偏高")
    
    archive_alert = check_archive_freshness(state)
    if archive_alert:
        alerts.append(archive_alert)
        if status == "green":
            status = "yellow"
    
    return status, alerts

def trigger_session_checkpoint(status: str, rounds: int):
    """
    联动 session_manager：根据状态触发归档
    
    红色 → 强制刷新所有活跃会话的缓冲区
    黄色 → 仅提醒，不强制
    """
    if not os.path.exists(SESSION_MANAGER):
        return
    
    try:
        result = subprocess.run(
            [sys.executable, SESSION_MANAGER, "checkpoint", str(rounds)],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            print(f"[session联动] {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"[session联动] {result.stderr.strip()}")
    except Exception as e:
        print(f"[session联动] 调用失败: {e}")


def main():
    state = load_state()
    status, alerts = check_budget_status(state)
    daily = state.get("daily", {})
    rounds = daily.get("main_chat_rounds", 0)
    
    # 更新状态
    state["daily"]["budget_status"] = status
    
    if alerts:
        state["alerts"] = alerts
        for a in alerts:
            print(a)
    else:
        state["alerts"] = []
        print("✅ Token预算正常")
    
    save_state(state)
    
    # 联动 session_manager
    if status in ("yellow", "red"):
        trigger_session_checkpoint(status, rounds)

if __name__ == "__main__":
    main()
