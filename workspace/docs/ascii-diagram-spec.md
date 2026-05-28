# 图示规范

## 原则
- **Mermaid为主** — 结构图/流程图/架构图统一用Mermaid代码
- **飞书文档渲染** — 创建飞书文档放Mermaid代码块，飞书原生渲染
- **发链接** — Captain在飞书里直接看渲染后的图，不用翻源码
- **纯文本备用** — 简单关系/状态才用ASCII

## 工作流

**方案A（首选）：** 飞书文档渲染
```
我写Mermaid代码 → 创建飞书文档 → 发链接 → Captain看渲染图
```

**方案B（备用）：** 直接发图
```
生成PNG到workspace路径 → message(filePath=...) → Captain看内联图
```

**禁止：**
- 不调用kroki.io/mermaid.ink等外部API
- 不下载PNG再发送（链路长、不稳定）
- 不用`/tmp`路径发图（不在mediaLocalRoots白名单内）
- 不发纯代码让Captain自己渲染

## 图类型选择

| 场景 | 方式 | 示例 |
|------|------|------|
| 流程/链路 | Mermaid graph TD | session管理链路 |
| 时序 | Mermaid sequenceDiagram | 消息传递流程 |
| 状态机 | Mermaid stateDiagram | 交易状态 |
| 类关系 | Mermaid classDiagram | 模块关系 |
| 简单列表 | Markdown表格 | 数据对比 |
| 极简关系 | ASCII文本 | 快速草图 |
