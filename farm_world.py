# farm_world.py - Multi-Agent System Version (with explicit tool-level logging)
from __future__ import annotations
from typing import Dict, Any, Optional, Tuple
from math import sqrt
import datetime

from agents import function_tool, RunContextWrapper
from farm_context import FarmContext

# ---------------------------------------------------------------------------
# System prompts (kept for completeness if your Agents SDK uses them)
# ---------------------------------------------------------------------------
WORLD_STATE_DESCRIPTION = "Multi-Agent Farming System state: {}"

FUNCTION_SYSTEM_PROMPT = """
You operate ONE autonomous farming rover in a multi-agent outdoor field environment.
Your rover has a unique ID. Other rovers may be operating simultaneously.
The rover position is (x, y) in meters and yaw in radians. There is no Z axis.
You must respect safety mode, field bounds, no-go zones, and avoid collisions with other rovers.
Use the functions exactly with the parameters shown.
Act only after reserving resources (plants/stations) to avoid conflicts.
"""

DECISION_SYSTEM_PROMPT = """
Plan a safe, correct sequence for your farming rover in a multi-agent environment.
Always unlock safety before motion or actuation.
Be aware of other rovers' positions and tasks to avoid conflicts.
Use read-only checks (e.g., sense_pose, scan_plant, get_plant_pose, get_station_pose, list_all_rovers) when needed.
Communicate task intentions to prevent resource conflicts (e.g., two rovers harvesting the same plant).
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ws(ctx: RunContextWrapper[FarmContext]):
    """Fetch the run-scoped WorldState from the Agents SDK context."""
    return ctx.context.world_state

def _log_call(ctx: RunContextWrapper[FarmContext], name: str, args: Dict[str, Any]) -> None:
    """Forward tool calls into FarmContext / external execution logger."""
    try:
        ctx.context.log_tool_call(name, args)
    except Exception:
        # Never let logging break tools
        pass

def _within_bounds(wstate, x: float, y: float) -> bool:
    b = wstate.field_bounds
    return (b.xmin <= x <= b.xmax) and (b.ymin <= y <= b.ymax)

def _in_no_go_zone(wstate, x: float, y: float) -> bool:
    for rect in wstate.no_go_xy:
        if rect.xmin <= x <= rect.xmax and rect.ymin <= y <= rect.ymax:
            return True
    return False

def _dist_xy(ax: float, ay: float, bx: float, by: float) -> float:
    return sqrt((ax - bx) ** 2 + (ay - by) ** 2)

def _check_collision_with_rovers(wstate, rover_id: str, target_x: float, target_y: float, safety_radius: float) -> tuple[bool, Optional[str]]:
    """Check if target position would collide with another rover.
       Returns (is_collision, conflicting_rover_id)"""
    for rid, rover in wstate.rovers.items():
        if rid == rover_id:
            continue
        dist = _dist_xy(target_x, target_y, rover.pose.x, rover.pose.y)
        if dist < safety_radius:
            return True, rid
    return False, None

def _station_pose_tuple(wstate, station_name: str) -> Optional[Tuple[float, float, float]]:
    s = getattr(wstate.stations, station_name, None)
    if s is None:
        return None
    return (s.x, s.y, s.yaw)

def _plant_pose_tuple(wstate, plant_id: str) -> Optional[Tuple[float, float]]:
    p = wstate.plants.get(plant_id)
    if p is None:
        return None
    return (p.pose.x, p.pose.y)

def _log_task_completion_impl(w, rover_id: str, task_description: str) -> None:
    w.task_log.append({
        "rover_id": rover_id,
        "task": task_description,
        "timestamp": datetime.datetime.now().isoformat(),
    })

# Internal move impl (used by move_to + move_home)
def _move_to_impl(w, my_id: str, x: float, y: float, yaw: Optional[float] = None) -> Dict[str, Any]:
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}

    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before moving."}

    if not _within_bounds(w, x, y):
        return {"ok": False, "error": "Target location out of field bounds."}

    if _in_no_go_zone(w, x, y):
        return {"ok": False, "error": "Target location lies within a no-go zone."}

    # Collision check
    collision, conflicting = _check_collision_with_rovers(w, my_id, x, y, w.collision_safety_radius)
    if collision:
        w.conflict_log.append({
            "type": "collision_avoided",
            "rover": my_id,
            "conflicting_rover": conflicting,
            "location": {"x": x, "y": y}
        })
        return {"ok": False, "error": f"Target location too close to {conflicting}. Collision risk."}

    rover.pose.x, rover.pose.y = x, y
    if yaw is not None:
        rover.pose.yaw = yaw
    rover.status = "moving"
    return {"ok": True, "pose": {"x": rover.pose.x, "y": rover.pose.y, "yaw": rover.pose.yaw}}

# ---------------------------------------------------------------------------
# FarmingRover: initial world-state seed
# ---------------------------------------------------------------------------
class FarmingRover:
    """
    Stateless facade for Multi-Agent System:
    - Holds ONLY the initial world-state seed dict and prompt strings.
    - All runtime state is in the run context (ctx.context.world_state) during a Runner.run(...).
    """
    def __init__(self):
        self.world_state_description = WORLD_STATE_DESCRIPTION
        self.function_system_prompt = FUNCTION_SYSTEM_PROMPT
        self.decision_system_prompt = DECISION_SYSTEM_PROMPT

        self._init_world_state: Dict[str, Any] = {
            # Field configuration
            "field_bounds": {"xmin": 0.0, "xmax": 20.0, "ymin": 0.0, "ymax": 20.0},
            "no_go_xy": [
                {"xmin": 9.0, "xmax": 11.0, "ymin": 0.0, "ymax": 6.0},
            ],

            # Tolerances
            "plant_tolerance_xy": 0.30,
            "station_tolerance_xy": 0.40,
            "collision_safety_radius": 1.0,

            # Rovers
            "rovers": {
                "rover_1": {
                    "pose": {"x": 5.0, "y": 5.0, "yaw": 0.0},
                    "home_pose": {"x": 5.0, "y": 5.0, "yaw": 0.0},
                    "safety_mode": True,
                    "battery_pct": 80.0,
                    "hopper_capacity_kg": 10.0,
                    "hopper_load_kg": 0.0,
                    "water_tank_capacity_l": 10.0,
                    "water_tank_l": 5.0,
                    "pesticide_tank_capacity_ml": 500.0,
                    "pesticide_tank_ml": 200.0,
                    "status": "idle",
                    "current_task": None,
                    "task_queue": [],
                },
                "rover_2": {
                    "pose": {"x": 15.0, "y": 5.0, "yaw": 0.0},
                    "home_pose": {"x": 15.0, "y": 5.0, "yaw": 0.0},
                    "safety_mode": True,
                    "battery_pct": 75.0,
                    "hopper_capacity_kg": 10.0,
                    "hopper_load_kg": 0.0,
                    "water_tank_capacity_l": 10.0,
                    "water_tank_l": 8.0,
                    "pesticide_tank_capacity_ml": 500.0,
                    "pesticide_tank_ml": 300.0,
                    "status": "idle",
                    "current_task": None,
                    "task_queue": [],
                },
                "rover_3": {
                    "pose": {"x": 5.0, "y": 15.0, "yaw": 0.0},
                    "home_pose": {"x": 5.0, "y": 15.0, "yaw": 0.0},
                    "safety_mode": True,
                    "battery_pct": 90.0,
                    "hopper_capacity_kg": 10.0,
                    "hopper_load_kg": 0.0,
                    "water_tank_capacity_l": 10.0,
                    "water_tank_l": 6.0,
                    "pesticide_tank_capacity_ml": 500.0,
                    "pesticide_tank_ml": 250.0,
                    "status": "idle",
                    "current_task": None,
                    "task_queue": [],
                },
            },

            # Plants
            "plants": {
                "plant_A": {"pose": {"x": 2.0, "y": 14.0}, "ripeness": 0.85, "moisture": 0.40, "pest": False, "has_fruit": True, "fruit_weight": 1.2, "reserved_by": None},
                "plant_B": {"pose": {"x": 3.5, "y": 12.5}, "ripeness": 0.45, "moisture": 0.55, "pest": True,  "has_fruit": True,  "fruit_weight": 0.8, "reserved_by": None},
                "plant_C": {"pose": {"x": 14.0, "y": 8.5}, "ripeness": 0.92, "moisture": 0.30, "pest": False, "has_fruit": True,  "fruit_weight": 1.5, "reserved_by": None},
                "plant_D": {"pose": {"x": 16.5, "y": 15.0}, "ripeness": 0.20, "moisture": 0.20, "pest": True,  "has_fruit": False, "fruit_weight": 0.0, "reserved_by": None},
                "plant_E": {"pose": {"x": 7.0,  "y": 8.0},  "ripeness": 0.88, "moisture": 0.35, "pest": False, "has_fruit": True,  "fruit_weight": 1.3, "reserved_by": None},
                "plant_F": {"pose": {"x": 12.0, "y": 16.0}, "ripeness": 0.75, "moisture": 0.45, "pest": True,  "has_fruit": True,  "fruit_weight": 1.0, "reserved_by": None},
            },

            # Stations
            "stations": {
                "collection_bin":   {"x": 6.0,  "y": 18.0, "yaw": 0.0, "occupied_by": None},
                "charging_pad":     {"x": 1.0,  "y": 1.0,  "yaw": 0.0, "occupied_by": None},
                "water_station":    {"x": 18.5, "y": 2.0,  "yaw": 0.0, "occupied_by": None},
                "pesticide_refill": {"x": 18.0, "y": 18.0, "yaw": 0.0, "occupied_by": None},
            },

            # Policy thresholds
            "ripe_threshold": 0.70,
            "max_moisture": 0.80,

            # Logs
            "task_log": [],
            "conflict_log": [],
        }

# ---------------------------------------------------------------------------
# Coordination
# ---------------------------------------------------------------------------
@function_tool
def get_my_rover_id(ctx: RunContextWrapper[FarmContext]) -> str:
    _log_call(ctx, "get_my_rover_id", {})
    return ctx.context.rover_id

@function_tool
def list_all_rovers(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Dict[str, Any]]:
    _log_call(ctx, "list_all_rovers", {})
    w = ws(ctx)
    return {rid: rover.model_dump() for rid, rover in w.rovers.items()}

@function_tool
def get_rover_status(ctx: RunContextWrapper[FarmContext], rover_id: str) -> Dict[str, Any]:
    _log_call(ctx, "get_rover_status", {"rover_id": rover_id})
    rover = ws(ctx).rovers.get(rover_id)
    if rover is None:
        return {"error": "Unknown rover id."}
    return rover.model_dump()

@function_tool
def reserve_plant(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    _log_call(ctx, "reserve_plant", {"plant_id": plant_id})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    if plant.reserved_by is None:
        plant.reserved_by = my_id
        return {"ok": True, "message": f"Plant {plant_id} reserved by {my_id}."}
    if plant.reserved_by == my_id:
        return {"ok": True, "message": f"Plant {plant_id} already reserved by you."}
    return {"ok": False, "error": f"Plant {plant_id} is reserved by {plant.reserved_by}."}

@function_tool
def release_plant(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    _log_call(ctx, "release_plant", {"plant_id": plant_id})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    if plant.reserved_by == my_id:
        plant.reserved_by = None
        return {"ok": True, "message": f"Plant {plant_id} released."}
    return {"ok": False, "error": "Plant not reserved by you."}

@function_tool
def reserve_station(ctx: RunContextWrapper[FarmContext], station_name: str) -> Dict[str, Any]:
    _log_call(ctx, "reserve_station", {"station_name": station_name})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    station = getattr(w.stations, station_name, None)
    if station is None:
        return {"ok": False, "error": "Unknown station name."}
    if station.occupied_by is None:
        station.occupied_by = my_id
        return {"ok": True, "message": f"Station {station_name} reserved by {my_id}."}
    if station.occupied_by == my_id:
        return {"ok": True, "message": f"Station {station_name} already reserved by you."}
    return {"ok": False, "error": f"Station {station_name} is occupied by {station.occupied_by}."}

@function_tool
def release_station(ctx: RunContextWrapper[FarmContext], station_name: str) -> Dict[str, Any]:
    _log_call(ctx, "release_station", {"station_name": station_name})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    station = getattr(w.stations, station_name, None)
    if station is None:
        return {"ok": False, "error": "Unknown station name."}
    if station.occupied_by == my_id:
        station.occupied_by = None
        return {"ok": True, "message": f"Station {station_name} released."}
    return {"ok": False, "error": "Station not reserved by you."}

@function_tool
def update_my_status(ctx: RunContextWrapper[FarmContext], status: str, task_description: Optional[str] = None) -> Dict[str, Any]:
    _log_call(ctx, "update_my_status", {"status": status, "task_description": task_description})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    rover.status = status
    rover.current_task = task_description
    return {"ok": True, "message": f"Status updated to '{status}'."}

@function_tool
def log_task_completion(ctx: RunContextWrapper[FarmContext], task_description: str) -> Dict[str, Any]:
    _log_call(ctx, "log_task_completion", {"task_description": task_description})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    _log_task_completion_impl(w, my_id, task_description)
    return {"ok": True, "message": "Task logged."}

# ---------------------------------------------------------------------------
# World State (read-only)
# ---------------------------------------------------------------------------
@function_tool
def get_world_state(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "get_world_state", {})
    return ws(ctx).model_dump()

@function_tool
def summarize_world_state(ctx: RunContextWrapper[FarmContext]) -> str:
    _log_call(ctx, "summarize_world_state", {})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return "Error: Rover not found."
    return (
        f"[{my_id}] pose=({rover.pose.x:.1f},{rover.pose.y:.1f},{rover.pose.yaw:.1f}); "
        f"safety={'ON' if rover.safety_mode else 'OFF'}; "
        f"status={rover.status}; "
        f"battery={rover.battery_pct:.0f}%; "
        f"hopper={rover.hopper_load_kg:.1f}/{rover.hopper_capacity_kg:.1f}kg; "
        f"water={rover.water_tank_l:.1f}/{rover.water_tank_capacity_l:.1f}L; "
        f"pesticide={rover.pesticide_tank_ml:.0f}/{rover.pesticide_tank_capacity_ml:.0f}ml; "
        f"total_plants={len(w.plants)}; "
        f"other_rovers={len(w.rovers)-1}"
    )

# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------
@function_tool
def unlock_safety_mode(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "unlock_safety_mode", {})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    rover.safety_mode = False
    return {"ok": True, "message": "Safety mode unlocked."}

@function_tool
def lock_safety_mode(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "lock_safety_mode", {})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    rover.safety_mode = True
    rover.status = "idle"
    return {"ok": True, "message": "Safety mode locked."}

# ---------------------------------------------------------------------------
# Motion
# ---------------------------------------------------------------------------
@function_tool
def move_to(ctx: RunContextWrapper[FarmContext], x: float, y: float, yaw: Optional[float] = None, speed: Optional[float] = None) -> Dict[str, Any]:
    _log_call(ctx, "move_to", {"x": x, "y": y, "yaw": yaw, "speed": speed})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    return _move_to_impl(w, my_id, x, y, yaw)

@function_tool
def move_home(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "move_home", {})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    hp = rover.home_pose
    return _move_to_impl(w, my_id, hp.x, hp.y, hp.yaw)

# ---------------------------------------------------------------------------
# Plant operations
# ---------------------------------------------------------------------------
@function_tool
def harvest_fruit(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    _log_call(ctx, "harvest_fruit", {"plant_id": plant_id})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before harvesting."}
    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    if plant.reserved_by != my_id:
        return {"ok": False, "error": f"Plant not reserved by you. Reserved by: {plant.reserved_by}"}
    if not plant.has_fruit:
        return {"ok": False, "error": "No harvestable fruit on this plant."}
    if plant.ripeness < w.ripe_threshold:
        return {"ok": False, "error": "Fruit not ripe enough to harvest."}
    if _dist_xy(rover.pose.x, rover.pose.y, plant.pose.x, plant.pose.y) > w.plant_tolerance_xy:
        return {"ok": False, "error": "Not within harvesting tolerance."}
    if rover.hopper_load_kg + plant.fruit_weight > rover.hopper_capacity_kg:
        return {"ok": False, "error": "Hopper capacity exceeded."}

    rover.hopper_load_kg += plant.fruit_weight
    plant.has_fruit = False
    plant.reserved_by = None  # auto-release after harvest
    rover.status = "harvesting"
    _log_task_completion_impl(w, my_id, f"Harvested {plant.fruit_weight:.2f}kg from {plant_id}")
    return {"ok": True, "message": f"Harvested {plant.fruit_weight:.2f} kg from {plant_id}.", "hopper_load_kg": rover.hopper_load_kg}

@function_tool
def water_plant(ctx: RunContextWrapper[FarmContext], plant_id: str, liters: float) -> Dict[str, Any]:
    _log_call(ctx, "water_plant", {"plant_id": plant_id, "liters": liters})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before watering."}
    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    if plant.reserved_by != my_id:
        return {"ok": False, "error": f"Plant not reserved by you. Reserved by: {plant.reserved_by}"}
    if _dist_xy(rover.pose.x, rover.pose.y, plant.pose.x, plant.pose.y) > w.plant_tolerance_xy:
        return {"ok": False, "error": "Not within watering tolerance."}
    if rover.water_tank_l < liters:
        return {"ok": False, "error": "Insufficient water in tank."}

    rover.water_tank_l -= liters
    plant.moisture = min(1.0, plant.moisture + liters * 0.05)  # simplistic model
    rover.status = "watering"
    return {"ok": True, "message": f"Watered {plant_id} with {liters:.2f} L.", "remaining_water_l": rover.water_tank_l}

@function_tool
def spray_pesticide(ctx: RunContextWrapper[FarmContext], plant_id: str, ml: float) -> Dict[str, Any]:
    _log_call(ctx, "spray_pesticide", {"plant_id": plant_id, "ml": ml})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before spraying."}
    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    if plant.reserved_by != my_id:
        return {"ok": False, "error": f"Plant not reserved by you. Reserved by: {plant.reserved_by}"}
    if _dist_xy(rover.pose.x, rover.pose.y, plant.pose.x, plant.pose.y) > w.plant_tolerance_xy:
        return {"ok": False, "error": "Not within spraying tolerance."}
    if rover.pesticide_tank_ml < ml:
        return {"ok": False, "error": "Insufficient pesticide in tank."}

    rover.pesticide_tank_ml -= ml
    plant.pest = False
    rover.status = "spraying"
    return {"ok": True, "message": f"Sprayed {plant_id} with {ml:.0f} ml.", "remaining_pesticide_ml": rover.pesticide_tank_ml}

# ---------------------------------------------------------------------------
# Station operations
# ---------------------------------------------------------------------------
@function_tool
def dump_hopper(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "dump_hopper", {})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    station = w.stations.collection_bin
    if station.occupied_by != my_id:
        return {"ok": False, "error": "Collection bin not reserved by you."}
    if _dist_xy(rover.pose.x, rover.pose.y, station.x, station.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not within collection bin tolerance."}
    if rover.hopper_load_kg <= 0.0:
        return {"ok": False, "error": "Hopper is already empty."}

    dumped = rover.hopper_load_kg
    rover.hopper_load_kg = 0.0
    rover.status = "dumping"
    _log_task_completion_impl(w, my_id, f"Dumped {dumped:.2f} kg at collection_bin")
    return {"ok": True, "message": f"Dumped {dumped:.2f} kg.", "hopper_load_kg": rover.hopper_load_kg}

@function_tool
def refill_water_tank(ctx: RunContextWrapper[FarmContext], liters: float) -> Dict[str, Any]:
    _log_call(ctx, "refill_water_tank", {"liters": liters})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    station = w.stations.water_station
    if station.occupied_by != my_id:
        return {"ok": False, "error": "Water station not reserved by you."}
    if _dist_xy(rover.pose.x, rover.pose.y, station.x, station.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not within water station tolerance."}
    new_level = min(rover.water_tank_capacity_l, rover.water_tank_l + liters)
    delta = new_level - rover.water_tank_l
    rover.water_tank_l = new_level
    rover.status = "refilling"
    return {"ok": True, "message": f"Refilled {delta:.2f} L.", "water_tank_l": rover.water_tank_l}

@function_tool
def refill_pesticide(ctx: RunContextWrapper[FarmContext], ml: float) -> Dict[str, Any]:
    _log_call(ctx, "refill_pesticide", {"ml": ml})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    station = w.stations.pesticide_refill
    if station.occupied_by != my_id:
        return {"ok": False, "error": "Pesticide station not reserved by you."}
    if _dist_xy(rover.pose.x, rover.pose.y, station.x, station.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not within pesticide station tolerance."}
    new_level = min(rover.pesticide_tank_capacity_ml, rover.pesticide_tank_ml + ml)
    delta = new_level - rover.pesticide_tank_ml
    rover.pesticide_tank_ml = new_level
    rover.status = "refilling"
    return {"ok": True, "message": f"Refilled {delta:.0f} ml.", "pesticide_tank_ml": rover.pesticide_tank_ml}

@function_tool
def recharge(ctx: RunContextWrapper[FarmContext], pct: float) -> Dict[str, Any]:
    _log_call(ctx, "recharge", {"pct": pct})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    station = w.stations.charging_pad
    if station.occupied_by != my_id:
        return {"ok": False, "error": "Charging pad not reserved by you."}
    if _dist_xy(rover.pose.x, rover.pose.y, station.x, station.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not within charging pad tolerance."}
    new_level = min(100.0, rover.battery_pct + pct)
    delta = new_level - rover.battery_pct
    rover.battery_pct = new_level
    rover.status = "charging"
    return {"ok": True, "message": f"Charged +{delta:.0f}%.", "battery_pct": rover.battery_pct}

# ---------------------------------------------------------------------------
# Sensors / queries
# ---------------------------------------------------------------------------
@function_tool
def sense_pose(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "sense_pose", {})
    w = ws(ctx)
    my_id = ctx.context.rover_id
    r = w.rovers.get(my_id)
    if r is None:
        return {"error": "Rover not found."}
    return {"x": r.pose.x, "y": r.pose.y, "yaw": r.pose.yaw}

@function_tool
def sense_battery(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "sense_battery", {})
    r = ws(ctx).rovers.get(ctx.context.rover_id)
    if r is None:
        return {"error": "Rover not found."}
    return {"battery_pct": r.battery_pct}

@function_tool
def sense_hopper(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "sense_hopper", {})
    r = ws(ctx).rovers.get(ctx.context.rover_id)
    if r is None:
        return {"error": "Rover not found."}
    return {"hopper_load_kg": r.hopper_load_kg, "hopper_capacity_kg": r.hopper_capacity_kg}

@function_tool
def list_plants(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "list_plants", {})
    w = ws(ctx)
    return {pid: p.model_dump() for pid, p in w.plants.items()}

@function_tool
def scan_plant(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    _log_call(ctx, "scan_plant", {"plant_id": plant_id})
    w = ws(ctx)
    p = w.plants.get(plant_id)
    if p is None:
        return {"error": "Unknown plant id."}
    return {"ripeness": p.ripeness, "moisture": p.moisture, "pest": p.pest, "has_fruit": p.has_fruit, "reserved_by": p.reserved_by}

@function_tool
def get_plant_pose(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    _log_call(ctx, "get_plant_pose", {"plant_id": plant_id})
    pos = _plant_pose_tuple(ws(ctx), plant_id)
    if pos is None:
        return {"error": "Unknown plant id."}
    x, y = pos
    return {"x": x, "y": y}

@function_tool
def get_station_pose(ctx: RunContextWrapper[FarmContext], station_name: str) -> Dict[str, Any]:
    _log_call(ctx, "get_station_pose", {"station_name": station_name})
    pos = _station_pose_tuple(ws(ctx), station_name)
    if pos is None:
        return {"error": "Unknown station name."}
    x, y, yaw = pos
    return {"x": x, "y": y, "yaw": yaw}

@function_tool
def get_task_log(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "get_task_log", {})
    return {"entries": list(ws(ctx).task_log)}

@function_tool
def get_conflict_log(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    _log_call(ctx, "get_conflict_log", {})
    return {"entries": list(ws(ctx).conflict_log)}
