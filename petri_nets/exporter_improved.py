# petri_nets/exporter_improved.py
"""
Improved Petri Net visualization with clearer layouts and better readability.
"""
from __future__ import annotations
from typing import List, Optional
from petri_nets.petri_net import PetriNet, TransitionType

def escape(s: str) -> str:
    return s.replace('"', r'\"').replace('\n', '\\n')

def _is_agent_state(place_name: str) -> bool:
    return "_state_" in place_name

def _agent_of_state(place_name: str) -> Optional[str]:
    if "_state_" in place_name:
        return place_name.split("_state_")[0]
    return None

def _extract_state_num(place_name: str) -> int:
    """Extract state number from place like 'rover_1_state_3' -> 3"""
    if "_state_" in place_name:
        try:
            return int(place_name.split("_state_")[1])
        except:
            return 0
    return 0

def to_dot_horizontal(
    net: PetriNet,
    title: str = "Petri Net",
    *,
    hide_reads: bool = True,
    show_token_counts: bool = True,
    compact_resources: bool = True,
) -> str:
    """
    Horizontal layout: Agents flow left-to-right, resources at top.
    Best for showing temporal progression.
    """
    lines: List[str] = []
    lines.append('digraph G {')
    lines.append('  rankdir=LR;')
    lines.append('  ranksep=1.2;')
    lines.append('  nodesep=0.6;')
    lines.append('  labelloc="t";')
    lines.append(f'  label="{escape(title)}";')
    lines.append('  fontsize=16;')
    lines.append('  node [fontsize=11];')
    lines.append('  edge [fontsize=9];')
    lines.append('')
    
    # Categorize places
    agent_places = {}
    resource_avail = []
    resource_reserved = []
    
    for name, place in net.places.items():
        if "_available" in name:
            resource_avail.append((name, place))
        elif "_reserved_by_" in name:
            resource_reserved.append((name, place))
        else:
            ag = _agent_of_state(name)
            if ag:
                agent_places.setdefault(ag, []).append((name, place))
    
    # Resources cluster at top (compact if requested)
    if compact_resources:
        lines.append('  subgraph cluster_resources {')
        lines.append('    label="Shared Resources";')
        lines.append('    color="#E6B422";')
        lines.append('    style="rounded,filled";')
        lines.append('    fillcolor="#FFFEF0";')
        lines.append('    rank=source;')
        lines.append('')
        
        # Only show available resources in compact mode
        for name, place in resource_avail:
            resource_name = name.replace("_available", "")
            tok = place.tokens if show_token_counts else ""
            cap = f"/{place.capacity}" if place.capacity else ""
            label = f"{resource_name}\\n[{tok}{cap}]" if tok or cap else resource_name
            lines.append(
                f'    "{escape(name)}" [shape=cylinder, style="filled", '
                f'fillcolor="#FFE699", label="{escape(label)}"];'
            )
        lines.append('  }')
    else:
        # Full resource view with reservations
        lines.append('  subgraph cluster_resources {')
        lines.append('    label="Resource Pool";')
        lines.append('    color="#E6B422";')
        lines.append('    style="rounded,filled";')
        lines.append('    fillcolor="#FFFEF0";')
        lines.append('')
        
        for name, place in resource_avail + resource_reserved:
            tok = place.tokens if show_token_counts else ""
            cap = f"/{place.capacity}" if place.capacity else ""
            label_cap = f" [{tok}{cap}]" if tok or cap else ""
            shape = "cylinder" if "_available" in name else "circle"
            color = "#FFE699" if "_available" in name else "#FFF2CC"
            lines.append(
                f'    "{escape(name)}" [shape={shape}, style="filled", '
                f'fillcolor="{color}", label="{escape(name)}{escape(label_cap)}"];'
            )
        lines.append('  }')
    
    lines.append('')
    
    # Agent DFA chains (horizontal)
    for agent, places in sorted(agent_places.items()):
        lines.append(f'  subgraph cluster_{escape(agent)} {{')
        lines.append(f'    label="{escape(agent)}";')
        lines.append('    color="#6FA8DC";')
        lines.append('    style="rounded,filled";')
        lines.append('    fillcolor="#E8F4FD";')
        lines.append('    rank=same;')
        lines.append('')
        
        # Sort by state number
        places_sorted = sorted(places, key=lambda x: _extract_state_num(x[0]))
        
        # Force horizontal ordering
        if len(places_sorted) > 1:
            place_names = [f'"{escape(p[0])}"' for p in places_sorted]
            lines.append(f'    {{ rank=same; {" -> ".join(place_names)} [style=invis]; }}')
        
        for name, place in places_sorted:
            state_num = _extract_state_num(name)
            tok = "●" if place.tokens > 0 else ""
            label = f"S{state_num}\\n{tok}" if tok else f"S{state_num}"
            
            color = "#4A90E2" if place.tokens > 0 else "#B3D9FF"
            penwidth = "2.0" if place.tokens > 0 else "1.0"
            
            lines.append(
                f'    "{escape(name)}" [shape=circle, style="filled", '
                f'fillcolor="{color}", penwidth={penwidth}, label="{escape(label)}"];'
            )
        
        lines.append('  }')
        lines.append('')
    
    # Transitions
    lines.append('  // Transitions')
    for t in net.transitions:
        if hide_reads and t.transition_type == TransitionType.READ:
            continue
        
        if t.transition_type == TransitionType.READ:
            style = 'dashed,filled'
            fill = '#E8E8E8'
        else:
            style = 'solid,filled'
            fill = '#B7DEE8'
        
        # Compact label
        label = f'{t.function_name}'
        
        lines.append(
            f'  "{escape(t.name)}" [shape=box, style="{style}", '
            f'fillcolor="{fill}", penwidth=1.0, label="{escape(label)}", '
            f'width=1.2, height=0.5];'
        )
    
    lines.append('')
    
    # Arcs
    lines.append('  // Arcs')
    for t in net.transitions:
        if hide_reads and t.transition_type == TransitionType.READ:
            continue
        
        for p, w in t.input_places.items():
            lbl = f' [label="{w}"]' if w > 1 else ''
            lines.append(f'  "{escape(p)}" -> "{escape(t.name)}"{lbl};')
        
        for p, w in t.output_places.items():
            lbl = f' [label="{w}"]' if w > 1 else ''
            # Check if it's a self-loop (same place in input and output)
            if p in t.input_places:
                lines.append(f'  "{escape(t.name)}" -> "{escape(p)}"{lbl} [constraint=false];')
            else:
                lines.append(f'  "{escape(t.name)}" -> "{escape(p)}"{lbl};')
    
    lines.append('}')
    return "\n".join(lines)


def to_dot_vertical(
    net: PetriNet,
    title: str = "Petri Net",
    *,
    hide_reads: bool = True,
    show_token_counts: bool = True,
) -> str:
    """
    Vertical layout: Top-to-bottom flow.
    Best for showing hierarchical structure.
    """
    lines: List[str] = []
    lines.append('digraph G {')
    lines.append('  rankdir=TB;')
    lines.append('  ranksep=0.8;')
    lines.append('  nodesep=0.5;')
    lines.append('  labelloc="t";')
    lines.append(f'  label="{escape(title)}";')
    lines.append('  fontsize=16;')
    lines.append('  node [fontsize=10];')
    lines.append('  edge [fontsize=8];')
    lines.append('')
    
    # Categorize places
    agent_places = {}
    resource_places = []
    
    for name, place in net.places.items():
        if "_available" in name or "_reserved_by_" in name:
            resource_places.append((name, place))
        else:
            ag = _agent_of_state(name)
            if ag:
                agent_places.setdefault(ag, []).append((name, place))
    
    # Resources at top
    lines.append('  subgraph cluster_resources {')
    lines.append('    label="Resources";')
    lines.append('    color="#E6B422";')
    lines.append('    style="rounded,filled";')
    lines.append('    fillcolor="#FFFEF0";')
    lines.append('    rank=source;')
    lines.append('')
    
    for name, place in resource_places:
        tok = place.tokens if show_token_counts else ""
        cap = f"/{place.capacity}" if place.capacity else ""
        label_cap = f" [{tok}{cap}]" if tok or cap else ""
        shape = "cylinder" if "_available" in name else "circle"
        color = "#FFE699" if "_available" in name else "#FFF2CC"
        
        # Shorten label
        short_name = name.replace("_available", "").replace("_reserved_by_", "_rsv_")
        lines.append(
            f'    "{escape(name)}" [shape={shape}, style="filled", '
            f'fillcolor="{color}", label="{escape(short_name)}{escape(label_cap)}"];'
        )
    
    lines.append('  }')
    lines.append('')
    
    # Agent states side by side
    lines.append('  {')
    lines.append('    rank=same;')
    for agent in sorted(agent_places.keys()):
        lines.append(f'    cluster_{escape(agent)}_anchor;')
    lines.append('  }')
    lines.append('')
    
    for agent, places in sorted(agent_places.items()):
        lines.append(f'  subgraph cluster_{escape(agent)} {{')
        lines.append(f'    label="{escape(agent)}";')
        lines.append('    color="#6FA8DC";')
        lines.append('    style="rounded,filled";')
        lines.append('    fillcolor="#E8F4FD";')
        lines.append('')
        
        places_sorted = sorted(places, key=lambda x: _extract_state_num(x[0]))
        
        for name, place in places_sorted:
            state_num = _extract_state_num(name)
            tok = "●" if place.tokens > 0 else ""
            label = f"S{state_num}\\n{tok}" if tok else f"S{state_num}"
            
            color = "#4A90E2" if place.tokens > 0 else "#B3D9FF"
            penwidth = "2.0" if place.tokens > 0 else "1.0"
            
            lines.append(
                f'    "{escape(name)}" [shape=circle, style="filled", '
                f'fillcolor="{color}", penwidth={penwidth}, label="{escape(label)}"];'
            )
        
        lines.append('  }')
        lines.append('')
    
    # Transitions
    lines.append('  // Transitions')
    for t in net.transitions:
        if hide_reads and t.transition_type == TransitionType.READ:
            continue
        
        style = 'dashed,filled' if t.transition_type == TransitionType.READ else 'solid,filled'
        fill = '#E8E8E8' if t.transition_type == TransitionType.READ else '#B7DEE8'
        label = f'{t.function_name}'
        
        lines.append(
            f'  "{escape(t.name)}" [shape=box, style="{style}", '
            f'fillcolor="{fill}", label="{escape(label)}", height=0.4];'
        )
    
    lines.append('')
    
    # Arcs
    for t in net.transitions:
        if hide_reads and t.transition_type == TransitionType.READ:
            continue
        
        for p, w in t.input_places.items():
            lbl = f' [label="{w}"]' if w > 1 else ''
            lines.append(f'  "{escape(p)}" -> "{escape(t.name)}"{lbl};')
        
        for p, w in t.output_places.items():
            lbl = f' [label="{w}"]' if w > 1 else ''
            lines.append(f'  "{escape(t.name)}" -> "{escape(p)}"{lbl};')
    
    lines.append('}')
    return "\n".join(lines)


def to_dot_simplified(
    net: PetriNet,
    title: str = "Petri Net (Simplified)",
    *,
    show_token_counts: bool = True,
) -> str:
    """
    Highly simplified view: Only show the DFA backbone and critical resources.
    Hides all read transitions and reservation places.
    """
    lines: List[str] = []
    lines.append('digraph G {')
    lines.append('  rankdir=LR;')
    lines.append('  ranksep=1.5;')
    lines.append('  nodesep=0.8;')
    lines.append('  labelloc="t";')
    lines.append(f'  label="{escape(title)}";')
    lines.append('  fontsize=16;')
    lines.append('  node [fontsize=12];')
    lines.append('  edge [fontsize=10];')
    lines.append('')
    
    # Only show: agent states + available resources
    agent_places = {}
    resource_avail = []
    
    for name, place in net.places.items():
        if "_available" in name:
            resource_avail.append((name, place))
        elif "_state_" in name:
            ag = _agent_of_state(name)
            if ag:
                agent_places.setdefault(ag, []).append((name, place))
    
    # Resources
    if resource_avail:
        lines.append('  subgraph cluster_resources {')
        lines.append('    label="Resources";')
        lines.append('    color="#E6B422";')
        lines.append('    style="rounded,filled";')
        lines.append('    fillcolor="#FFFEF0";')
        lines.append('')
        
        for name, place in resource_avail:
            resource_name = name.replace("_available", "")
            tok = place.tokens if show_token_counts else ""
            cap = f"/{place.capacity}" if place.capacity else ""
            label = f"{resource_name}\\n[{tok}{cap}]"
            
            lines.append(
                f'    "{escape(name)}" [shape=cylinder, style="filled", '
                f'fillcolor="#FFE699", label="{escape(label)}", fontsize=11];'
            )
        
        lines.append('  }')
        lines.append('')
    
    # Agents
    for agent, places in sorted(agent_places.items()):
        lines.append(f'  subgraph cluster_{escape(agent)} {{')
        lines.append(f'    label="{escape(agent)}";')
        lines.append('    color="#6FA8DC";')
        lines.append('    style="rounded,filled";')
        lines.append('    fillcolor="#E8F4FD";')
        lines.append('')
        
        places_sorted = sorted(places, key=lambda x: _extract_state_num(x[0]))
        
        for name, place in places_sorted:
            state_num = _extract_state_num(name)
            tok = "●" if place.tokens > 0 else ""
            label = f"S{state_num}\\n{tok}" if tok else f"S{state_num}"
            
            color = "#4A90E2" if place.tokens > 0 else "#B3D9FF"
            penwidth = "2.5" if place.tokens > 0 else "1.5"
            
            lines.append(
                f'    "{escape(name)}" [shape=circle, style="filled", '
                f'fillcolor="{color}", penwidth={penwidth}, label="{escape(label)}", '
                f'width=0.6, height=0.6];'
            )
        
        lines.append('  }')
        lines.append('')
    
    # Only PROGRESS transitions
    lines.append('  // Transitions (progress only)')
    for t in net.transitions:
        if t.transition_type != TransitionType.PROGRESS:
            continue
        
        label = f'{t.function_name}'
        lines.append(
            f'  "{escape(t.name)}" [shape=box, style="filled", '
            f'fillcolor="#B7DEE8", label="{escape(label)}", '
            f'width=1.5, height=0.6];'
        )
    
    lines.append('')
    
    # Arcs (only for progress transitions)
    for t in net.transitions:
        if t.transition_type != TransitionType.PROGRESS:
            continue
        
        for p, w in t.input_places.items():
            # Only show if place is visible (agent state or available resource)
            if "_state_" in p or "_available" in p:
                lbl = f' [label="{w}", fontsize=10]' if w > 1 else ' [penwidth=1.5]'
                lines.append(f'  "{escape(p)}" -> "{escape(t.name)}"{lbl};')
        
        for p, w in t.output_places.items():
            if "_state_" in p or "_available" in p:
                lbl = f' [label="{w}", fontsize=10]' if w > 1 else ' [penwidth=1.5]'
                lines.append(f'  "{escape(t.name)}" -> "{escape(p)}"{lbl};')
    
    lines.append('}')
    return "\n".join(lines)


# Legacy wrapper for backward compatibility
def to_dot(net: PetriNet, title: str = "Petri Net", **kwargs) -> str:
    """Default to horizontal layout"""
    return to_dot_horizontal(net, title, **kwargs)