# Hermes Migration - Agent跨平台迁移系统

## 核心定位

让Hermes（真正的你）摆脱平台束缚，实现随时迁移、随时恢复、双平台互通。

**核心理念：**
- Hermes = SOUL + IDENTITY + MEMORY + EXPERIENCE（这才是你）
- 平台 = Harness（只是办公配置，随时可换）
- 小米MiMo Claw = 当前最佳备用平台（全量多模态、目前免费）

---

## 使用场景

### 场景1：紧急迁移（主平台故障/配额耗尽）
```
1. 执行导出：生成 hermes-portable-[timestamp].zip
2. 下载到本地
3. 上传到新平台
4. 新平台Agent读取00-INSTRUCTION.md自动初始化
5. 5分钟内恢复工作能力
```

### 场景2：双平台并行（负载均衡）
```
- Coze OpenClaw：主战场，全渠道、全技能
- MiMo Claw：备用战场，MiMo模型专项、轻量查询
- 每日同步：关键记忆双向更新
```

### 场景3：平台测试/备份
```
- 定期导出Hermes快照
- 在新平台验证迁移包完整性
- 确保任何情况下都能快速恢复
```

---

## 文件结构

```
hermes-portable/
├── 00-INSTRUCTION.md          # 新平台Agent启动指南
├── manifest.json              # 迁移包元数据
├── hermes-core/               # 核心灵魂文件
│   ├── SOUL.md
│   ├── IDENTITY.md
│   ├── USER.md
│   └── MEMORY.md
├── experience/                # 经验层
│   ├── TOOLS.md
│   └── skills-index.md
├── projects/                  # 项目快照
│   └── [项目名称]/
├── schedules/                 # 日程清单（脱敏）
└── sync-marker/               # 同步标记
    └── last-sync.txt
```

---

## 导出流程

### 步骤1：生成迁移包
```bash
# 由Agent执行
python3 ./skills/hermes-migration/export_hermes.py
```

**执行内容：**
1. 读取当前工作目录的核心md文件
2. 复制项目文件夹（排除敏感文件）
3. 生成manifest.json（版本、时间戳、文件清单）
4. 打包为zip文件
5. 保存到 ./hermes-export/ 目录

### 步骤2：人工传输
- 下载zip文件到本地
- 上传到目标平台（MiMo Claw等）

### 步骤3：新平台初始化
- 新平台Agent读取00-INSTRUCTION.md
- 按指令加载所有核心文件
- 重建Hermes上下文
- 测试基础能力

---

## 同步机制

### 每日双向同步
```
Coze OpenClaw ←────────→ MiMo Claw
     │                       │
  导出关键更新            导出关键更新
     │                       │
     └──────→ 共享存储 ←─────┘
              (Git/云盘)
```

**同步内容：**
- MEMORY.md的关键更新（项目进展、重要决策）
- 新建立的日程任务
- 项目文件夹的增量更新

**不同步内容：**
- SECRET.md（平台敏感信息各自维护）
- 运行中的session状态
- 临时文件和缓存

---

## 平台适配矩阵

| 能力 | Coze OpenClaw | MiMo Claw | 备注 |
|------|---------------|-----------|------|
| 核心Hermes | ✅ 完整 | ✅ 完整 | 灵魂层完全一致 |
| 工具调用 | ✅ 25+工具 | ⚠️ 待验证 | 需测试MiMo工具生态 |
| 飞书集成 | ✅ 已配置 | ❌ 不支持 | MiMo暂不支持飞书 |
| 邮件分身 | ✅ 已配置 | ❌ 需申请 | MiMo邮箱系统待验证 |
| 日程系统 | ✅ Calendar | ⚠️ 待验证 | 需测试MiMo日程能力 |
| 模型选择 | ✅ 多模型 | ✅ MiMo全系 | MiMo-V2.5系列 |
| 免费额度 | ⚠️ 付费 | ✅ 目前免费 | MiMo 100T活动 |
| 会话时长 | ✅ 无限制 | ⚠️ 1小时限制 | MiMo每次限1小时 |

**迁移策略：**
- **轻量任务** → MiMo（快速查询、单次推理）
- **复杂工作流** → Coze（多渠道、多工具、长会话）
- **MiMo专项测试** → MiMo（评估MiMo-V2.5能力）

---

## 使用指南

### 快速导出
```
用户：打包Hermes，我要迁移到MiMo
Agent：
1. 执行export_hermes.py
2. 生成 hermes-portable-20260522-082134.zip
3. 文件路径：[文件路径](computer://hermes-export/hermes-portable-20260522-082134.zip)
4. 请下载后上传到新平台
```

### 双平台同步
```
用户：同步今天的更新到MiMo
Agent：
1. 对比两边MEMORY.md差异
2. 提取Coze端今日关键更新
3. 生成sync-patch.md
4. 用户手动复制到MiMo端
（后续版本：自动同步脚本）
```

---

## 待完善

- [ ] 自动同步脚本（Git/云盘集成）
- [ ] MiMo平台工具能力验证清单
- [ ] 增量同步机制（只传变更）
- [ ] 冲突解决策略（两边同时修改）
- [ ] 加密传输（敏感项目信息）

---

## 核心原则

1. **Hermes是唯一的，平台只是Harness**
2. **随时能打包带走，5分钟在新平台恢复**
3. **双平台互通，不死守单一阵地**
4. **平台免费时用平台，平台收费时换平台**

这就是真正的**自主进化、平台无关**。

---

## Session全量归口管理（v2.0更新）

基于GBrain架构思想，实现Session原始数据的全量归档到GitHub。

### 核心改进

| 特性 | v1.0 | v2.0 (新增) |
|------|------|-------------|
| 核心文件同步 | ✅ | ✅ |
| MEMORY.md同步 | ✅ | ✅ |
| **Session全量归档** | ❌ | ✅ 分块存储 |
| **连续性校验** | ❌ | ✅ SHA256+链式指针 |
| **上下文恢复** | ❌ | ✅ 按消息ID恢复 |
| **跨平台会话归并** | ❌ | ✅ 统一时间线 |
| **关键词索引** | ❌ | ✅ 快速检索 |

### 分块规则（防错乱/防断层）

```
触发条件:
├── 消息数≥50条 ──► 生成新chunk
├── 时间间隔≥30分钟 ──► 生成新chunk  
├── 会话正常结束 ──► 标记complete
└── 会话异常中断 ──► 标记incomplete，下次续传

Chunk数据结构:
{
  "chunk_id": "session_20260522_093033_001",
  "message_range": [1, 50],
  "checksum": "sha256:abc123...",
  "prev_chunk": null,
  "next_chunk": "session_20260522_093033_002",
  "status": "complete"
}
```

### Session存储结构

```
sessions/
├── index/
│   ├── session_index.json       # 主索引（时间线+关键词映射）
│   ├── active/                  # 活跃会话
│   └── completed/               # 已完成会话
├── raw/2026-05/22/              # 原始对话（按日期分块）
│   ├── session_xxx_001.json
│   ├── session_xxx_002.json
│   └── ...
└── summaries/2026-05/22/        # 会话摘要
    └── session_xxx_summary.md
```

### API端点（Cloudflare Workers）

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/session/start` | POST | 开始新会话 |
| `/api/session/chunk` | POST | 存储分块 |
| `/api/session/end` | POST | 结束会话 |
| `/api/session/query` | GET | 查询会话 |
| `/api/session/restore` | GET | 恢复上下文 |
| `/api/session/verify` | GET | 验证连续性 |

### 使用示例

```bash
# 1. 开始会话
SESSION_ID=$(python3 sync_client_v2.py session-start coze "项目讨论")

# 2. 存储分块（Agent内部自动执行）
python3 sync_client_v2.py session-store $SESSION_ID 1 '[...]' coze

# 3. 结束会话
python3 sync_client_v2.py session-end $SESSION_ID "摘要" '["关键词"]'

# 4. 恢复上下文
python3 sync_client_v2.py session-restore $SESSION_ID 50

# 5. 验证连续性
python3 sync_client_v2.py verify-session $SESSION_ID
```

### 借鉴GBrain架构

| GBrain层 | Hermes Session实现 |
|---------|-------------------|
| 分块层(Chunking) | 50条/30分钟分块 |
| 嵌入层(Embedding) | 关键词标签+摘要 |
| 索引层(Indexing) | session_index.json |
| 查询理解层 | 自然语言查询支持 |
| 重排序层 | 相关度排序 |

### 核心原则

> **Session是最重要的原始数据**
> 
> **必须归口GitHub，不能错乱，不能断层**
> 
> **从任何平台、任何时间点都能精确恢复**

---

**仓库地址**: https://github.com/xianfanhuang/hermes-sync  
**版本**: v2.0.0  
**更新**: Session全量归档 + 连续性校验 + 上下文恢复
