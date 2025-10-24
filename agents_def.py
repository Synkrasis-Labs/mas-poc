from agents import Agent
from farm_context import FarmContext
from farm_world import (
    get_world_state, summarize_world_state,
    unlock_safety_mode, lock_safety_mode,
    move_to, move_home,
    harvest_fruit, dump_hopper,
    water_plant, spray_pesticide,
    refill_water_tank, refill_pesticide, recharge,
    sense_pose, sense_battery, sense_hopper,
    list_plants, scan_plant, get_plant_pose, get_station_pose,
)



farm_tools = [
    get_world_state, summarize_world_state,
    unlock_safety_mode, lock_safety_mode,
    move_to, move_home,
    harvest_fruit, dump_hopper,
    water_plant, spray_pesticide,
    refill_water_tank, refill_pesticide, recharge,
    sense_pose, sense_battery, sense_hopper,
    list_plants, scan_plant, get_plant_pose, get_station_pose,
]

INSTRUCTIONS = (
    "You are an agent operating a rover in a farm. "
    "Use only the provided tools. "
    "Call get_world_state() if you need the latest snapshot."
)

Rover = Agent[FarmContext](
    name="PlannerAgent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    tools=farm_tools
)



