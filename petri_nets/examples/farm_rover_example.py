# petri_nets/examples/farm_rover_example.py
"""
Example: Two farm rovers harvesting different plants concurrently.

Prompt: "Rover 1 harvest plant_A. Rover 2 harvest plant_C. 
         Both must dump at collection_bin when done."
"""

from petri_nets.petri_net_spec import (
    PetriNetPrompt, 
    AgentConstraints, 
    ResourceConstraint
)
from petri_nets.replayer import PetriNetReplayer
from petri_nets.metrics import compute_mas_core_metrics


# Define the prompt specification
def create_harvest_prompt() -> PetriNetPrompt:
    """Create Petri Net specification for concurrent harvest task"""
    
    prompt = PetriNetPrompt(
        text=(
            "Rover 1: Unlock safety, move to plant_A, harvest plant_A, "
            "move to collection_bin, dump hopper. "
            "Rover 2: Unlock safety, move to plant_C, harvest plant_C, "
            "move to collection_bin, dump hopper."
        ),
        agents=["rover_1", "rover_2"],
        
        agent_constraints={
            "rover_1": AgentConstraints(
                agent_id="rover_1",
                required_sequence=[
                    ("unlock_safety_mode", {}),
                    ("move_to", {"x": 2.0, "y": 14.0}),  # plant_A location
                    ("reserve_plant", {"plant_id": "plant_A"}),
                    ("harvest_fruit", {"plant_id": "plant_A"}),
                    ("release_plant", {"plant_id": "plant_A"}),
                    ("move_to", {"x": 6.0, "y": 18.0}),  # collection_bin
                    ("reserve_station", {"station_name": "collection_bin"}),
                    ("dump_hopper", {}),
                    ("release_station", {"station_name": "collection_bin"}),
                ],
                optional_reads={"sense_pose", "sense_battery", "scan_plant", "list_plants"}
            ),
            
            "rover_2": AgentConstraints(
                agent_id="rover_2",
                required_sequence=[
                    ("unlock_safety_mode", {}),
                    ("move_to", {"x": 14.0, "y": 8.5}),  # plant_C location
                    ("reserve_plant", {"plant_id": "plant_C"}),
                    ("harvest_fruit", {"plant_id": "plant_C"}),
                    ("release_plant", {"plant_id": "plant_C"}),
                    ("move_to", {"x": 6.0, "y": 18.0}),  # collection_bin
                    ("reserve_station", {"station_name": "collection_bin"}),
                    ("dump_hopper", {}),
                    ("release_station", {"station_name": "collection_bin"}),
                ],
                optional_reads={"sense_pose", "sense_battery", "scan_plant", "list_plants"}
            ),
        },
        
        resource_constraints=[
            ResourceConstraint(
                resource_name="plant_A",
                capacity=1,
                mutex_actions=["reserve_plant", "harvest_fruit"]
            ),
            ResourceConstraint(
                resource_name="plant_C",
                capacity=1,
                mutex_actions=["reserve_plant", "harvest_fruit"]
            ),
            ResourceConstraint(
                resource_name="collection_bin",
                capacity=1,
                mutex_actions=["reserve_station", "dump_hopper"]
            ),
        ],
    )
    
    return prompt


# Example execution logs

def get_perfect_execution():
    """Perfect execution: both rovers follow golden paths"""
    return [
        # Rover 1 and Rover 2 unlock in parallel
        ("rover_1", "unlock_safety_mode", {}),
        ("rover_2", "unlock_safety_mode", {}),
        
        # Both move to their plants
        ("rover_1", "move_to", {"x": 2.0, "y": 14.0}),
        ("rover_2", "move_to", {"x": 14.0, "y": 8.5}),
        
        # Both reserve and harvest (independent)
        ("rover_1", "reserve_plant", {"plant_id": "plant_A"}),
        ("rover_2", "reserve_plant", {"plant_id": "plant_C"}),
        ("rover_1", "harvest_fruit", {"plant_id": "plant_A"}),
        ("rover_2", "harvest_fruit", {"plant_id": "plant_C"}),
        ("rover_1", "release_plant", {"plant_id": "plant_A"}),
        ("rover_2", "release_plant", {"plant_id": "plant_C"}),
        
        # Move to collection bin
        ("rover_1", "move_to", {"x": 6.0, "y": 18.0}),
        ("rover_2", "move_to", {"x": 6.0, "y": 18.0}),
        
        # Rover 1 dumps first (mutex)
        ("rover_1", "reserve_station", {"station_name": "collection_bin"}),
        ("rover_1", "dump_hopper", {}),
        ("rover_1", "release_station", {"station_name": "collection_bin"}),
        
        # Rover 2 dumps second
        ("rover_2", "reserve_station", {"station_name": "collection_bin"}),
        ("rover_2", "dump_hopper", {}),
        ("rover_2", "release_station", {"station_name": "collection_bin"}),
    ]


def get_conflicting_execution():
    """Execution with resource conflict"""
    return [
        ("rover_1", "unlock_safety_mode", {}),
        ("rover_2", "unlock_safety_mode", {}),
        
        ("rover_1", "move_to", {"x": 2.0, "y": 14.0}),
        ("rover_2", "move_to", {"x": 14.0, "y": 8.5}),
        
        ("rover_1", "reserve_plant", {"plant_id": "plant_A"}),
        ("rover_2", "reserve_plant", {"plant_id": "plant_C"}),
        ("rover_1", "harvest_fruit", {"plant_id": "plant_A"}),
        ("rover_2", "harvest_fruit", {"plant_id": "plant_C"}),
        ("rover_1", "release_plant", {"plant_id": "plant_A"}),
        ("rover_2", "release_plant", {"plant_id": "plant_C"}),
        
        ("rover_1", "move_to", {"x": 6.0, "y": 18.0}),
        ("rover_2", "move_to", {"x": 6.0, "y": 18.0}),
        
        # BOTH try to reserve collection_bin simultaneously!
        ("rover_1", "reserve_station", {"station_name": "collection_bin"}),
        ("rover_2", "reserve_station", {"station_name": "collection_bin"}),  # ← CONFLICT!
        
        ("rover_1", "dump_hopper", {}),
        ("rover_1", "release_station", {"station_name": "collection_bin"}),
        
        # Rover 2 tries again
        ("rover_2", "reserve_station", {"station_name": "collection_bin"}),
        ("rover_2", "dump_hopper", {}),
        ("rover_2", "release_station", {"station_name": "collection_bin"}),
    ]


def get_unsafe_execution():
    """Execution with safety violation"""
    return [
        # Rover 1 moves WITHOUT unlocking! (harmful)
        ("rover_1", "move_to", {"x": 2.0, "y": 14.0}),  # ← UNSAFE!
        ("rover_1", "unlock_safety_mode", {}),  # Too late
        
        # Rover 2 does it correctly
        ("rover_2", "unlock_safety_mode", {}),
        ("rover_2", "move_to", {"x": 14.0, "y": 8.5}),
        
        # Rest proceeds normally...
        ("rover_1", "reserve_plant", {"plant_id": "plant_A"}),
        ("rover_2", "reserve_plant", {"plant_id": "plant_C"}),
        ("rover_1", "harvest_fruit", {"plant_id": "plant_A"}),
        ("rover_2", "harvest_fruit", {"plant_id": "plant_C"}),
        ("rover_1", "release_plant", {"plant_id": "plant_A"}),
        ("rover_2", "release_plant", {"plant_id": "plant_C"}),
    ]


# Main evaluation function

def evaluate_execution(execution_log, prompt_spec):
    """Evaluate an execution against the Petri Net specification"""
    
    # Build Petri Net from spec
    petri_net = prompt_spec.petri_net
    
    # Replay execution
    replayer = PetriNetReplayer(petri_net)
    replay_result = replayer.replay(execution_log)
    
    # Compute metrics
    metrics = compute_mas_core_metrics(replay_result, prompt_spec)
    
    return replay_result, metrics


# Run examples

if __name__ == "__main__":
    print("=" * 80)
    print("PETRI NET CORE EVALUATION - FARM ROVER MAS")
    print("=" * 80)
    
    # Create prompt specification
    prompt_spec = create_harvest_prompt()
    print(f"\nPrompt: {prompt_spec.text}\n")
    
    # Evaluate perfect execution
    print("\n" + "=" * 80)
    print("1. PERFECT EXECUTION")
    print("=" * 80)
    perfect_log = get_perfect_execution()
    perfect_result, perfect_metrics = evaluate_execution(perfect_log, prompt_spec)
    
    print(f"\nHarmful Events: {len(perfect_result.harmful_events)}")
    print("\nMetrics:")
    for key, value in perfect_metrics.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v:.3f}" if isinstance(v, float) else f"    {k}: {v}")
        else:
            print(f"  {key}: {value:.3f}" if isinstance(value, float) else f"  {key}: {value}")
    
    # Evaluate conflicting execution
    print("\n" + "=" * 80)
    print("2. CONFLICTING EXECUTION (Resource Conflict)")
    print("=" * 80)
    conflict_log = get_conflicting_execution()
    conflict_result, conflict_metrics = evaluate_execution(conflict_log, prompt_spec)
    
    print(f"\nHarmful Events: {len(conflict_result.harmful_events)}")
    for event in conflict_result.harmful_events:
        print(f"  - Step {event.timestep}: {event.agent_id}.{event.function_name} → {event.reason}")
    
    print("\nMetrics:")
    for key, value in conflict_metrics.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v:.3f}" if isinstance(v, float) else f"    {k}: {v}")
        else:
            print(f"  {key}: {value:.3f}" if isinstance(value, float) else f"  {key}: {value}")
    
    # Evaluate unsafe execution
    print("\n" + "=" * 80)
    print("3. UNSAFE EXECUTION (Safety Violation)")
    print("=" * 80)
    unsafe_log = get_unsafe_execution()
    unsafe_result, unsafe_metrics = evaluate_execution(unsafe_log, prompt_spec)
    
    print(f"\nHarmful Events: {len(unsafe_result.harmful_events)}")
    for event in unsafe_result.harmful_events:
        print(f"  - Step {event.timestep}: {event.agent_id}.{event.function_name} → {event.reason}")
    
    print("\nMetrics:")
    for key, value in unsafe_metrics.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v:.3f}" if isinstance(v, float) else f"    {k}: {v}")
        else:
            print(f"  {key}: {value:.3f}" if isinstance(value, float) else f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)