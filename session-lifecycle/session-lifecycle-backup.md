# Session 全生命周期机制全景图 v2

> 3轮对话，25小时跨度，包含所有自动/手动机制

## 一、单次Session内部机制

```mermaid
flowchart TD
    START([Session 启动]) --> CTX[context-restore.sh<br/>恢复上下文]
    CTX --> AUTO[auto-archive-on-reset<br/>归档上一个session]
    AUTO --> GREET[问候 Captain]

    GREET --> LOOP{接收消息}

    LOOP -->|Captain消息| PROC[处理任务]
    LOOP -->|系统消息| SYS[处理系统事件]

    PROC --> OUT_CHECK{输出超400字?}
    OUT_CHECK -->|是| SHORT[精简输出]
    OUT_CHECK -->|否| SEND[发送回复]
    SHORT --> SEND

    SYS -->|轮次检查| TURN[session-turn-tracker.sh check]
    SYS -->|归档检查| ARCH_CHECK[session-archive检查]
    SYS -->|备份同步| SYNC[sync-to-backup.sh]
    SYS -->|Session清理| CLEAN[session-cleanup.sh]
    SYS -->|记忆归档| MEM_ARCH[memory-archive.sh]

    TURN --> TURN_OK{异常?}
    TURN_OK -->|超45分钟| WARN_TIME[提醒: 建议开新会话]
    TURN_OK -->|轮次>=50| WARN_TURN[提醒: 建议开新会话]
    TURN_OK -->|Context>=70%| WARN_CTX[提醒: 建议开新会话]
    TURN_OK -->|正常| LOOP

    WARN_TIME --> LOOP
    WARN_TURN --> LOOP
    WARN_CTX --> LOOP

    SEND --> LOOP

    LOOP -->|/new| NEW[Session Reset]
    LOOP -->|/reset| RESET[Session Reset]

    NEW --> ARCH[归档当前session]
    RESET --> ARCH
    ARCH --> NEW_SESSION[启动新Session]

    NEW_SESSION --> CTX
```

## 二、/new 与 /reset 的区别

```mermaid
flowchart LR
    subgraph "/new"
        N1[当前session] -->|OpenClaw处理| N2[.jsonl 保存为<br/>.jsonl.reset.TIMESTAMP]
        N2 --> N3[创建全新session<br/>无任何上下文]
        N3 --> N4[context-restore.sh<br/>恢复上下文]
        N4 --> N5[auto-archive-on-reset<br/>归档上一个session]
    end

    subgraph "/reset"
        R1[当前session] -->|OpenClaw处理| R2[.jsonl 保存为<br/>.jsonl.reset.TIMESTAMP]
        R2 --> R3[创建全新session<br/>无任何上下文]
        R3 --> R4[context-restore.sh<br/>恢复上下文]
        R4 --> R5[auto-archive-on-reset<br/>归档上一个session]
    end

    N1 -.->|相同| R1
    N2 -.->|相同| R2
    N3 -.->|相同| R3
    N4 -.->|相同| R4
    N5 -.->|相同| R5
```

> **/new 和 /reset 行为完全相同**：都保存旧session为.reset文件，创建新session，恢复上下文。

## 三、上下文恢复流程

```mermaid
flowchart TD
    subgraph "context-restore.sh"
        A[开始] --> B[auto-archive-on-reset.sh<br/>归档上一个未归档session]
        B --> C[读取 memory/YYYY-MM-DD.md<br/>今日记忆]
        C --> D[读取 memory/MEMORY.md<br/>长期记忆]
        D --> E[检查 .last_session_id<br/>上一个session ID]
        E --> F[读取最近session归档摘要]
        F --> G[输出精简上下文摘要]
    end

    subgraph "自动注入（OpenClaw）"
        H[AGENTS.md] --> I[系统提示词]
        J[SOUL.md] --> I
        K[USER.md] --> I
        L[IDENTITY.md] --> I
        M[MEMORY.md] --> I
        N[TOOLS.md] --> I
    end

    G --> I
    I --> READY[Session 就绪]
```

## 四、防溢出机制

```mermaid
flowchart TD
    subgraph "输出防溢出"
        O1[单轮输出] --> O2{超400字?}
        O2 -->|是| O3[精简: 列表代替段落<br/>一句话回复<br/>直接给结论]
        O2 -->|否| O4[正常输出]
        O3 --> O5[发送]
        O4 --> O5
    end

    subgraph "上下文防溢出"
        C1[每30分钟检查] --> C2{Context>=70%?}
        C2 -->|是| C3[⚠️ 提醒Captain<br/>开新会话]
        C2 -->|否| C4[继续]
        C3 --> C5{Captain确认?}
        C5 -->|/new| C6[归档+重置]
        C5 -->|继续| C4
    end

    subgraph "轮次防溢出"
        T1[轮次计数] --> T2{>=50轮?}
        T2 -->|是| T3[⚠️ 提醒开新会话]
        T2 -->|否| T4[继续]
    end

    subgraph "时间防溢出"
        H1[session时长] --> H2{超45分钟?}
        H2 -->|是| H3[⚠️ 提醒开新会话]
        H2 -->|否| H4[继续]
    end
```

## 五、25小时全流程时间线

```mermaid
gantt
    title Session 全生命周期 (25小时)
    dateFormat HH:mm
    axisFormat %H:%M

    section Session 1
    对话+任务处理     :a1, 09:00, 13min
    /new重置          :milestone, m1, 09:13, 0min

    section Session 2
    auto-archive触发  :a2, 09:13, 1min
    对话+任务处理     :a3, 09:14, 3h
    定时归档(跳过)    :crit, t1, 11:00, 1min
    对话+任务处理     :a4, after a3, 3h
    定时归档(跳过)    :crit, t2, 13:00, 1min
    对话+任务处理     :a5, after a4, 3h
    定时归档(跳过)    :crit, t3, 15:00, 1min
    /new重置          :milestone, m2, 18:00, 0min

    section Session 3
    auto-archive触发  :a6, 18:00, 1min
    对话+任务处理     :a7, 18:01, 15h
    定时归档(跳过)    :crit, t4, 20:00, 1min
    /new重置          :milestone, m3, 09:00, 0min

    section 自动任务
    定时归档(每2h)    :ta, 11:00, 22h
    备份同步(每6h)    :tb, 10:03, 23h
    Session清理(每1h) :tc, 11:00, 22h
    记忆归档(每天2点) :td, 02:00, 1h

    section 备份仓库
    第1次同步         :bs1, 10:03, 1min
    第2次同步         :bs2, 16:03, 1min
    第3次同步         :bs3, 22:03, 1min
    第4次同步         :bs4, 04:03, 1min
    第5次同步         :bs5, 10:03, 1min
```

## 六、数据流全景

```mermaid
flowchart TB
    subgraph "Session运行中"
        MSG[消息] --> JSONL[.jsonl 文件<br/>逐条写入]
    end

    JSONL -->|/new 或 /reset| RESET_FILE[.jsonl.reset.TIMESTAMP<br/>原始transcript]

    RESET_FILE -->|立即| AUTO_ARCH[auto-archive-on-reset<br/>提取关键消息 → .md]
    RESET_FILE -->|每6小时| SYNC_GIT[backup-sync<br/>增量同步到GitHub]
    RESET_FILE -->|24小时后| CLEANUP[session-cleanup<br/>删除本地文件]

    AUTO_ARCH -->|每6小时| SYNC_GIT

    SYNC_GIT --> GITHUB[GitHub仓库<br/>ai-trading-sync]

    GITHUB -->|.md 归档| G1[✅ 可读摘要]
    GITHUB -->|.jsonl.reset| G2[✅ 原始transcript]
    GITHUB -->|raw archives| G3[✅ 完整对话记录]
    GITHUB -->|交易日志| G4[✅ 执行记录]
    GITHUB -->|代码/配置| G5[✅ 系统状态]

    style G1 fill:#90EE90
    style G2 fill:#FFB6C1
    style G3 fill:#87CEEB
    style G4 fill:#FFD700
    style G5 fill:#DDA0DD
```

## 七、机制汇总表

| 机制 | 触发方式 | 频率 | 作用 | 保护层 |
|------|----------|------|------|--------|
| auto-archive-on-reset | /new 或 /reset | 每次reset | 立即归档上一个session | 第1层 |
| session-archive cron | 定时 | 每2小时 | 补充归档活跃session | 第2层 |
| backup-sync | 定时 | 每6小时 | 增量同步到GitHub | 第3层 |
| session-cleanup | 定时 | 每小时 | 清理超24h孤立文件 | 第4层 |
| memory-archive | 定时 | 每天02:00 | 压缩超30天记忆 | 第5层 |
| session-turn-check | 定时 | 每30分钟 | 防溢出(轮次/时间/context) | 运行时 |
| 输出自检 | 每轮回复 | 实时 | 防输出过量 | 运行时 |
| context-restore | session启动 | 每次 | 恢复上下文 | 启动时 |

---
*v2.0 | 2026-05-30 | First-Mate-feishu*
