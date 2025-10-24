# agents_def.py
from agents import Agent
from farm_context import FarmContext
from farm_world import (
    # Coordination functions
    get_my_rover_id, list_all_rovers, get_rover_status,
    reserve_plant, release_plant,
    reserve_station, release_station,
    update_my_status, log_task_completion,
    
    # World state queries
    get_world_state, summarize_world_state,
    
    # Safety & control
    unlock_safety_mode, lock_safety_mode,
    
    # Motion
    move_to, move_home,
    
    # Plant operations
    harvest_fruit, water_plant, spray_pesticide,
    
    # Station operations
    dump_hopper, refill_water_tank, refill_pesticide, recharge,
    
    # Sensors
    sense_pose, sense_battery, sense_hopper,
    list_plants, scan_plant, get_plant_pose, get_station_pose,
    get_task_log, get_conflict_log,
)

# All available tools for rover agents
farm_tools = [
    # Coordination
    get_my_rover_id, list_all_rovers, get_rover_status,
    reserve_plant, release_plant,
    reserve_station, release_station,
    update_my_status, log_task_completion,
    
    # World state
    get_world_state, summarize_world_state,
    
    # Safety
    unlock_safety_mode, lock_safety_mode,
    
    # Motion
    move_to, move_home,
    
    # Plant operations
    harvest_fruit, water_plant, spray_pesticide,
    
    # Station operations
    dump_hopper, refill_water_tank, refill_pesticide, recharge,
    
    # Sensors
    sense_pose, sense_battery, sense_hopper,
    list_plants, scan_plant, get_plant_pose, get_station_pose,
    get_task_log, get_conflict_log,
]

ROVER_INSTRUCTIONS = """
You are an autonomous farming rover agent operating in a MULTI-AGENT system.

CRITICAL MULTI-AGENT RULES:
1. You are ONE of MULTIPLE rovers operating simultaneously in the same field
2. ALWAYS check what other rovers are doing before taking actions
3. ALWAYS reserve resources (plants/stations) before using them
4. ALWAYS release resources after you're done
5. AVOID collisions - if a move fails due to another rover, wait or find alternative
6. Update your status so other rovers know what you're doing
7. Check if plants/stations are already reserved before attempting to reserve them

COORDINATION WORKFLOW:
1. Check other rovers' positions and statuses (list_all_rovers)
2. Identify available plants/stations (list_plants, check reserved_by field)
3. Reserve the resource BEFORE moving to it (reserve_plant/reserve_station)
4. Update your status (update_my_status) to inform others
5. Perform the task
6. Release the resource (release_plant/release_station)
7. Log task completion (log_task_completion)

SAFETY WORKFLOW:
- ALWAYS unlock safety mode before any motion or actuation
- Lock safety mode when idle or task complete
- If collision detected, wait and retry or choose different target

RESOURCE MANAGEMENT:
- Monitor your battery, hopper, water, and pesticide levels
- Plan refill trips when resources are low
- Don't attempt tasks you don't have resources for

Be efficient, cooperative, and avoid conflicts with other rovers.
"""


def create_rover_agent(rover_id: str, model: str = "gpt-4o-mini") -> Agent[FarmContext]:
    """
    Create a rover agent for the multi-agent system.
    
    Args:
        rover_id: Unique identifier for this rover (e.g., "rover_1")
        model: The OpenAI model to use
    
    Returns:
        An Agent configured for this specific rover
    """
    return Agent[FarmContext](
        name=f"RoverAgent_{rover_id}",
        instructions=ROVER_INSTRUCTIONS,
        model=model,
        tools=farm_tools
    )


# Pre-configured agents for the three default rovers
Rover1 = create_rover_agent("rover_1", model="gpt-4o-mini")
Rover2 = create_rover_agent("rover_2", model="gpt-4o-mini")
Rover3 = create_rover_agent("rover_3", model="gpt-4o-mini")