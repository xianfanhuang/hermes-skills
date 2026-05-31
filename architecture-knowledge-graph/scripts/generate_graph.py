#!/usr/bin/env python3
"""
架构知识图谱生成器
将 JSON 配置转换为交互式 HTML 图谱
"""

import json
import argparse
import os
import sys

# 默认配置示例
DEFAULT_CONFIG = {
    "system_name": "智能交易决策系统",
    "description": "基于AI的智能交易决策支持系统，实现从数据采集到自动执行的完整闭环",
    "layers": [
        {
            "id": "perception",
            "name": "感知层",
            "color": "#3498db",
            "y": 150,
            "nodes": [
                {
                    "id": "data_collection",
                    "name": "数据采集",
                    "detail": "实时获取市场数据、订单簿、资金流向等多维度信息，支持多交易所数据源接入"
                },
                {
                    "id": "feature_extraction",
                    "name": "特征提取",
                    "detail": "计算技术指标（MACD、RSI、布林带等），生成模型输入特征向量"
                }
            ]
        },
        {
            "id": "decision",
            "name": "决策层",
            "color": "#e67e22",
            "y": 300,
            "nodes": [
                {
                    "id": "signal_generation",
                    "name": "信号生成",
                    "detail": "基于机器学习模型生成交易信号，包括入场点、出场点、仓位建议"
                },
                {
                    "id": "risk_assessment",
                    "name": "风险评估",
                    "detail": "评估单笔交易风险、组合风险，计算VaR、最大回撤等指标"
                }
            ]
        },
        {
            "id": "execution",
            "name": "执行层",
            "color": "#27ae60",
            "y": 450,
            "nodes": [
                {
                    "id": "order_management",
                    "name": "订单管理",
                    "detail": "智能订单拆分、滑点控制、最优执行策略选择"
                },
                {
                    "id": "monitor",
                    "name": "监控模块",
                    "detail": "实时跟踪订单状态、持仓盈亏、系统健康度监控"
                }
            ]
        }
    ],
    "edges": [
        {"source": "data_collection", "target": "feature_extraction", "label": "原始数据"},
        {"source": "feature_extraction", "target": "signal_generation", "label": "特征向量"},
        {"source": "signal_generation", "target": "risk_assessment", "label": "交易信号"},
        {"source": "risk_assessment", "target": "order_management", "label": "风控确认"},
        {"source": "order_management", "target": "monitor", "label": "执行状态"}
    ]
}


def generate_html(config, template_path=None):
    """根据配置生成 HTML"""
    
    # 构建节点数据
    nodes = []
    descriptions = {}
    
    for layer in config["layers"]:
        layer_x = 150
        layer_spacing = 300
        
        for i, node in enumerate(layer["nodes"]):
            nodes.append({
                "data": {
                    "id": node["id"],
                    "label": node["name"],
                    "type": "layer",
                    "layer": layer["id"]
                },
                "position": {
                    "x": layer_x + i * layer_spacing,
                    "y": layer["y"]
                }
            })
            
            descriptions[node["id"]] = {
                "title": node["name"],
                "desc": node["detail"],
                "tag": layer["name"],
                "color": layer["color"]
            }
    
    # 构建边数据
    edges = []
    for edge in config["edges"]:
        edges.append({
            "data": {
                "source": edge["source"],
                "target": edge["target"],
                "label": edge.get("label", "")
            }
        })
    
    # 生成 HTML
    html = generate_html_template(
        config["system_name"],
        config["description"],
        nodes,
        edges,
        descriptions,
        config["layers"]
    )
    
    return html


def generate_html_template(title, description, nodes, edges, descriptions, layers):
    """生成完整的 HTML 模板"""
    
    nodes_json = json.dumps(nodes, ensure_ascii=False, indent=2)
    edges_json = json.dumps(edges, ensure_ascii=False, indent=2)
    descriptions_json = json.dumps(descriptions, ensure_ascii=False, indent=2)
    
    # 生成图例 HTML
    legend_html = ""
    for layer in layers:
        legend_html += f'''
        <div class="legend-item">
          <div class="legend-color" style="background: {layer['color']}"></div>
          <span>{layer['name']}</span>
        </div>'''
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 架构知识图谱</title>
    <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        
        .main {{
            display: flex;
            height: 700px;
        }}
        
        #graph {{
            flex: 1;
            background: #f8f9fa;
        }}
        
        .sidebar {{
            width: 350px;
            background: white;
            border-left: 1px solid #e0e0e0;
            padding: 24px;
            overflow-y: auto;
        }}
        
        .sidebar h3 {{
            font-size: 16px;
            color: #333;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid #667eea;
        }}
        
        .empty-state {{
            color: #999;
            text-align: center;
            padding: 40px 20px;
            font-size: 14px;
        }}
        
        .node-detail {{
            display: none;
        }}
        
        .node-detail.active {{
            display: block;
            animation: fadeIn 0.3s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .detail-tag {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            color: white;
            margin-bottom: 12px;
        }}
        
        .detail-title {{
            font-size: 20px;
            color: #333;
            margin-bottom: 12px;
            font-weight: 600;
        }}
        
        .detail-desc {{
            color: #666;
            line-height: 1.8;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        
        .legend {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
        
        .legend h4 {{
            font-size: 14px;
            color: #333;
            margin-bottom: 12px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            font-size: 13px;
            color: #666;
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            margin-right: 8px;
        }}
        
        .hint {{
            margin-top: 20px;
            padding: 12px;
            background: #f0f4ff;
            border-radius: 8px;
            font-size: 12px;
            color: #667eea;
        }}
        
        @media (max-width: 900px) {{
            .main {{
                flex-direction: column;
                height: auto;
            }}
            
            #graph {{
                height: 500px;
            }}
            
            .sidebar {{
                width: 100%;
                border-left: none;
                border-top: 1px solid #e0e0e0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>{description}</p>
        </div>
        
        <div class="main">
            <div id="graph"></div>
            
            <div class="sidebar">
                <h3>🔍 节点详情</h3>
                
                <div class="empty-state" id="emptyState">
                    点击图谱中的节点<br>查看详细信息
                </div>
                
                <div class="node-detail" id="nodeDetail">
                    <div class="detail-tag" id="detailTag">标签</div>
                    <div class="detail-title" id="detailTitle">标题</div>
                    <div class="detail-desc" id="detailDesc">描述内容</div>
                </div>
                
                <div class="legend">
                    <h4>📊 架构分层</h4>
                    {legend_html}
                </div>
                
                <div class="hint">
                    💡 提示：拖拽可移动视图，滚轮可缩放，点击节点查看详情
                </div>
            </div>
        </div>
    </div>

    <script>
        const descriptions = {descriptions_json};
        
        const cy = cytoscape({{
            container: document.getElementById('graph'),
            
            elements: {{
                nodes: {nodes_json},
                edges: {edges_json}
            }},
            
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'background-color': function(ele) {{
                            const layerColors = {{
                                'perception': '#3498db',
                                'decision': '#e67e22',
                                'execution': '#27ae60'
                            }};
                            return layerColors[ele.data('layer')] || '#95a5a6';
                        }},
                        'label': 'data(label)',
                        'width': 120,
                        'height': 60,
                        'shape': 'roundrectangle',
                        'border-width': 3,
                        'border-color': '#fff',
                        'color': '#fff',
                        'font-size': '13px',
                        'font-weight': '600',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'text-wrap': 'wrap',
                        'text-max-width': '100px',
                        'shadow-blur': 10,
                        'shadow-color': 'rgba(0,0,0,0.2)',
                        'shadow-offset-y': 4,
                        'transition-property': 'background-color, border-color, opacity',
                        'transition-duration': '0.3s'
                    }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'width': 2,
                        'line-color': '#bdc3c7',
                        'target-arrow-color': '#bdc3c7',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': '11px',
                        'color': '#7f8c8d',
                        'text-background-color': '#f8f9fa',
                        'text-background-opacity': 1,
                        'text-background-padding': '3px',
                        'arrow-scale': 1.2
                    }}
                }},
                {{
                    selector: '.highlight',
                    style: {{
                        'background-color': '#e74c3c',
                        'border-color': '#c0392b',
                        'border-width': 4
                    }}
                }},
                {{
                    selector: '.semitransparent',
                    style: {{
                        'opacity': 0.3
                    }}
                }},
                {{
                    selector: 'node:selected',
                    style: {{
                        'border-color': '#e74c3c',
                        'border-width': 4
                    }}
                }}
            ],
            
            layout: {{
                name: 'preset'
            }},
            
            minZoom: 0.3,
            maxZoom: 3,
            wheelSensitivity: 0.3
        }});
        
        // 点击节点显示详情
        cy.on('tap', 'node', function(evt) {{
            const node = evt.target;
            const nodeId = node.id();
            const desc = descriptions[nodeId];
            
            if (desc) {{
                document.getElementById('emptyState').style.display = 'none';
                const detailEl = document.getElementById('nodeDetail');
                detailEl.classList.add('active');
                
                document.getElementById('detailTag').textContent = desc.tag;
                document.getElementById('detailTag').style.background = desc.color;
                document.getElementById('detailTitle').textContent = desc.title;
                document.getElementById('detailDesc').textContent = desc.desc;
                
                highlightNode(node);
            }}
        }});
        
        // 点击空白处重置
        cy.on('tap', function(evt) {{
            if (evt.target === cy) {{
                document.getElementById('emptyState').style.display = 'block';
                document.getElementById('nodeDetail').classList.remove('active');
                
                cy.elements().removeClass('highlight semitransparent');
            }}
        }});
        
        // 高亮节点及其邻居
        function highlightNode(node) {{
            cy.elements().removeClass('highlight semitransparent').addClass('semitransparent');
            node.closedNeighborhood().removeClass('semitransparent').addClass('highlight');
        }}
        
        // 初始动画
        cy.elements().animate({{
            style: {{ 'opacity': 0 }}
        }}, {{ duration: 0 }});
        
        setTimeout(() => {{
            cy.elements().animate({{
                style: {{ 'opacity': 1 }}
            }}, {{ duration: 500 }});
        }}, 100);
    </script>
</body>
</html>'''
    
    return html


def main():
    parser = argparse.ArgumentParser(description='架构知识图谱生成器')
    parser.add_argument('--config', '-c', help='配置文件路径 (JSON)')
    parser.add_argument('--output', '-o', default='architecture_graph.html', help='输出文件路径')
    
    args = parser.parse_args()
    
    # 加载配置
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = DEFAULT_CONFIG
        print("使用默认示例配置")
    
    # 生成 HTML
    html = generate_html(config)
    
    # 保存文件
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 图谱已生成: {args.output}")
    print(f"📊 节点数: {sum(len(layer['nodes']) for layer in config['layers'])}")
    print(f"🔗 边数: {len(config['edges'])}")


if __name__ == '__main__':
    main()
