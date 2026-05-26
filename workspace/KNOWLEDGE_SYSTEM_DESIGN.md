# Session → 知识库自动提取系统设计

> **版本:** v1.0  
> **日期:** 2026-05-27  
> **设计目标:** 三级全量模式 — session完整归档 → 自动知识提取 → 统一知识库

---

## 一、问题诊断

### 现状
| 问题 | 详情 |
|------|------|
| 知识散落三处 | `knowledge/`、`chanlun-agent/knowledge/`、`skills/.../knowledge/` |
| 内容单薄 | 实战仅2条，规则仅笔和中枢 |
| 无自动提取 | session结束后知识不沉淀 |
| Memory Search | 0/119 indexed（embedding bug，FTS可用） |

### 目标
- **三级全量**: session → 完整归档 → 自动提取 → 统一知识库
- **不压缩**: session transcripts保留完整上下文
- **幂等**: 重复运行不产生重复内容
- **FTS友好**: 所有文件可被全文搜索

---

## 二、架构设计

### 2.1 数据流

```
Session JSONL
    │
    ├─[1]─→ session-to-md.sh ──→ memory/sessions/raw/{uuid}.md (完整transcript)
    │
    ├─[2]─→ session-archive.sh ──→ memory/sessions/{date}-{channel}-{id}.md (摘要)
    │
    └─[3]─→ knowledge-extract.sh ──→ knowledge/{B,G,R}/ (自动提取)
                                        │
                                        ▼
                              knowledge-consolidate.sh (统一散落知识)
                                        │
                                        ▼
                              knowledge-index.md (索引文件，FTS入口)
```

### 2.2 目录结构（统一后）

```
workspace/
├── knowledge/                          # 统一知识库（唯一权威源）
│   ├── B-practices/                    # 实战记录
│   │   ├── 2026-05-20_CRCL_long_loss.md
│   │   ├── 2026-05-21_SOXS_long_loss.md
│   │   └── ...
│   ├── G-guides/                       # 指南/方法论
│   │   ├── signal_sop.md
│   │   ├── chanlun-meta-trading-system.md
│   │   └── ...
│   ├── R-rules/                        # 交易规则
│   │   ├── bi_rules.md
│   │   ├── zs_rules.md
│   │   ├── chanlun-rules.md
│   │   └── ...
│   └── INDEX.md                        # 知识库索引（FTS入口）
│
├── memory/
│   ├── sessions/
│   │   ├── raw/                        # 完整transcripts（session-to-md输出）
│   │   │   └── {uuid}.md
│   │   └── {date}-{channel}-{id}.md   # 摘要归档
│   └── YYYY-MM-DD.md                  # 每日记忆
│
└── scripts/
    ├── session-to-md.sh               # JSONL → MD (已有)
    ├── session-archive.sh             # 归档摘要 (已有)
    ├── knowledge-extract.sh           # 从sessions提取知识 (新建)
    ├── knowledge-consolidate.sh       # 统一散落知识 (新建)
    └── knowledge-index.sh             # 构建索引 (新建)
```

### 2.3 B/G/R 分类定义

| 类别 | 目录 | 内容 | 提取关键词 |
|------|------|------|-----------|
| **B-practices** | `knowledge/B-practices/` | 实战交易记录、盈亏分析、反思 | 入场/出场/盈亏/止损/平仓/买入/卖出 |
| **G-guides** | `knowledge/G-guides/` | 方法论、SOP、系统设计、分析框架 | 策略/框架/SOP/流程/方法/体系 |
| **R-rules** | `knowledge/R-rules/` | 交易规则、风控规则、技术规则 | 规则/必须/禁止/止损/风控/条件 |

### 2.4 幂等设计

| 操作 | 幂等机制 |
|------|---------|
| session归档 | 检查输出文件是否存在且比源文件新 |
| 知识提取 | 按session ID+内容hash去重 |
| 知识合并 | 按文件名精确匹配，内容hash防重复段落 |
| 索引构建 | 每次全量重建（轻量操作） |

### 2.5 Cron集成

```bash
# 每小时: session转MD (已有)
0 * * * * bash scripts/session-to-md.sh

# 每6小时: 知识提取
0 */6 * * * bash scripts/knowledge-extract.sh

# 每天03:00: 知识统一 + 索引构建
0 3 * * * bash scripts/knowledge-consolidate.sh && bash scripts/knowledge-index.sh
```

---

## 三、实现计划

1. `knowledge-extract.sh` — 从session transcripts提取B/G/R知识
2. `knowledge-consolidate.sh` — 统一三处散落知识到knowledge/
3. `knowledge-index.sh` — 生成INDEX.md索引文件
4. 更新 `auto-memory.sh` — 集成知识提取调用
5. 验证幂等性和FTS兼容性
