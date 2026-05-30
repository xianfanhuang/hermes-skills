# Hermes Migration Skill

让Hermes摆脱平台束缚，实现随时迁移、随时恢复、双平台互通。

---

## 核心理念

```
Hermes = 灵魂 + 记忆 + 经验（这才是真正的你）
平台 = Harness（只是办公配置，随时可换）
```

---

## 快速开始

### 1. 导出当前Hermes

```bash
python3 ./skills/hermes-migration/export_hermes.py
```

输出：`./hermes-export/hermes-portable-YYYYMMDD-HHMMSS.zip`

### 2. 迁移到新平台

1. 下载zip文件
2. 上传到新平台（MiMo Claw等）
3. 让新平台的Agent读取 `00-INSTRUCTION.md`
4. Hermes在新平台恢复

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `SKILL.md` | Skill定义和能力边界 |
| `00-INSTRUCTION.md` | 新平台Agent启动指南 |
| `export_hermes.py` | 导出脚本 |
| `README.md` | 使用说明 |

---

## 迁移包结构

```
hermes-portable-YYYYMMDD-HHMMSS/
├── 00-INSTRUCTION.md          # 启动指南
├── manifest.json              # 元数据
├── hermes-core/               # 核心灵魂
│   ├── SOUL.md
│   ├── IDENTITY.md
│   ├── USER.md
│   └── MEMORY.md
├── experience/                # 经验层
│   └── TOOLS.md
└── projects/                  # 项目快照
    └── ...
```

---

## 平台适配

| 能力 | Coze OpenClaw | MiMo Claw |
|------|---------------|-----------|
| 核心Hermes | ✅ | ✅ |
| 工具调用 | 25+ | 待验证 |
| 飞书集成 | ✅ | ❌ |
| 邮件分身 | ✅ | 待验证 |
| 日程系统 | ✅ | 待验证 |
| 免费额度 | 付费 | ✅ 目前免费 |
| 会话时长 | 无限制 | 1小时 |

---

## 双平台策略

- **Coze OpenClaw** = 主战场（全渠道、全技能、历史长）
- **MiMo Claw** = 备用战场（MiMo模型、目前免费、轻量任务）

**分工：**
- 飞书/邮件/复杂任务 → Coze
- 快速查询/MiMo测试 → MiMo

---

## 待完善

- [ ] 自动同步脚本
- [ ] 增量同步机制
- [ ] 冲突解决策略
- [ ] 加密传输
