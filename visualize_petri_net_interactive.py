#!/usr/bin/env python3
# visualize_petri_net_proper.py
"""
Proper Petri Net visualization with traditional notation:
- Places = Circles with tokens (black dots)
- Transitions = Rectangles
- Arcs = Arrows showing flow
- Token counts visible
- Classic Petri net appearance
"""
import argparse
import json
import pathlib
import sys

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            overflow: hidden;
        }}
        #header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 15px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            position: relative;
            z-index: 1000;
        }}
        #header h1 {{
            margin: 0;
            font-size: 20px;
            font-weight: 600;
        }}
        #header p {{
            margin: 5px 0 0 0;
            opacity: 0.8;
            font-size: 12px;
        }}
        #controls {{
            background: white;
            padding: 12px 20px;
            border-bottom: 2px solid #ddd;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        #controls label {{
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            font-size: 13px;
            color: #333;
        }}
        #controls button {{
            padding: 6px 14px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }}
        #controls button:hover {{
            background: #2980b9;
            transform: translateY(-1px);
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}
        #controls button:active {{
            transform: translateY(0);
        }}
        .divider {{
            width: 1px;
            height: 24px;
            background: #ddd;
        }}
        #network {{
            width: 100%;
            height: calc(100vh - 120px);
            background: #ffffff;
        }}
        #info {{
            position: fixed;
            right: 20px;
            top: 140px;
            background: white;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            max-width: 300px;
            max-height: 500px;
            display: none;
            z-index: 1000;
            overflow-y: auto;
            border: 2px solid #3498db;
        }}
        #info h3 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 15px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }}
        #info .close-btn {{
            float: right;
            cursor: pointer;
            color: #999;
            font-size: 20px;
            line-height: 15px;
            font-weight: bold;
        }}
        #info .close-btn:hover {{
            color: #e74c3c;
        }}
        #info .info-row {{
            margin: 8px 0;
            font-size: 12px;
        }}
        #info .info-label {{
            font-weight: bold;
            color: #555;
            display: inline-block;
            min-width: 80px;
        }}
        #info .info-value {{
            color: #333;
        }}
        .legend {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            position: fixed;
            left: 20px;
            top: 140px;
            width: 220px;
            z-index: 1000;
            border: 2px solid #95a5a6;
        }}
        .legend h4 {{
            margin: 0 0 12px 0;
            color: #2c3e50;
            font-size: 14px;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 5px;
        }}
        .legend-section {{
            margin: 10px 0;
        }}
        .legend-section-title {{
            font-size: 11px;
            font-weight: bold;
            color: #7f8c8d;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 6px 0;
            font-size: 12px;
        }}
        .legend-circle {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 2px solid #2c3e50;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .legend-rect {{
            width: 30px;
            height: 20px;
            border: 2px solid #2c3e50;
            flex-shrink: 0;
        }}
        .legend-token {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: black;
        }}
        .legend-arrow {{
            width: 30px;
            height: 2px;
            background: #2c3e50;
            position: relative;
        }}
        .legend-arrow::after {{
            content: '';
            position: absolute;
            right: 0;
            top: -3px;
            width: 0;
            height: 0;
            border-left: 6px solid #2c3e50;
            border-top: 4px solid transparent;
            border-bottom: 4px solid transparent;
        }}
        #stats {{
            position: fixed;
            left: 20px;
            bottom: 20px;
            background: white;
            padding: 12px 15px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            font-size: 11px;
            z-index: 1000;
            border: 2px solid #95a5a6;
        }}
        #stats h4 {{
            margin: 0 0 8px 0;
            font-size: 12px;
            color: #2c3e50;
        }}
        #stats .stat-row {{
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin: 4px 0;
        }}
        #stats .stat-label {{
            color: #666;
        }}
        #stats .stat-value {{
            font-weight: bold;
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>{title}</h1>
        <p>{description} • Classic Petri Net Visualization</p>
    </div>
    
    <div id="controls">
        <label title="Show read transitions (optional actions)">
            <input type="checkbox" id="showReads">
            Show Reads
        </label>
        <label title="Show reservation places">
            <input type="checkbox" id="showReservations">
            Show Reservations
        </label>
        
        <div class="divider"></div>
        
        <label>
            Layout:
            <select id="layoutSelect" onchange="changeLayout()">
                <option value="hierarchical_lr">Hierarchical (L→R)</option>
                <option value="hierarchical_td">Hierarchical (T→D)</option>
                <option value="hierarchical_du">Hierarchical (D→U)</option>
            </select>
        </label>
        
        <div class="divider"></div>
        
        <button onclick="fitNetwork()" title="Fit network to screen">🔍 Fit to Screen</button>
        <button onclick="network.moveTo({{scale: 1.0}})" title="Reset zoom">🔄 Reset Zoom</button>
        <button onclick="toggleLegend()" title="Toggle legend">ℹ️ Legend</button>
        <button onclick="toggleStats()" title="Toggle statistics">📊 Stats</button>
    </div>
    
    <div id="network"></div>
    
    <div class="legend" id="legend">
        <h4>Petri Net Elements</h4>
        
        <div class="legend-section">
            <div class="legend-section-title">Places</div>
            <div class="legend-item">
                <div class="legend-circle" style="background: white;">
                    <div class="legend-token"></div>
                </div>
                <span>Place with token</span>
            </div>
            <div class="legend-item">
                <div class="legend-circle" style="background: white;"></div>
                <span>Empty place</span>
            </div>
        </div>
        
        <div class="legend-section">
            <div class="legend-section-title">Transitions</div>
            <div class="legend-item">
                <div class="legend-rect" style="background: #34495e;"></div>
                <span>Transition</span>
            </div>
        </div>
        
        <div class="legend-section">
            <div class="legend-section-title">Flow</div>
            <div class="legend-item">
                <div class="legend-arrow"></div>
                <span>Arc (token flow)</span>
            </div>
        </div>
    </div>
    
    <div id="stats">
        <h4>Network Statistics</h4>
        <div class="stat-row">
            <span class="stat-label">Places:</span>
            <span class="stat-value" id="numPlaces">0</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Transitions:</span>
            <span class="stat-value" id="numTransitions">0</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Arcs:</span>
            <span class="stat-value" id="numArcs">0</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Tokens:</span>
            <span class="stat-value" id="numTokens">0</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Visible:</span>
            <span class="stat-value" id="numVisible">0</span>
        </div>
    </div>
    
    <div id="info">
        <span class="close-btn" onclick="hideInfo()">×</span>
        <h3 id="infoTitle">Element Info</h3>
        <div id="infoContent"></div>
    </div>

    <script type="text/javascript">
        const nodesData = {nodes_json};
        const edgesData = {edges_json};
        
        const container = document.getElementById('network');
        let nodes = new vis.DataSet(nodesData);
        let edges = new vis.DataSet(edgesData);
        
        const data = {{
            nodes: nodes,
            edges: edges
        }};
        
        let options = {{
            layout: {{
                hierarchical: {{
                    direction: 'LR',
                    sortMethod: 'directed',
                    nodeSpacing: 150,
                    levelSeparation: 250,
                    treeSpacing: 200,
                    blockShifting: true,
                    edgeMinimization: true
                }}
            }},
            physics: {{
                enabled: false
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 100,
                navigationButtons: false,
                keyboard: true
            }},
            nodes: {{
                font: {{
                    size: 14,
                    face: 'Arial',
                    color: '#2c3e50',
                    bold: {{
                        size: 15
                    }}
                }},
                borderWidth: 2.5,
                shadow: {{
                    enabled: true,
                    color: 'rgba(0,0,0,0.15)',
                    size: 8,
                    x: 2,
                    y: 2
                }}
            }},
            edges: {{
                arrows: {{
                    to: {{
                        enabled: true,
                        scaleFactor: 0.8,
                        type: 'arrow'
                    }}
                }},
                smooth: {{
                    enabled: true,
                    type: 'cubicBezier',
                    forceDirection: 'horizontal',
                    roundness: 0.5
                }},
                color: {{
                    color: '#2c3e50',
                    highlight: '#e74c3c',
                    hover: '#e74c3c'
                }},
                width: 2,
                font: {{
                    size: 12,
                    align: 'horizontal',
                    strokeWidth: 3,
                    strokeColor: '#ffffff',
                    color: '#2c3e50',
                    bold: true
                }},
                shadow: {{
                    enabled: true,
                    color: 'rgba(0,0,0,0.1)',
                    size: 3
                }}
            }}
        }};
        
        const network = new vis.Network(container, data, options);
        
        // Track hidden elements
        let hiddenElements = {{
            reads: new Set(),
            reservations: new Set()
        }};
        
        // Click handler
        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                showInfo(node);
            }} else if (params.edges.length > 0) {{
                const edgeId = params.edges[0];
                const edge = edges.get(edgeId);
                showEdgeInfo(edge);
            }} else {{
                hideInfo();
            }}
        }});
        
        // Hover effect
        network.on('hoverNode', function(params) {{
            container.style.cursor = 'pointer';
        }});
        
        network.on('blurNode', function(params) {{
            container.style.cursor = 'default';
        }});
        
        function showInfo(node) {{
            const info = document.getElementById('info');
            const title = document.getElementById('infoTitle');
            const content = document.getElementById('infoContent');
            
            title.textContent = node.data.type === 'place' ? 'Place' : 'Transition';
            
            let html = '';
            
            if (node.data.type === 'place') {{
                html += `<div class="info-row">
                    <span class="info-label">Name:</span>
                    <span class="info-value">${{node.data.original_name}}</span>
                </div>`;
                html += `<div class="info-row">
                    <span class="info-label">Tokens:</span>
                    <span class="info-value">${{node.data.tokens}}</span>
                </div>`;
                if (node.data.capacity !== null) {{
                    html += `<div class="info-row">
                        <span class="info-label">Capacity:</span>
                        <span class="info-value">${{node.data.capacity}}</span>
                    </div>`;
                }}
                html += `<div class="info-row">
                    <span class="info-label">Type:</span>
                    <span class="info-value">${{node.data.place_type}}</span>
                </div>`;
            }} else {{
                html += `<div class="info-row">
                    <span class="info-label">Name:</span>
                    <span class="info-value">${{node.data.transition_name}}</span>
                </div>`;
                html += `<div class="info-row">
                    <span class="info-label">Agent:</span>
                    <span class="info-value">${{node.data.agent_id}}</span>
                </div>`;
                html += `<div class="info-row">
                    <span class="info-label">Function:</span>
                    <span class="info-value">${{node.data.function}}</span>
                </div>`;
                html += `<div class="info-row">
                    <span class="info-label">Type:</span>
                    <span class="info-value">${{node.data.transition_type}}</span>
                </div>`;
                if (Object.keys(node.data.arguments || {{}}).length > 0) {{
                    html += `<div class="info-row">
                        <span class="info-label">Arguments:</span>
                    </div>`;
                    html += '<div style="margin-left: 10px; font-size: 11px; color: #555;">';
                    for (const [key, val] of Object.entries(node.data.arguments)) {{
                        html += `<div>${{key}}: ${{JSON.stringify(val)}}</div>`;
                    }}
                    html += '</div>';
                }}
            }}
            
            content.innerHTML = html;
            info.style.display = 'block';
        }}
        
        function showEdgeInfo(edge) {{
            const info = document.getElementById('info');
            const title = document.getElementById('infoTitle');
            const content = document.getElementById('infoContent');
            
            title.textContent = 'Arc';
            
            let html = `<div class="info-row">
                <span class="info-label">From:</span>
                <span class="info-value">${{edge.from_name || edge.from}}</span>
            </div>`;
            html += `<div class="info-row">
                <span class="info-label">To:</span>
                <span class="info-value">${{edge.to_name || edge.to}}</span>
            </div>`;
            html += `<div class="info-row">
                <span class="info-label">Weight:</span>
                <span class="info-value">${{edge.weight || 1}}</span>
            </div>`;
            
            content.innerHTML = html;
            info.style.display = 'block';
        }}
        
        function hideInfo() {{
            document.getElementById('info').style.display = 'none';
        }}
        
        function toggleReads() {{
            const show = document.getElementById('showReads').checked;
            
            nodesData.forEach(node => {{
                if (node.is_read_transition) {{
                    nodes.update({{id: node.id, hidden: !show}});
                    if (show) {{
                        hiddenElements.reads.delete(node.id);
                    }} else {{
                        hiddenElements.reads.add(node.id);
                    }}
                }}
            }});
            
            edgesData.forEach(edge => {{
                if (edge.is_read_edge) {{
                    edges.update({{id: edge.id, hidden: !show}});
                }}
            }});
            
            updateStats();
        }}
        
        function toggleReservations() {{
            const show = document.getElementById('showReservations').checked;
            
            nodesData.forEach(node => {{
                if (node.is_reservation_place) {{
                    nodes.update({{id: node.id, hidden: !show}});
                    if (show) {{
                        hiddenElements.reservations.delete(node.id);
                    }} else {{
                        hiddenElements.reservations.add(node.id);
                    }}
                }}
            }});
            
            updateStats();
        }}
        
        function changeLayout() {{
            const layout = document.getElementById('layoutSelect').value;
            let direction = 'LR';
            
            if (layout === 'hierarchical_td') {{
                direction = 'UD';
            }} else if (layout === 'hierarchical_du') {{
                direction = 'DU';
            }}
            
            network.setOptions({{
                layout: {{
                    hierarchical: {{
                        direction: direction,
                        sortMethod: 'directed',
                        nodeSpacing: 150,
                        levelSeparation: 250,
                        treeSpacing: 200,
                        blockShifting: true,
                        edgeMinimization: true
                    }}
                }},
                physics: {{ enabled: false }}
            }});
            
            setTimeout(() => fitNetwork(), 100);
        }}
        
        function fitNetwork() {{
            network.fit({{
                animation: {{
                    duration: 600,
                    easingFunction: 'easeInOutQuad'
                }}
            }});
        }}
        
        function toggleLegend() {{
            const legend = document.getElementById('legend');
            legend.style.display = legend.style.display === 'none' ? 'block' : 'none';
        }}
        
        function toggleStats() {{
            const stats = document.getElementById('stats');
            stats.style.display = stats.style.display === 'none' ? 'block' : 'none';
        }}
        
        function updateStats() {{
            const places = nodesData.filter(n => n.data.type === 'place');
            const transitions = nodesData.filter(n => n.data.type === 'transition');
            const totalTokens = places.reduce((sum, p) => sum + (p.data.tokens || 0), 0);
            
            const visibleNodes = nodesData.filter(n => 
                !hiddenElements.reads.has(n.id) && 
                !hiddenElements.reservations.has(n.id)
            ).length;
            
            document.getElementById('numPlaces').textContent = places.length;
            document.getElementById('numTransitions').textContent = transitions.length;
            document.getElementById('numArcs').textContent = edgesData.length;
            document.getElementById('numTokens').textContent = totalTokens;
            document.getElementById('numVisible').textContent = visibleNodes;
        }}
        
        // Setup event listeners
        document.getElementById('showReads').addEventListener('change', toggleReads);
        document.getElementById('showReservations').addEventListener('change', toggleReservations);
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'f' || e.key === 'F') {{
                fitNetwork();
            }} else if (e.key === 'l' || e.key === 'L') {{
                toggleLegend();
            }} else if (e.key === 's' || e.key === 'S') {{
                toggleStats();
            }} else if (e.key === 'Escape') {{
                hideInfo();
            }}
        }});
        
        // Initial setup
        toggleReads();
        toggleReservations();
        updateStats();
        
        setTimeout(() => {{
            fitNetwork();
        }}, 200);
        
        console.log('Petri Net loaded successfully!');
        console.log('Shortcuts: F=fit, L=legend, S=stats, ESC=close info');
    </script>
</body>
</html>
"""


def net_to_visjs_proper_petri_net(net):
    """
    Convert to proper Petri net visualization:
    - Places = circles with token dots
    - Transitions = rectangles  
    - Traditional Petri net appearance
    """
    nodes = []
    edges = []
    edge_id = 0
    
    # Process places - traditional circles with tokens
    for name, place in net.places.items():
        # Determine place type
        if "_state_" in name:
            place_type = "Agent State"
            color_bg = "#e8f4fd"
            color_border = "#4a90e2"
        elif "_available" in name:
            place_type = "Resource (Available)"
            color_bg = "#fff8e1"
            color_border = "#ffa726"
        elif "_reserved_by_" in name:
            place_type = "Resource (Reserved)"
            color_bg = "#fff3e0"
            color_border = "#ff9800"
        else:
            place_type = "Place"
            color_bg = "#ffffff"
            color_border = "#2c3e50"
        
        # Create label with token count
        tokens = place.tokens
        capacity_str = f"/{place.capacity}" if place.capacity is not None else ""
        
        # For places with tokens, show black dots inside
        # For proper Petri nets, we show small name + token count
        short_name = name.replace("_available", "").replace("_state_", "_S").replace("_reserved_by_", "_rsv_")
        if len(short_name) > 20:
            short_name = short_name[:17] + "..."
        
        label = f"{short_name}\\n"
        if tokens > 0:
            if tokens <= 5:
                label += "●" * tokens
            else:
                label += f"● × {tokens}"
        else:
            label += "○"  # Empty
        
        if capacity_str:
            label += f"  {capacity_str}"
        
        node = {
            "id": name,
            "label": label,
            "shape": "circle",
            "size": 35 if tokens > 0 else 30,
            "color": {
                "background": color_bg,
                "border": color_border,
                "highlight": {
                    "background": color_bg,
                    "border": "#e74c3c"
                }
            },
            "borderWidth": 2.5 if tokens > 0 else 2,
            "font": {
                "size": 11 if tokens > 0 else 10,
                "multi": True,
                "bold": tokens > 0
            },
            "is_reservation_place": "_reserved_by_" in name,
            "data": {
                "type": "place",
                "original_name": name,
                "tokens": tokens,
                "capacity": place.capacity,
                "place_type": place_type
            }
        }
        
        nodes.append(node)
    
    # Process transitions - traditional rectangles
    for t in net.transitions:
        is_read = t.transition_type.value == "read"
        
        # Create label
        label = t.function_name.replace("_", " ")
        if len(label) > 15:
            label = label[:12] + "..."
        
        # Traditional black rectangle for transitions
        node = {
            "id": t.name,
            "label": label,
            "shape": "box",
            "size": 20,
            "color": {
                "background": "#bdc3c7" if is_read else "#34495e",
                "border": "#95a5a6" if is_read else "#2c3e50",
                "highlight": {
                    "background": "#e74c3c",
                    "border": "#c0392b"
                }
            },
            "borderWidth": 2,
            "font": {
                "color": "#ecf0f1" if not is_read else "#2c3e50",
                "size": 11,
                "bold": not is_read
            },
            "is_read_transition": is_read,
            "data": {
                "type": "transition",
                "transition_name": t.name,
                "agent_id": t.agent_id,
                "function": t.function_name,
                "arguments": t.arguments,
                "transition_type": t.transition_type.value
            }
        }
        
        nodes.append(node)
        
        # Create arcs (edges)
        for place, weight in t.input_places.items():
            edge = {
                "id": edge_id,
                "from": place,
                "to": t.name,
                "width": 2,
                "weight": weight,
                "from_name": place,
                "to_name": t.name,
                "is_read_edge": is_read
            }
            
            if weight > 1:
                edge["label"] = str(weight)
                edge["font"] = {"size": 12, "strokeWidth": 3, "strokeColor": "#ffffff"}
            
            edges.append(edge)
            edge_id += 1
        
        for place, weight in t.output_places.items():
            edge = {
                "id": edge_id,
                "from": t.name,
                "to": place,
                "width": 2,
                "weight": weight,
                "from_name": t.name,
                "to_name": place,
                "is_read_edge": is_read
            }
            
            if weight > 1:
                edge["label"] = str(weight)
                edge["font"] = {"size": 12, "strokeWidth": 3, "strokeColor": "#ffffff"}
            
            # Check for self-loop (read transitions often have these)
            if place in t.input_places:
                edge["dashes"] = [8, 4]
                edge["color"] = {"color": "#7f8c8d"}
            
            edges.append(edge)
            edge_id += 1
    
    return nodes, edges


def main():
    ap = argparse.ArgumentParser(
        description="Generate proper Petri net visualization with traditional notation"
    )
    ap.add_argument("task_id", help="Task ID to visualize")
    ap.add_argument("--out", default="output/petri_net_proper.html", help="Output HTML file")
    args = ap.parse_args()
    
    try:
        from prompt_registry import get_task
        from petri_nets.petri_net_builder import build_petri_net_from_spec
    except ImportError as e:
        print(f"Error importing: {e}")
        sys.exit(1)
    
    task = get_task(args.task_id)
    net = build_petri_net_from_spec(task["spec"])
    
    nodes, edges = net_to_visjs_proper_petri_net(net)
    
    html = HTML_TEMPLATE.format(
        title=task["name"],
        description=task.get("description", ""),
        nodes_json=json.dumps(nodes, indent=2),
        edges_json=json.dumps(edges, indent=2)
    )
    
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print("✓ Proper Petri Net visualization created: {out_path}")
    print("\n✨ Traditional Petri Net Features:")
    print("  • Places = Circles with token dots (●)")
    print("  • Transitions = Rectangles (black boxes)")
    print("  • Arcs = Arrows showing token flow")
    print("  • Token counts visible in places")
    print("  • Capacity shown where applicable")
    print("  • Read transitions hidden by default (toggle to show)")
    print("\n📊 Statistics panel shows:")
    print("  • Number of places, transitions, arcs")
    print("  • Total tokens in the system")
    print("  • Visible elements count")
    print("\n🎮 Interactive features:")
    print("  • Click places/transitions for details")
    print("  • Toggle reads and reservations")
    print("  • Multiple layout directions")
    print("  • Keyboard shortcuts: F=fit, L=legend, S=stats")
    print("\n📂 Open in browser:")
    print("  file://{out_path.absolute()}")


if __name__ == "__main__":
    main()