# Architecture Knowledge Graph Skill

交互式架构知识图谱构建技能，将系统架构描述转化为可交互的 Web 可视化图谱。

## 快速开始

### 1. 使用技能生成图谱

```bash
# 使用默认示例生成
python3 scripts/generate_graph.py --output my_architecture.html

# 使用自定义配置文件生成
python3 scripts/generate_graph.py --config my_system.json --output my_architecture.html
```

### 2. 配置文件格式

```json
{
  "system_name": "智能交易决策系统",
  "description": "基于AI的交易决策支持系统",
  "layers": [
    {
      "id": "perception",
      "name": "感知层",
      "color": "#3498db",
      "y": 100,
      "nodes": [
        {
          "id": "data_collection",
          "name": "数据采集",
          "detail": "实时获取市场数据、订单簿信息"
        }
      ]
    }
  ],
  "edges": [
    {
      "source": "data_collection",
      "target": "feature_extraction",
      "label": "原始数据"
    }
  ]
}
```

### 3. 查看结果

直接在浏览器中打开生成的 `.html` 文件即可。

## 特性

- **可交互**: 拖拽、缩放、点击查看详情
- **高亮关联**: 点击节点高亮其邻居节点
- **响应式**: 适配不同屏幕尺寸
- **自包含**: 单文件输出，无需服务器

## 技术栈

- Cytoscape.js - 图可视化库
- Pure CSS - 样式（无外部 CSS 框架依赖）
- Vanilla JavaScript - 原生 JS，无框架依赖
