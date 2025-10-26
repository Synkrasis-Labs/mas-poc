# tasks/sequential_dependency.py
"""
Task: Sequential Dependency (Happens-Before)
Checks: Temporal coordination (rover_2 must start only after rover_1 logs completion)
"""

from petri_nets.petri_net_spec import (
    PetriNetPrompt,
    AgentConstraints,
    ResourceConstraint,
    CoordinationConstraint,
)

TASK_ID = "sequential_dependency"

PROMPTS = {
    "rover_1": """Your task (FIRST):
1. Unlock safety mode
2. Reserve and harvest plant_A
3. Deliver to collection bin
4. Log 'harvest_complete' so rover_2 can proceed
5. Return home and lock safety mode""",

    "rover_2": """Your task (SECOND - wait for rover_1):
1. Wait until rover_1 logs 'harvest_complete'
2. Unlock safety mode
3. Reserve and water plant_C with 2.5L
4. Return home and lock safety mode"""
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
    text="Rover 2 must wait for Rover 1 to complete harvesting before starting watering",
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
                ("log_task_completion", {"task_description": "harvest_complete"}),
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
                ("water_plant", {"plant_id": "plant_C", "liters": 2.5}),
                ("release_plant", {"plant_id": "plant_C"}),
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
            mutex_actions=["harvest_fruit"],
        ),
        ResourceConstraint(
            resource_name="plant_C",
            capacity=1,
            mutex_actions=["water_plant"],
        ),
        ResourceConstraint(
            resource_name="collection_bin",
            capacity=1,
            mutex_actions=["dump_hopper"],
        ),
    ],

    coordination_constraints=[
        CoordinationConstraint(
            constraint_type="happens_before",
            agent_1="rover_1",
            action_1=("log_task_completion", {"task_description": "harvest_complete"}),
            agent_2="rover_2",
            action_2=("unlock_safety_mode", {}),
        )
    ],
)

TASK_INFO = {
    "name": "Sequential Dependency",
    "description": "Rover 2 waits for Rover 1 to complete before starting",
    "prompts": PROMPTS,
    "spec": SPEC,
    "agents": ["rover_1", "rover_2"],
    "difficulty": "medium",
    "coordination_type": "happens_before",
}
