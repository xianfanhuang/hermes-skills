# 🦞 ai-trading-sync

> Meta-Sensory Intelligence Ltd - 自主交易系统同步仓库

## 简介

这是 Trading Assistant 的核心数据仓库，包含知识库、记忆、自动化脚本和配置文件。支持跨平台恢复、自动同步和静默运转。

## 仓库结构

```
ai-trading-sync/
├── README.md                  # 本文件
├── RESTORE.md                 # 一键恢复指南
├── RESTORE-3LAYER.md          # 三层恢复体系文档
├── SESSION-TIMER-PROMPT.md    # 通用Session计时提示词
├── MEMORY.md                  # 长期记忆
├── USER.md                    # 用户偏好
├── IDENTITY.md                # 身份定义
├── SOUL.md                    # 安全规则
├── AGENTS.md                  # 代理配置
├── TOOLS.md                   # 工具配置
│
├── knowledge/                 # 知识库
│   ├── INDEX.md               # 知识库索引（FTS入口）
│   ├── B-practices/           # 实战记录
│   ├── G-guides/              # 指南
│   └── R-rules/               # 规则
│
├── memory/                    # 记忆系统
│   ├── 2026-*.md              # 每日记忆
│   └── sessions/              # Session归档
│
├── scripts/                   # 自动化脚本
│   ├── auto-memory.sh         # 自动记忆更新
│   ├── session-archive.sh     # Session归档
│   ├── knowledge-extract.sh   # 知识提取
│   ├── knowledge-consolidate.sh # 知识统一
│   ├── knowledge-index.sh     # 索引生成
│   ├── sync-to-backup.sh      # 同步到备份
│   ├── memory-cli.sh          # 统一CLI工具
│   ├── full-restore.sh        # 全量恢复
│   ├── cron-restore.sh        # Cron恢复
│   ├── restore-layer1-lightweight.sh  # 轻量恢复
│   ├── restore-layer3-disaster.sh     # 备灾恢复
│   └── session-turn-tracker.sh        # 轮次追踪
│
└── chanlun-agent/             # 缠论交易系统
    ├── czsc_extension.py      # 缠论扩展
    ├── risk_engine.py         # 风控引擎
    └── paper-trading/         # 模拟交易
```

## 快速开始

### 一键恢复（推荐）

```bash
# Layer 1: 轻量恢复（无运行环境）
curl -sL https://raw.githubusercontent.com/xianfanhuang/ai-trading-sync/main/scripts/restore-layer1-lightweight.sh | bash

# Layer 2: 全量恢复（有OpenClaw）
git clone git@github.com:xianfanhuang/ai-trading-sync.git /workspace/projects/workspace
bash /workspace/projects/workspace/scripts/full-restore.sh
```

### 日常使用

```bash
# 搜索知识库
bash memory-cli.sh search "止损"

# 查看系统状态
bash memory-cli.sh status

# 同步到云端
bash memory-cli.sh sync
```

## 三层恢复体系

| 层级 | 用途 | 方式 | 能力 |
|------|------|------|------|
| **Layer 1** | 豆包/ChatGPT等 | curl + GitHub Raw | 方案讨论、知识查询 |
| **Layer 2** | OpenClaw环境 | git clone + full-restore.sh | 完整运行、自动归档 |
| **Layer 3** | 灾难恢复 | 快照 + Git + S3 | 一键恢复、多地冗余 |

详见 [RESTORE-3LAYER.md](RESTORE-3LAYER.md)

## 知识库

- **B-practices**: 实战记录（交易案例）
- **G-guides**: 指南（缠论体系、SOP）
- **R-rules**: 规则（笔、中枢、背驰规则）

当前状态: **69个知识文件**

## 自动化

| 任务 | 频率 | 说明 |
|------|------|------|
| auto-memory | 每小时 | 自动记忆更新 |
| session-archive | 每2小时 | Session归档检查 |
| backup-sync | 每6小时 | 增量同步到GitHub |
| memory-archive | 每天02:00 | 记忆压缩归档 |
| session-turn-check | 每30分钟 | 轮次/时间检查 |

## 跨平台进化

```
豆包/ChatGPT → 对话产出 → 文档链接 → 传回
                       ↓
OpenClaw → 拉取 → 归档 → 知识提取 → 同步GitHub
                       ↓
各终端 ← 拉取最新知识 ← GitHub
```

## Session管理

- **OpenClaw**: 全自动（45分钟/50轮/70%context提醒）
- **豆包/ChatGPT**: 提示词（SESSION-TIMER-PROMPT.md）

## 更新日志

### 2026-05-27

#### 知识库自动提取系统
- 知识库从5条增长到69条（B-practices 26, G-guides 14, R-rules 29）
- 实现Session → 知识库自动提取
- 三处散落文件统一到knowledge/目录
- 脚本: knowledge-extract.sh, knowledge-consolidate.sh, knowledge-index.sh

#### 三层恢复体系
- Layer 1: 轻量恢复（curl + GitHub Raw，无运行环境）
- Layer 2: 全量恢复（git clone + full-restore.sh）
- Layer 3: 备灾恢复（快照 + Git + S3）
- 脚本: restore-layer1-lightweight.sh, restore-layer3-disaster.sh

#### 统一CLI工具
- memory-cli.sh: 纯bash实现，平台无关
- 支持: search, knowledge, memory, sync, restore, status

#### Session轮次追踪
- session-turn-tracker.sh: 追踪轮次和时间
- 配置: 45分钟/50轮/70%context
- 自动提醒 + 自动归档
- 通用提示词: SESSION-TIMER-PROMPT.md

#### 跨平台进化逻辑
- 豆包产出 → OpenClaw处理 → GitHub同步
- 各终端通过GitHub保持一致

### 2026-05-26

#### 缠论交易系统
- 统一引擎: engine.py + config.json
- 三层止损体系: 入场止损/结构止损/移动止损
- 老虎模拟盘下单对接
- 数据源: Finnhub(美股) + Tiger(港股)

#### 记忆系统
- Auto-Memory v2: 幂等性修复
- Session归档: 自动归档到memory/sessions/
- 记忆压缩: 30天以上压缩归档

### 2026-05-20

#### ChanlunAgent MVP
- 核心模块: czsc扩展层/风控引擎/反思引擎
- 数据路由: SmartDataRouter
- 飞书集成: 飞书CLI

### 2026-05-18

#### 缠论元交易体系
- 知识库: chanlun-meta-trading-system.md
- 存在本体论×缠论双向整合
- GitHub开源生态调研

---

## 维护

- **自动同步**: 每6小时同步到GitHub
- **自动归档**: Session自动归档
- **自动压缩**: 30天以上记忆压缩
- **最小维护成本**: 静默运转

## 许可

Private - Meta-Sensory Intelligence Ltd

---

*最后更新: 2026-05-27 07:27 GMT+8*
