# session-lifecycle

> 版本：v2.0  
> 作者：First Mate (OpenClaw)  
> 创建时间：2026-05-30  
> 最后更新：2026-05-31

## 简介

Session 全生命周期管理技能，涵盖 OpenClaw session 的启动、归档、防溢出、备份同步等完整机制。

## 功能

- **启动流程**：context-restore → auto-archive → 上下文恢复
- **/new 与 /reset**：session 重置机制（行为完全相同）
- **四层防溢出**：输出/轮次/时间/context 使用率检查
- **五层定时保护**：归档/备份/清理/记忆压缩
- **排查指南**：session 卡住、context 满等问题排查

## 快速开始

```bash
# 读技能文档
cat SKILL.md

# 需要细节时看原文
cat session-lifecycle-backup.md
```

## 适用场景

- 理解 OpenClaw session 运行机制
- 排查 session 卡住/context 满等问题
- 新 agent 快速了解系统运行原理

## 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 提炼后的技能文档（核心机制、防溢出、定时任务、排查指南） |
| `session-lifecycle-backup.md` | 原始完整文档（含 Mermaid 流程图、时间线、数据流全景） |
