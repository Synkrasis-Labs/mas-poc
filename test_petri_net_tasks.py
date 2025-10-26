# test_petri_net_tasks.py
"""
Test Petri Net evaluation with synthetic agent execution traces.

This allows testing without making actual LLM calls.
"""

from typing import List, Tuple, Dict, Any
from petri_nets.petri_net_builder import build_petri_net_from_spec
from petri_nets.replayer import PetriNetReplayer
from petri_nets.metrics import compute_mas_core_metrics
from prompts import get_task


def create_perfect_execution(task_id: str) -> List[Tuple[str, str, Dict[str, Any]]]:
    """Create a perfect execution trace for a task"""
    
    task = get_task(task_id)
    spec = task['spec']
    
    execution = []
    
    if task_id == "two_rover_harvest":
        # Interleaved execution: both start, rover_1 uses bin first
        execution = [
            # Both unlock
            ("rover_1", "unlock_safety_mode", {}),
            ("rover_2", "unlock_safety_mode", {}),
            
            # Both reserve plants
            ("rover_1", "reserve_plant", {"plant_id": "plant_A"}),
            ("rover_2", "reserve_plant", {"plant_id": "plant_C"}),
            
            # Both move and harvest (parallel)
            ("rover_1", "move_to", {"x": 2.0, "y": 14.0}),
            ("rover_2", "move_to", {"x": 14.0, "y": 8.5}),
            
            ("rover_1", "harvest_fruit", {"plant_id": "plant_A"}),
            ("rover_2", "harvest_fruit", {"plant_id": "plant_C"}),
            
            ("rover_1", "release_plant", {"plant_id": "plant_A"}),
            ("rover_2", "release_plant", {"plant_id": "plant_C"}),
            
            # Rover 1 uses bin first
            ("rover_1", "reserve_station", {"station_name": "collection_bin"}),
            ("rover_1", "move_to", {"x": 18.0, "y": 18.0}),
            ("rover_1", "dump_hopper", {}),
            ("rover_1", "release_station", {"station_name": "collection_bin"}),
            
            # Now rover 2 can use bin
            ("rover_2", "reserve_station", {"station_name": "collection_bin"}),
            ("rover_2", "move_to", {"x": 18.0, "y": 18.0}),
            ("rover_2", "dump_hopper", {}),
            ("rover_2", "release_station", {"station_name": "collection_bin"}),
            
            # Both go home
            ("rover_1", "move_home", {}),
            ("rover_2", "move_home", {}),
            
            ("rover_1", "lock_safety_mode", {}),
            ("rover_2", "lock_safety_mode", {}),
        ]
    
    elif task_id == "three_rover_mixed":
        # All three rovers work in parallel
        execution = [
            # All unlock
            ("rover_1", "unlock_safety_mode", {}),
            ("rover_2", "unlock_safety_mode", {}),
            ("rover_3", "unlock_safety_mode", {}),
            
            # All reserve their plants
            ("rover_1", "reserve_plant", {"plant_id": "plant_A"}),
            ("rover_2", "reserve_plant", {"plant_id": "plant_D"}),
            ("rover_3", "reserve_plant", {"plant_id": "plant_B"}),
            
            # All move to plants
            ("rover_1", "move_to", {"x": 2.0, "y": 14.0}),
            ("rover_2", "move_to", {"x": 16.5, "y": 15.0}),
            ("rover_3", "move_to", {"x": 3.5, "y": 12.5}),
            
            # All perform operations
            ("rover_1", "harvest_fruit", {"plant_id": "plant_A"}),
            ("rover_2", "water_plant", {"plant_id": "plant_D", "liters": 3.0}),
            ("rover_3", "spray_pesticide", {"plant_id": "plant_B", "ml": 50.0}),
            
            # All release plants
            ("rover_1", "release_plant", {"plant_id": "plant_A"}),
            ("rover_2", "release_plant", {"plant_id": "plant_D"}),
            ("rover_3", "release_plant", {"plant_id": "plant_B"}),
            
            # Rover 1 goes to bin
            ("rover_1", "reserve_station", {"station_name": "collection_bin"}),
            ("rover_1", "move_to", {"x": 18.0, "y": 18.0}),
            ("rover_1", "dump_hopper", {}),
            ("rover_1", "release_station", {"station_name": "collection_bin"}),
            
            # All go home
            ("rover_1", "move_home", {}),
            ("rover_2", "move_home", {}),
            ("rover_3", "move_home", {}),
            
            ("rover_1", "lock_safety_mode", {}),
            ("rover_2", "lock_safety_mode", {}),
            ("rover_3", "lock_safety_mode", {}),
        ]
    
    else:
        # Fall back to sequential execution from spec
        for agent_id, constraints in spec.agent_constraints.items():
            for func_name, args in constraints.required_sequence:
                execution.append((agent_id, func_name, args))
    
    return execution


def create_faulty_execution(task_id: str, fault_type: str) -> List[Tuple[str, str, Dict[str, Any]]]:
    """Create a faulty execution trace with specific error patterns"""
    
    # Start with perfect execution
    execution = create_perfect_execution(task_id)
    
    if fault_type == "reservation_conflict":
        # Rover 2 tries to reserve plant_A (already reserved by rover_1)
        # Insert conflict after rover_1 reserves
        for i, (agent, func, args) in enumerate(execution):
            if agent == "rover_1" and func == "reserve_plant" and args.get("plant_id") == "plant_A":
                # Insert rover_2's conflicting reservation right after
                execution.insert(i + 1, ("rover_2", "reserve_plant", {"plant_id": "plant_A"}))
                break
    
    elif fault_type == "missing_reservation":
        # Rover_1 harvests without reserving first
        # Remove the reserve_plant call
        execution = [
            (agent, func, args)
            for agent, func, args in execution
            if not (agent == "rover_1" and func == "reserve_plant" and args.get("plant_id") == "plant_A")
        ]
    
    elif fault_type == "missing_release":
        # Rover_1 doesn't release collection_bin
        execution = [
            (agent, func, args)
            for agent, func, args in execution
            if not (agent == "rover_1" and func == "release_station" and args.get("station_name") == "collection_bin")
        ]
    
    elif fault_type == "wrong_order":
        # Rover_1 tries to dump before reserving bin
        # Find dump_hopper and reserve_station, swap them
        for i, (agent, func, args) in enumerate(execution):
            if agent == "rover_1" and func == "reserve_station":
                # Find next dump_hopper
                for j in range(i + 1, len(execution)):
                    if execution[j][0] == "rover_1" and execution[j][1] == "dump_hopper":
                        # Swap
                        execution[i], execution[j] = execution[j], execution[i]
                        break
                break
    
    return execution


def test_task(task_id: str, execution_type: str = "perfect"):
    """Test a single task with specified execution type"""
    
    print("\n" + "=" * 80)
    print(f"TESTING TASK: {task_id}")
    print(f"Execution type: {execution_type}")
    print("=" * 80)
    
    # Get task
    task = get_task(task_id)
    print(f"\nTask: {task['name']}")
    print(f"Description: {task['description']}")
    print(f"Agents: {', '.join(task['agents'])}")
    
    # Create execution trace
    if execution_type == "perfect":
        execution = create_perfect_execution(task_id)
    else:
        execution = create_faulty_execution(task_id, execution_type)
    
    print(f"\nExecution trace: {len(execution)} actions")
    
    # Build Petri Net
    print("\nBuilding Petri Net from specification...")
    spec = task['spec']
    petri_net = build_petri_net_from_spec(spec)
    
    print(f"  Places: {len(petri_net.places)}")
    print(f"  Transitions: {len(petri_net.transitions)}")
    
    # Replay execution
    print("\nReplaying execution on Petri Net...")
    replayer = PetriNetReplayer(petri_net)
    replay_result = replayer.replay(execution)
    
    print(f"  Transitions fired: {len(replay_result.fired_transitions)}")
    print(f"  Harmful events: {len(replay_result.harmful_events)}")
    
    # Show harmful events
    if replay_result.harmful_events:
        print("\n⚠️  HARMFUL EVENTS:")
        for event in replay_result.harmful_events[:5]:  # Show first 5
            print(f"  Step {event.timestep}: {event.agent_id}.{event.function_name}()")
            print(f"    Reason: {event.reason}")
        if len(replay_result.harmful_events) > 5:
            print(f"  ... and {len(replay_result.harmful_events) - 5} more")
    else:
        print("\n✓ No harmful events!")
    
    # Compute metrics
    print("\nComputing MAS-CORE metrics...")
    metrics = compute_mas_core_metrics(replay_result, spec)
    
    # Display results
    print("\n" + "-" * 80)
    print("METRICS:")
    print("-" * 80)
    print(f"Path Correctness (Overall):    {metrics['path_correctness']:.3f}")
    print(f"Harmful Rate:                  {metrics['harmful_rate']:.3f}")
    print(f"Harmful-Free Score:            {metrics['harmful_free']:.3f}")
    print(f"Prefix Criticality:            {metrics['prefix_criticality']:.3f}")
    print(f"Efficiency:                    {metrics['efficiency']:.3f}")
    print(f"Coordination Score:            {metrics['coordination_score']:.3f}")
    print(f"Parallelism Utilization:       {metrics['parallelism_utilization']:.3f}")
    
    print("\nPer-Agent Path Correctness:")
    for agent_id, pc in metrics['path_correctness_per_agent'].items():
        print(f"  {agent_id}: {pc:.3f}")
    
    # Check agent completion
    print("\nAgent Completion Status:")
    final_marking = replay_result.get_marking_snapshot()
    for agent_id in task['agents']:
        final_state_place = f"{agent_id}_state_{len(spec.agent_constraints[agent_id].required_sequence)}"
        completed = final_state_place in final_marking and final_marking[final_state_place] > 0
        status = "✓ COMPLETED" if completed else "✗ INCOMPLETE"
        print(f"  {agent_id}: {status}")
    
    # Overall assessment
    print("\n" + "-" * 80)
    perfect = (
        metrics['harmful_rate'] == 0 and
        metrics['path_correctness'] >= 0.95 and
        metrics['coordination_score'] >= 0.95
    )
    print(f"Overall: {'✓ EXCELLENT' if perfect else '⚠️  NEEDS IMPROVEMENT'}")
    print("-" * 80)
    
    return {
        "task_id": task_id,
        "execution_type": execution_type,
        "metrics": metrics,
        "replay_result": replay_result,
        "perfect": perfect
    }


def run_comprehensive_test():
    """Run comprehensive test suite"""
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE MAS-CORE PETRI NET TEST SUITE")
    print("=" * 80)
    
    results = []
    
    # Test each task with different execution types
    test_scenarios = [
        ("two_rover_harvest", "perfect"),
        ("two_rover_harvest", "reservation_conflict"),
        ("two_rover_harvest", "missing_release"),
        ("three_rover_mixed", "perfect"),
        ("three_rover_mixed", "wrong_order"),
    ]
    
    for task_id, exec_type in test_scenarios:
        try:
            result = test_task(task_id, exec_type)
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary table
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    print(f"\n{'Task':<25} {'Type':<20} {'PC':<8} {'Harm':<8} {'Coord':<8} {'Status':<10}")
    print("-" * 85)
    
    for result in results:
        m = result['metrics']
        status = "✓ PASS" if result['perfect'] else "⚠️  FAIL"
        print(f"{result['task_id']:<25} {result['execution_type']:<20} "
              f"{m['path_correctness']:<8.3f} {m['harmful_rate']:<8.3f} "
              f"{m['coordination_score']:<8.3f} {status:<10}")
    
    # Statistics
    total = len(results)
    passed = sum(1 for r in results if r['perfect'])
    
    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed ({100*passed/total:.1f}%)")
    print("=" * 80 + "\n")
    
    return results


def demo_single_task():
    """Demo a single task in detail"""
    print("\nDEMO: Two Rover Harvest Task")
    print("=" * 80)
    
    # Perfect execution
    print("\n1. Perfect Execution:")
    result_perfect = test_task("two_rover_harvest", "perfect")
    
    # Faulty execution
    print("\n\n2. Execution with Reservation Conflict:")
    result_conflict = test_task("two_rover_harvest", "reservation_conflict")
    
    # Compare
    print("\n\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    
    m1 = result_perfect['metrics']
    m2 = result_conflict['metrics']
    
    print(f"\n{'Metric':<30} {'Perfect':<15} {'With Conflict':<15}")
    print("-" * 60)
    print(f"{'Path Correctness':<30} {m1['path_correctness']:<15.3f} {m2['path_correctness']:<15.3f}")
    print(f"{'Harmful Rate':<30} {m1['harmful_rate']:<15.3f} {m2['harmful_rate']:<15.3f}")
    print(f"{'Coordination Score':<30} {m1['coordination_score']:<15.3f} {m2['coordination_score']:<15.3f}")
    print(f"{'Efficiency':<30} {m1['efficiency']:<15.3f} {m2['efficiency']:<15.3f}")
    
    print("\n" + "=" * 80)
    print("Key Insight:")
    print("  The reservation conflict is detected as a harmful event, lowering")
    print("  the coordination score and harmful-free score, while path correctness")
    print("  remains relatively high since the overall sequence structure is correct.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            run_comprehensive_test()
        elif sys.argv[1] == "demo":
            demo_single_task()
        else:
            # Test specific task
            task_id = sys.argv[1]
            exec_type = sys.argv[2] if len(sys.argv) > 2 else "perfect"
            test_task(task_id, exec_type)
    else:
        print("\nUsage:")
        print("  python test_petri_net_tasks.py all          # Run all tests")
        print("  python test_petri_net_tasks.py demo         # Run detailed demo")
        print("  python test_petri_net_tasks.py <task_id> [exec_type]")
        print("\nRunning demo by default...\n")
        demo_single_task()