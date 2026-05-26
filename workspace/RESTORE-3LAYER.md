# 🔄 三层恢复体系

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    三层恢复体系                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 1: 轻量恢复层                                    │
│  ├── 用途: 无运行环境客户端（豆包/ChatGPT等）           │
│  ├── 方式: curl + GitHub Raw URL                        │
│  ├── 内容: 知识库索引 + 核心文件 + 上下文摘要           │
│  └── 能力: 方案讨论、知识查询、决策参考                 │
│                                                         │
│  Layer 2: 全量恢复层                                    │
│  ├── 用途: 有OpenClaw环境的完整恢复                     │
│  ├── 方式: git clone + full-restore.sh                  │
│  ├── 内容: 全部文件 + cron + 配置                       │
│  └── 能力: 完整运行、自动归档、增量同步                 │
│                                                         │
│  Layer 3: 备灾恢复层                                    │
│  ├── 用途: 灾难恢复、异地备份                           │
│  ├── 方式: 定时快照 + Git + S3                          │
│  ├── 内容: 全量快照 + 异地副本                          │
│  └── 能力: 一键恢复、多地冗余、静默运转                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Layer 1: 轻量恢复层

### 使用场景
- 在豆包、ChatGPT等客户端上讨论方案
- 手机临时查看知识库
- 无git/ssh环境的电脑

### 一键恢复
```bash
curl -sL https://raw.githubusercontent.com/xianfanhuang/ai-trading-sync/main/scripts/restore-layer1-lightweight.sh | bash
```

### 输出文件
```
ai-trading-sync/
├── CONTEXT.md          # 上下文摘要（粘贴到AI客户端）
├── KNOWLEDGE_LINKS.md  # 知识库快速查询链接
├── MEMORY.md           # 长期记忆
├── USER.md             # 用户偏好
├── IDENTITY.md         # 身份定义
└── knowledge/INDEX.md  # 知识库索引
```

### 使用方式
1. 运行脚本获取文件
2. 将 `CONTEXT.md` 内容粘贴到AI客户端作为系统提示
3. 查看 `KNOWLEDGE_LINKS.md` 获取知识库链接
4. 点击链接查看完整知识内容

### 限制
- ❌ 不能自动执行
- ❌ 不能自动归档
- ❌ 不能增量同步

---

## Layer 2: 全量恢复层

### 使用场景
- 新环境完整恢复
- OpenClaw已安装的服务器
- 需要完整运行能力

### 一键恢复
```bash
# 方式1: 直接运行
bash /workspace/projects/workspace/scripts/full-restore.sh

# 方式2: 从GitHub恢复
git clone git@github.com:xianfanhuang/ai-trading-sync.git /workspace/projects/workspace
bash /workspace/projects/workspace/scripts/full-restore.sh
```

### 恢复内容
- ✅ 知识库（70个文件）
- ✅ 记忆文件（21个）
- ✅ 自动化脚本（10+个）
- ✅ Cron任务（4个）
- ✅ 配置文件

### 恢复后能力
- ✅ 知识库查询（FTS搜索）
- ✅ 记忆管理（自动归档）
- ✅ 增量同步（每6小时）
- ✅ 自动备份（每天）

### 环境要求
- OpenClaw 已安装
- Git 已配置
- bash + grep

---

## Layer 3: 备灾恢复层

### 使用场景
- 灾难恢复
- 异地备份
- 历史回溯

### 定时任务（自动静默运转）
```bash
# 每天凌晨3点创建快照
0 3 * * * bash /workspace/projects/workspace/scripts/restore-layer3-disaster.sh snapshot

# 每天凌晨4点清理旧备份
0 4 * * * bash /workspace/projects/workspace/scripts/restore-layer3-disaster.sh cleanup

# 每6小时异地备份
0 */6 * * * bash /workspace/projects/workspace/scripts/restore-layer3-disaster.sh offsite
```

### 手动操作
```bash
# 创建快照
bash scripts/restore-layer3-disaster.sh snapshot

# 查看状态
bash scripts/restore-layer3-disaster.sh status

# 从快照恢复
bash scripts/restore-layer3-disaster.sh restore

# 异地备份
bash scripts/restore-layer3-disaster.sh offsite
```

### 备份策略
| 类型 | 频率 | 保留 | 位置 |
|------|------|------|------|
| 本地快照 | 每天 | 30个 | /data/backups/ |
| Git push | 每6小时 | 永久 | GitHub |
| S3/OSS | 每天 | 可选 | 云存储 |

### 环境变量
```bash
WORKSPACE_DIR=/workspace/projects/workspace  # 工作目录
BACKUP_DIR=/data/backups/ai-trading-sync     # 备份目录
S3_BUCKET=my-bucket                          # S3 bucket（可选）
MAX_BACKUPS=30                               # 保留备份数量
```

---

## 自适应策略

### 环境检测
系统会自动检测当前环境并选择最佳恢复层：

```bash
# 检测脚本
if command -v openclaw &>/dev/null && openclaw status &>/dev/null; then
    # Layer 2: 完整恢复
    bash scripts/full-restore.sh
elif command -v git &>/dev/null; then
    # Layer 1+Git: 轻量恢复+Git
    git clone git@github.com:xianfanhuang/ai-trading-sync.git
    bash scripts/restore-layer1-lightweight.sh
else
    # Layer 1: 纯轻量恢复
    curl -sL https://raw.githubusercontent.com/.../restore-layer1-lightweight.sh | bash
fi
```

### 静默运转
- Layer 3 备灾任务通过cron自动运行
- 无需人工干预
- 失败时记录日志，不打扰用户
- 最小维护成本

---

## 维护成本

| 层级 | 维护内容 | 频率 | 成本 |
|------|----------|------|------|
| Layer 1 | 无需维护 | - | 零 |
| Layer 2 | 检查cron状态 | 每周 | 极低 |
| Layer 3 | 检查备份日志 | 每月 | 低 |

---

## 快速参考

### 临时讨论（豆包等）
```bash
curl -sL https://raw.githubusercontent.com/xianfanhuang/ai-trading-sync/main/scripts/restore-layer1-lightweight.sh | bash
# 将 CONTEXT.md 粘贴到AI客户端
```

### 完整恢复（新服务器）
```bash
git clone git@github.com:xianfanhuang/ai-trading-sync.git /workspace/projects/workspace
bash /workspace/projects/workspace/scripts/full-restore.sh
```

### 灾难恢复
```bash
bash scripts/restore-layer3-disaster.sh restore
```

### 查看状态
```bash
bash scripts/restore-layer3-disaster.sh status
bash memory-cli.sh status
```

---

*v1.0 - 2026-05-27 - 三层恢复体系*
