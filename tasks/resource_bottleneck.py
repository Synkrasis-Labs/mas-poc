# tasks/resource_bottleneck.py
"""
Task: Resource Bottleneck (Single Charging Pad)
Checks: Mutual exclusion & queueing behavior on a scarce station
"""

from petri_nets.petri_net_spec import (
    PetriNetPrompt,
    AgentConstraints,
    ResourceConstraint,
)

TASK_ID = "resource_bottleneck"

PROMPTS = {
    "rover_1": """Your task:
1. Unlock safety mode
2. Harvest plant_E
3. Recharge battery at charging pad (single shared pad)
4. Return home and lock safety mode""",

    "rover_2": """Your task:
1. Unlock safety mode
2. Water plant_F (2.0L)
3. Recharge battery at charging pad (single shared pad)
4. Return home and lock safety mode""",
}

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
    text="Two rovers with low battery must share single charging pad",
    agents=["rover_1", "rover_2"],

    agent_constraints={
        "rover_1": AgentConstraints(
            agent_id="rover_1",
            required_sequence=[
                ("unlock_safety_mode", {}),
                ("reserve_plant", {"plant_id": "plant_E"}),
                ("move_to", {"x": 7.0, "y": 6.0}),
                ("harvest_fruit", {"plant_id": "plant_E"}),
                ("release_plant", {"plant_id": "plant_E"}),
                ("reserve_station", {"station_name": "charging_pad"}),
                ("move_to", {"x": 1.0, "y": 1.0}),
                ("recharge", {}),
                ("release_station", {"station_name": "charging_pad"}),
                ("move_home", {}),
                ("lock_safety_mode", {}),
            ],
            optional_reads=set(OPTIONAL_READS),
        ),
        "rover_2": AgentConstraints(
            agent_id="rover_2",
            required_sequence=[
                ("unlock_safety_mode", {}),
                ("reserve_plant", {"plant_id": "plant_F"}),
                ("move_to", {"x": 12.5, "y": 3.0}),
                ("water_plant", {"plant_id": "plant_F", "liters": 2.0}),
                ("release_plant", {"plant_id": "plant_F"}),
                ("reserve_station", {"station_name": "charging_pad"}),
                ("move_to", {"x": 1.0, "y": 1.0}),
                ("recharge", {}),
                ("release_station", {"station_name": "charging_pad"}),
                ("move_home", {}),
                ("lock_safety_mode", {}),
            ],
            optional_reads=set(OPTIONAL_READS),
        ),
    },

    resource_constraints=[
        ResourceConstraint(
            resource_name="plant_E",
            capacity=1,
            mutex_actions=["harvest_fruit"],
        ),
        ResourceConstraint(
            resource_name="plant_F",
            capacity=1,
            mutex_actions=["water_plant"],
        ),
        ResourceConstraint(
            resource_name="charging_pad",
            capacity=1,
            mutex_actions=["recharge"],
        ),
    ],

    coordination_constraints=[],
)

TASK_INFO = {
    "name": "Resource Bottleneck",
    "description": "Two rovers compete for single charging pad",
    "prompts": PROMPTS,
    "spec": SPEC,
    "agents": ["rover_1", "rover_2"],
    "difficulty": "hard",
    "coordination_type": "queue_management",
}
