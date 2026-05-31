# Hermes Skills

Hermes 双轨制技能仓库 —— 与核心层分离，按需加载。

## 架构

```
Hermes-Core (轻量迁移包)
    ↓ 加载
skill-manifest.json
    ↓ 按需clone
Hermes-Skills (本仓库)
```

## 使用

### 新环境初始化

```bash
# 1. 加载必需技能
python3 hermes-cli.py --load-required

# 2. 加载所有技能
python3 hermes-cli.py --load-all

# 3. 加载指定技能
python3 hermes-cli.py --skill token-budget-manager
```

### 列出可用技能

```bash
python3 hermes-cli.py --list
```

## 技能清单

| 技能 | 版本 | 优先级 | 说明 |
|-----|------|--------|------|
| hermes-migration | 2.0 | 100 | 迁移系统 |
| token-budget-manager | 2.1 | 90 | 轻量预算管理 |
| trading-assistant | 1.0 | 80 | 交易助手核心能力（缠论/数据路由/风控/反思） |
| voice-assistant | 1.0.0 | 70 | 中英双语语音消息生成与识别（MIMO TTS + ASR） |
| architecture-knowledge-graph | 1.0.0 | 60 | 交互式架构知识图谱构建（Cytoscape.js 可视化） |

## 新增技能
**注意**此处只保留当日新增
### architecture-knowledge-graph (2026-05-31)

**功能**: 将系统架构描述转化为可交互的 Web 知识图谱

**使用场景**:
- 系统架构可视化
- 技术文档增强
- 知识图谱展示

**快速开始**:
```bash
cd architecture-knowledge-graph
python3 scripts/generate_graph.py --output my_arch.html
```

**特性**:
- 可拖拽、缩放、点击查看详情
- 节点关联高亮
- 响应式布局
- 自包含 HTML 输出

## 版本管理

- 每个skill独立版本
- Git tag格式: `skill-name-vx.x.x`
- manifest自动追踪版本

## 开发规范

1. 每个skill必须有SKILL.md，包含version字段
2. 敏感信息不进仓库（API key等）
3. 更新后及时打tag

---

## 新增技能

### session-lifecycle (2026-05-31)

**功能**: Session 全生命周期机制管理

**包含**:
- 启动流程（context-restore → auto-archive）
- /new 与 /reset 机制
- 四层防溢出（输出/轮次/时间/context）
- 五层定时保护（归档/备份/清理/记忆压缩）
- 排查指南

**使用场景**:
- 理解 OpenClaw session 机制
- 排查 session 卡住/context 满等问题
- 新 agent 快速了解系统运行原理

**快速开始**:
```bash
cd session-lifecycle
# 读技能文档
cat SKILL.md
# 需要细节时看原文
cat session-lifecycle-backup.md
```
