# Session 管理完整链路

## 架构总览

```mermaid
graph TD
    subgraph L1["L1: 实时自检（每轮自动）"]
        A[Agent 回复前] --> B{输出 > 1K字?}
        B -->|是| C[精简到5行以内]
        B -->|否| D[正常输出]
        A --> E{轮次 > 30?}
        E -->|是| F[⚠️ 追加归档提醒]
        E -->|否| D
        A --> G{工具调用 > 8?}
        G -->|是| H[派子session]
        G -->|否| D
    end

    subgraph L2["L2: 定时巡检（每30分钟）"]
        I[session-turn-check cron] --> J[session-turn-tracker.sh check]
        J --> K{时间 > 45min?}
        K -->|是| L[提醒开启新会话]
        J --> M{轮次 > 50?}
        M -->|是| L
        J --> N{context > 70%?}
        N -->|是| L
        K & M & N -->|否| O[正常继续]
    end

    subgraph L3["L3: 归档机制（每2小时）"]
        P[session-archive-check cron] --> Q{今日有活跃对话?}
        Q -->|是| R[生成摘要]
        R --> S[保存到 memory/sessions/]
        S --> T[更新 MEMORY.md]
        Q -->|否| U[跳过]
    end

    subgraph L4["L4: 跨域规则（启动加载）"]
        V[TOOLS.md] --> W[L1自检规则]
        V --> X[轻量回复规范]
        V --> Y[Spawn决策树]
        Z[AGENTS.md] --> AA[启动流程 2步]
    end

    L1 --> L2
    L2 --> L3
    L4 -.->|每次启动注入| L1

    style L1 fill:#e8f5e9,stroke:#4caf50
    style L2 fill:#e3f2fd,stroke:#2196f3
    style L3 fill:#fff3e0,stroke:#ff9800
    style L4 fill:#f3e5f5,stroke:#9c27b0
```

## 数据流

```mermaid
sequenceDiagram
    participant C as Captain
    participant A as Agent
    participant S as session-turn-tracker
    participant M as MEMORY.md
    participant G as GitHub

    C->>A: 发消息
    A->>A: L1自检（输出长度/轮次/工具数）
    A->>C: 精简回复

    Note over A: 每30分钟
    A->>S: session-turn-check
    S->>A: 轮次/时间/context状态
    A->>C: 超阈值则提醒归档

    Note over A: 每2小时
    A->>M: session-archive-check
    A->>M: 生成摘要归档

    Note over A: 每6小时
    A->>G: backup-sync
    A->>G: 同步到 ai-trading-sync

    Note over A: 每天02:00
    A->>M: memory-archive-daily
    A->>M: 压缩30天前记忆
```

## Cron 任务总表

| 任务 | 频率 | 动作 | 与Token预算关系 |
|------|------|------|----------------|
| session-turn-check | 每30分钟 | 检查轮次/时间/context + output自检 | **直接相关** |
| session-archive-check | 每2小时 | 归档活跃session | 释放上下文 |
| backup-sync | 每6小时 | 同步到GitHub | 无直接关系 |
| memory-archive-daily | 每天02:00 | 压缩旧记忆 | 减少启动加载 |
| SOP任务(6个) | 交易日固定时间 | 盘前/盘中/盘后 | 独立session，不影响主对话 |
| maintenance-check | 每天03:00 | 系统维护 | 无直接关系 |
