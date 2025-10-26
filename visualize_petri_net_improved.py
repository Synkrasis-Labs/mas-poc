#!/usr/bin/env python3
# visualize_petri_net_improved.py
"""
Enhanced Petri Net visualization with multiple layout options.

Usage:
  python visualize_petri_net_improved.py two_rover_harvest
  python visualize_petri_net_improved.py two_rover_harvest --layout horizontal
  python visualize_petri_net_improved.py two_rover_harvest --layout vertical  
  python visualize_petri_net_improved.py two_rover_harvest --layout simplified
  python visualize_petri_net_improved.py two_rover_harvest --all-layouts
"""
import argparse
import pathlib
import sys

# Add parent directory to path to import modules
sys.path.insert(0, str(pathlib.Path(__file__).parent))

def _ensure_parent(path: str) -> None:
    p = pathlib.Path(path).expanduser()
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)


def main():
    ap = argparse.ArgumentParser(
        description="Visualize Petri Nets with improved layouts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Layout options:
  horizontal  : Agents flow left-to-right (default, best for temporal flow)
  vertical    : Agents flow top-to-bottom (hierarchical view)
  simplified  : Only DFA backbone + critical resources (clearest overview)
  
Examples:
  python visualize_petri_net_improved.py two_rover_harvest
  python visualize_petri_net_improved.py two_rover_harvest --layout simplified --png
  python visualize_petri_net_improved.py two_rover_harvest --all-layouts --png
        """
    )
    
    ap.add_argument("task_id", help="Task ID to visualize")
    ap.add_argument(
        "--layout",
        choices=["horizontal", "vertical", "simplified"],
        default="horizontal",
        help="Layout style (default: horizontal)"
    )
    ap.add_argument(
        "--all-layouts",
        action="store_true",
        help="Generate all three layouts"
    )
    ap.add_argument(
        "--out-dir",
        default="output",
        help="Output directory (default: output)"
    )
    ap.add_argument(
        "--show-reads",
        action="store_true",
        help="Show read transitions (can be cluttered)"
    )
    ap.add_argument(
        "--hide-tokens",
        action="store_true",
        help="Hide token counts"
    )
    ap.add_argument(
        "--png",
        action="store_true",
        help="Render PNG (requires Graphviz)"
    )
    ap.add_argument(
        "--svg",
        action="store_true",
        help="Render SVG (requires Graphviz)"
    )
    
    args = ap.parse_args()
    
    # Import after argparse so --help works even if imports fail
    try:
        from prompt_registry import get_task
        from petri_nets.petri_net_builder import build_petri_net_from_spec
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Make sure you're running from the correct directory.")
        sys.exit(1)
    
    # Load task
    try:
        task = get_task(args.task_id)
    except Exception as e:
        print(f"Error loading task '{args.task_id}': {e}")
        sys.exit(1)
    
    # Build Petri Net
    try:
        net = build_petri_net_from_spec(task["spec"])
    except Exception as e:
        print(f"Error building Petri Net: {e}")
        sys.exit(1)
    
    # Import exporters
    try:
        from petri_nets.exporter_improved import to_dot_horizontal, to_dot_vertical, to_dot_simplified
    except ImportError:
        print("Error: Could not import exporter_improved.py")
        print("Make sure exporter_improved.py is in the same directory or in petri_nets/")
        sys.exit(1)
    
    # Determine which layouts to generate
    if args.all_layouts:
        layouts = ["horizontal", "vertical", "simplified"]
    else:
        layouts = [args.layout]
    
    # Common params
    hide_reads = not args.show_reads
    show_tokens = not args.hide_tokens
    
    # Create output directory
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Task: {task['name']}")
    print(f"Output directory: {out_dir}")
    print(f"Layouts: {', '.join(layouts)}")
    print()
    
    for layout in layouts:
        # Generate DOT
        if layout == "horizontal":
            dot_content = to_dot_horizontal(
                net,
                title=f"{task['name']} (Horizontal)",
                hide_reads=hide_reads,
                show_token_counts=show_tokens,
                compact_resources=True
            )
        elif layout == "vertical":
            dot_content = to_dot_vertical(
                net,
                title=f"{task['name']} (Vertical)",
                hide_reads=hide_reads,
                show_token_counts=show_tokens
            )
        else:  # simplified
            dot_content = to_dot_simplified(
                net,
                title=f"{task['name']} (Simplified)",
                show_token_counts=show_tokens
            )
        
        # Write DOT file
        dot_path = out_dir / f"{args.task_id}_{layout}.dot"
        with open(dot_path, "w", encoding="utf-8") as f:
            f.write(dot_content)
        print(f"✓ Wrote {dot_path}")
        
        # Render images if requested
        if args.png or args.svg:
            try:
                from graphviz import Source
                src = Source(dot_content)
                
                if args.png:
                    png_path = out_dir / f"{args.task_id}_{layout}"
                    src.render(filename=str(png_path), format="png", cleanup=True)
                    print(f"✓ Wrote {png_path}.png")
                
                if args.svg:
                    svg_path = out_dir / f"{args.task_id}_{layout}"
                    src.render(filename=str(svg_path), format="svg", cleanup=True)
                    print(f"✓ Wrote {svg_path}.svg")
            
            except ImportError:
                print("\n⚠ Warning: graphviz module not installed.")
                print("  Install with: pip install graphviz")
                print("  You'll also need Graphviz system binary:")
                print("    - macOS: brew install graphviz")
                print("    - Ubuntu: sudo apt-get install graphviz")
                print("    - conda: conda install -c conda-forge graphviz python-graphviz")
            except Exception as e:
                print(f"\n⚠ Warning: Could not render {layout} layout: {e}")
    
    print("\n" + "="*60)
    print("Visualization complete!")
    print("="*60)
    print("\nQuick guide:")
    print("  • Horizontal layout: Best for seeing temporal progression")
    print("  • Vertical layout: Best for hierarchical structure")
    print("  • Simplified layout: Clearest overview (recommended first view)")
    print("\nLegend:")
    print("  • Circles with ● : Current agent state (has token)")
    print("  • Cylinders: Available resources")
    print("  • Boxes: Transitions (actions)")
    print("  • S0, S1, S2...: DFA states for each agent")


if __name__ == "__main__":
    main()