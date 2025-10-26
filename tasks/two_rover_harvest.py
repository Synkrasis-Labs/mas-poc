# tasks/two_rover_harvest.py
"""
Task: Two Rover Independent Harvest
Checks: Per-agent DFA correctness + shared-station mutual exclusion (collection_bin)
"""

from petri_nets.petri_net_spec import (
    PetriNetPrompt,
    AgentConstraints,
    ResourceConstraint,
)

TASK_ID = "two_rover_harvest"

PROMPTS = {
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

# Neutral reads/admin ops allowed at any DFA state (self-loops)
OPTIONAL_READS = {
    "sense_pose", "sense_battery", "sense_hopper",
    "get_world_state", "summarize_world_state",
    "list_all_rovers",
    "list_plants", "scan_plant", "get_plant_pose", "get_station_pose",
    "get_task_log", "get_conflict_log",
    "update_my_status", "log_task_completion",
    "get_my_rover_id",
}

SPEC = PetriNetPrompt(
    text=(
        "Two rovers independently harvest different plants, then serialize on the shared "
        "collection bin to dump harvests."
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
                ("move_to", {"x": 6.0, "y": 18.0}),
                ("dump_hopper", {}),
                ("release_station", {"station_name": "collection_bin"}),
                ("move_home", {}),
                ("lock_safety_mode", {}),
            ],
            optional_reads=set(OPTIONAL_READS),
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
                ("move_to", {"x": 6.0, "y": 18.0}),
                ("dump_hopper", {}),
                ("release_station", {"station_name": "collection_bin"}),
                ("move_home", {}),
                ("lock_safety_mode", {}),
            ],
            optional_reads=set(OPTIONAL_READS),
        ),
    },

    resource_constraints=[
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
        ResourceConstraint(
            resource_name="collection_bin",
            capacity=1,
            mutex_actions=["dump_hopper"],
        ),
    ],

    coordination_constraints=[],
)

TASK_INFO = {
    "name": "Two Rover Independent Harvest",
    "description": "Two rovers harvest different plants and share collection bin",
    "prompts": PROMPTS,
    "spec": SPEC,
    "agents": ["rover_1", "rover_2"],
    "difficulty": "easy",
    "coordination_type": "mutual_exclusion",
}
