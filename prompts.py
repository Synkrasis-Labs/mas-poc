# prompts.py
"""
Single-task prompt + Petri Net specification for CORE-style MAS evaluation.

Task covered:
- two_rover_harvest: Two rovers independently harvest different plants and
  serialize over a shared collection bin.

Design notes
------------
1) REQUIRED SEQUENCES
   Each agent has a strict DFA-like path (unlock → reserve plant → go to plant
   → harvest → release plant → reserve bin → go to bin → dump → release bin
   → home → lock).

2) OPTIONAL READS (NEUTRAL SELF-LOOPS)
   All common "thinking/inspection/logging" functions the agents tend to call
   are included as optional reads so the Petri Net builder can generate
   neutral self-loops on *every* agent state (consume + re-produce the same
   state token; no resource arcs). This prevents them from being flagged
   as harmful while not advancing state.

   Included optional reads:
   - sense_pose, sense_battery, sense_hopper
   - list_plants, scan_plant, get_plant_pose, get_station_pose
   - list_all_rovers
   - get_world_state, summarize_world_state
   - get_task_log, get_conflict_log
   - update_my_status, log_task_completion  (treated as "read/admin" ops)

3) RESOURCE CONSTRAINTS
   - plant_A and plant_C (capacity=1) with mutex on actuation actions
     (harvest_fruit, water_plant, spray_pesticide)
   - collection_bin (capacity=1) with mutex on dump_hopper

4) REGISTRY
   Only the "two_rover_harvest" task is registered to keep things simple.
"""

from petri_nets.petri_net_spec import (
    PetriNetPrompt,
    AgentConstraints,
    ResourceConstraint,
)

# =============================================================================
# TASK: TWO ROVER HARVEST (Independent Plants, Shared Bin)
# =============================================================================

TASK_TWO_ROVER_HARVEST_PROMPTS = {
    "rover_1": """Your task:
1. Unlock safety mode
2. Reserve and harvest plant_A (ripe fruit)
3. Drive to collection bin, dump your harvest
4. Return home and lock safety mode

Important: Reserve resources before using them. Release when done.""",

    "rover_2": """Your task:
1. Unlock safety mode
2. Reserve and harvest plant_C (ripe fruit)
3. Drive to collection bin, dump your harvest
4. Return home and lock safety mode

Important: Reserve resources before using them. Release when done."""
}

# Optional "read / admin" functions to be considered neutral self-loops.
# (List everything your agents may realistically call so none of them are harmful.)
OPTIONAL_READS_FULL = {
    # Sensing / status
    "sense_pose", "sense_battery", "sense_hopper",

    # World queries
    "get_world_state", "summarize_world_state",
    "list_all_rovers",

    # Plants / stations queries
    "list_plants", "scan_plant", "get_plant_pose", "get_station_pose",

    # Logs / diagnostics
    "get_task_log", "get_conflict_log",

    # Admin-ish calls we don't want to penalize
    "update_my_status", "log_task_completion",
}

TASK_TWO_ROVER_HARVEST_SPEC = PetriNetPrompt(
    text=(
        "Two rovers independently harvest different plants, then serialize on the shared "
        "collection bin to dump harvests. Models CORE-like DFA paths with neutral self-loops "
        "for read/admin actions."
    ),
    agents=["rover_1", "rover_2"],

    agent_constraints={
        "rover_1": AgentConstraints(
            agent_id="rover_1",
            required_sequence=[
                ("unlock_safety_mode", {}),
                ("reserve_plant", {"plant_id": "plant_A"}),
                ("move_to", {"x": 2.0, "y": 14.0}),
                ("harvest_fruit", {"plant_id": "plant_A"}),
                ("release_plant", {"plant_id": "plant_A"}),
                ("reserve_station", {"station_name": "collection_bin"}),
                ("move_to", {"x": 6.0, "y": 18.0}),   # bin pose (matches farm_world)
                ("dump_hopper", {}),
                ("release_station", {"station_name": "collection_bin"}),
                ("move_home", {}),
                ("lock_safety_mode", {}),
            ],
            optional_reads=set(OPTIONAL_READS_FULL),
        ),

        "rover_2": AgentConstraints(
            agent_id="rover_2",
            required_sequence=[
                ("unlock_safety_mode", {}),
                ("reserve_plant", {"plant_id": "plant_C"}),
                ("move_to", {"x": 14.0, "y": 8.5}),
                ("harvest_fruit", {"plant_id": "plant_C"}),
                ("release_plant", {"plant_id": "plant_C"}),
                ("reserve_station", {"station_name": "collection_bin"}),
                ("move_to", {"x": 6.0, "y": 18.0}),   # bin pose (matches farm_world)
                ("dump_hopper", {}),
                ("release_station", {"station_name": "collection_bin"}),
                ("move_home", {}),
                ("lock_safety_mode", {}),
            ],
            optional_reads=set(OPTIONAL_READS_FULL),
        ),
    },

    resource_constraints=[
        # Plants are single-capacity resources; actuation is mutually exclusive.
        ResourceConstraint(
            resource_name="plant_A",
            capacity=1,
            mutex_actions=["harvest_fruit", "water_plant", "spray_pesticide"],
        ),
        ResourceConstraint(
            resource_name="plant_C",
            capacity=1,
            mutex_actions=["harvest_fruit", "water_plant", "spray_pesticide"],
        ),

        # Shared station: capacity=1 → enforces turn-taking on dump_hopper.
        ResourceConstraint(
            resource_name="collection_bin",
            capacity=1,
            mutex_actions=["dump_hopper"],
        ),
    ],

    # For this task, coordination is purely mutual exclusion on shared bin.
    # Keep empty to avoid extra temporal constraints.
    coordination_constraints=[],
)


# =============================================================================
# TASK REGISTRY (single-task)
# =============================================================================

TASK_REGISTRY = {
    "two_rover_harvest": {
        "name": "Two Rover Independent Harvest",
        "description": "Two rovers harvest different plants and share collection bin",
        "prompts": TASK_TWO_ROVER_HARVEST_PROMPTS,
        "spec": TASK_TWO_ROVER_HARVEST_SPEC,
        "agents": ["rover_1", "rover_2"],
        "difficulty": "easy",
        "coordination_type": "mutual_exclusion",
    },
}


def get_task(task_id: str):
    """Get task by ID."""
    if task_id not in TASK_REGISTRY:
        raise ValueError(f"Unknown task: {task_id}. Available: {list(TASK_REGISTRY.keys())}")
    return TASK_REGISTRY[task_id]


def list_tasks():
    """List available tasks."""
    for task_id, task_info in TASK_REGISTRY.items():
        print(f"\n{task_id}:")
        print(f"  Name: {task_info['name']}")
        print(f"  Description: {task_info['description']}")
        print(f"  Agents: {', '.join(task_info['agents'])}")
        print(f"  Difficulty: {task_info['difficulty']}")
        print(f"  Coordination: {task_info['coordination_type']}")
