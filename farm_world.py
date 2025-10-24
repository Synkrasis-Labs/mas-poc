# farm_world.py - Multi-Agent System Version (Fully Fixed)
from __future__ import annotations
from typing import Dict, Any, Optional, List
from math import sqrt
from agents import function_tool, RunContextWrapper
from farm_context import FarmContext
import datetime

WORLD_STATE_DESCRIPTION = "Multi-Agent Farming System state: {}"

FUNCTION_SYSTEM_PROMPT = """
You operate ONE autonomous farming rover in a multi-agent outdoor field environment.
Your rover has a unique ID. Other rovers may be operating simultaneously.
The rover position is (x, y) in meters and yaw in radians. There is no Z axis.
You must respect safety mode, field bounds, no-go zones, and avoid collisions with other rovers.
Use the functions exactly with the parameters shown.
Harvest/water/spray actions require the rover to be within the specified tolerances of the target plant or station.
Coordinate with other agents to avoid conflicts and optimize task allocation.
"""

DECISION_SYSTEM_PROMPT = """
Plan a safe, correct sequence for your farming rover in a multi-agent environment.
Always unlock safety before motion or actuation.
Be aware of other rovers' positions and tasks to avoid conflicts.
Use read-only checks (e.g., sense_pose, scan_plant, get_plant_pose, get_station_pose, list_all_rovers) when needed.
Communicate task intentions to prevent resource conflicts (e.g., two rovers harvesting the same plant).
"""


def ws(ctx):
    """Fetch the run-scoped WorldState from the Agents SDK context."""
    return ctx.context.world_state


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


def _check_collision_with_rovers(wstate, rover_id: str, target_x: float, target_y: float, safety_radius: float = 1.0) -> tuple[bool, Optional[str]]:
    """
    Check if target position would collide with another rover.
    Returns (is_collision, conflicting_rover_id)
    """
    for rid, rover in wstate.rovers.items():
        if rid == rover_id:  # Skip self
            continue
        dist = _dist_xy(target_x, target_y, rover.pose.x, rover.pose.y)
        if dist < safety_radius:
            return True, rid
    return False, None


def _check_station_occupied(wstate, rover_id: str, station_x: float, station_y: float, tolerance: float) -> tuple[bool, Optional[str]]:
    """
    Check if a station is currently occupied by another rover.
    Returns (is_occupied, occupying_rover_id)
    """
    for rid, rover in wstate.rovers.items():
        if rid == rover_id:
            continue
        dist = _dist_xy(station_x, station_y, rover.pose.x, rover.pose.y)
        if dist < tolerance * 2:  # Station occupied if rover is within double tolerance
            return True, rid
    return False, None


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPER FUNCTIONS (Not decorated with @function_tool)
# These are safe to call from within other functions
# ═══════════════════════════════════════════════════════════════════════════════

def _log_task_completion_impl(w, rover_id: str, task_description: str) -> None:
    """Internal helper to log task completion without calling a tool."""
    log_entry = {
        "rover_id": rover_id,
        "task": task_description,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    w.task_log.append(log_entry)


def _move_to_impl(w, my_id: str, x: float, y: float, yaw: Optional[float] = None) -> Dict[str, Any]:
    """Internal implementation of move_to logic without the @function_tool decorator."""
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before moving."}
    
    if not _within_bounds(w, x, y):
        return {"ok": False, "error": "Target location out of field bounds."}
    
    if _in_no_go_zone(w, x, y):
        return {"ok": False, "error": "Target location lies within a no-go zone."}
    
    # Check collision with other rovers
    collision, conflicting_rover = _check_collision_with_rovers(w, my_id, x, y, w.collision_safety_radius)
    if collision:
        w.conflict_log.append({
            "type": "collision_avoided",
            "rover": my_id,
            "conflicting_rover": conflicting_rover,
            "location": {"x": x, "y": y}
        })
        return {"ok": False, "error": f"Target location too close to {conflicting_rover}. Collision risk."}
    
    rover.pose.x, rover.pose.y = x, y
    if yaw is not None:
        rover.pose.yaw = yaw
    
    rover.status = "moving"
    return {"ok": True, "pose": {"x": rover.pose.x, "y": rover.pose.y, "yaw": rover.pose.yaw}}


# ═══════════════════════════════════════════════════════════════════════════════
# FARMING ROVER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class FarmingRover:
    """
    Stateless facade for Multi-Agent System:
    - Holds ONLY the initial world-state seed dict and prompt strings.
    - All runtime state is in the run context (ctx.context.world_state) during a Runner.run(...).
    - Supports multiple rovers operating simultaneously.
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

            # Multi-rover configuration
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

            # Shared resources (plants are shared among all rovers)
            "plants": {
                "plant_A": {"pose": {"x": 2.0, "y": 14.0}, "ripeness": 0.85, "moisture": 0.40, "pest": False, "has_fruit": True, "fruit_weight": 1.2, "reserved_by": None},
                "plant_B": {"pose": {"x": 3.5, "y": 12.5}, "ripeness": 0.45, "moisture": 0.55, "pest": True, "has_fruit": True, "fruit_weight": 0.8, "reserved_by": None},
                "plant_C": {"pose": {"x": 14.0, "y": 8.5}, "ripeness": 0.92, "moisture": 0.30, "pest": False, "has_fruit": True, "fruit_weight": 1.5, "reserved_by": None},
                "plant_D": {"pose": {"x": 16.5, "y": 15.0}, "ripeness": 0.20, "moisture": 0.20, "pest": True, "has_fruit": False, "fruit_weight": 0.0, "reserved_by": None},
                "plant_E": {"pose": {"x": 7.0, "y": 8.0}, "ripeness": 0.88, "moisture": 0.35, "pest": False, "has_fruit": True, "fruit_weight": 1.3, "reserved_by": None},
                "plant_F": {"pose": {"x": 12.0, "y": 16.0}, "ripeness": 0.75, "moisture": 0.45, "pest": True, "has_fruit": True, "fruit_weight": 1.0, "reserved_by": None},
            },

            # Shared stations
            "stations": {
                "collection_bin": {"x": 6.0, "y": 18.0, "yaw": 0.0, "occupied_by": None},
                "charging_pad": {"x": 1.0, "y": 1.0, "yaw": 0.0, "occupied_by": None},
                "water_station": {"x": 18.5, "y": 2.0, "yaw": 0.0, "occupied_by": None},
                "pesticide_refill": {"x": 18.0, "y": 18.0, "yaw": 0.0, "occupied_by": None},
            },

            # Policy thresholds
            "ripe_threshold": 0.70,
            "max_moisture": 0.80,

            # Task coordination
            "task_log": [],
            "conflict_log": [],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-AGENT COORDINATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@function_tool
def get_my_rover_id(ctx: RunContextWrapper[FarmContext]) -> str:
    """Returns the ID of the current rover agent."""
    return ctx.context.rover_id


@function_tool
def list_all_rovers(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Dict[str, Any]]:
    """Returns information about all rovers in the system."""
    w = ws(ctx)
    return {rid: rover.model_dump() for rid, rover in w.rovers.items()}


@function_tool
def get_rover_status(ctx: RunContextWrapper[FarmContext], rover_id: str) -> Dict[str, Any]:
    """Get the status of a specific rover."""
    rover = ws(ctx).rovers.get(rover_id)
    if rover is None:
        return {"error": "Unknown rover id."}
    return rover.model_dump()


@function_tool
def reserve_plant(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    """
    Reserve a plant for this rover to prevent conflicts.
    Returns success if plant is available or already reserved by this rover.
    """
    w = ws(ctx)
    my_id = ctx.context.rover_id
    plant = w.plants.get(plant_id)
    
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    
    if plant.reserved_by is None:
        plant.reserved_by = my_id
        return {"ok": True, "message": f"Plant {plant_id} reserved by {my_id}."}
    elif plant.reserved_by == my_id:
        return {"ok": True, "message": f"Plant {plant_id} already reserved by you."}
    else:
        return {"ok": False, "error": f"Plant {plant_id} is reserved by {plant.reserved_by}."}


@function_tool
def release_plant(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    """Release a plant reservation."""
    w = ws(ctx)
    my_id = ctx.context.rover_id
    plant = w.plants.get(plant_id)
    
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    
    if plant.reserved_by == my_id:
        plant.reserved_by = None
        return {"ok": True, "message": f"Plant {plant_id} released."}
    else:
        return {"ok": False, "error": "Plant not reserved by you."}


@function_tool
def reserve_station(ctx: RunContextWrapper[FarmContext], station_name: str) -> Dict[str, Any]:
    """Reserve a station for this rover."""
    w = ws(ctx)
    my_id = ctx.context.rover_id
    stations = w.stations
    station = getattr(stations, station_name, None)
    
    if station is None:
        return {"ok": False, "error": "Unknown station name."}
    
    if station.occupied_by is None:
        station.occupied_by = my_id
        return {"ok": True, "message": f"Station {station_name} reserved by {my_id}."}
    elif station.occupied_by == my_id:
        return {"ok": True, "message": f"Station {station_name} already reserved by you."}
    else:
        return {"ok": False, "error": f"Station {station_name} is occupied by {station.occupied_by}."}


@function_tool
def release_station(ctx: RunContextWrapper[FarmContext], station_name: str) -> Dict[str, Any]:
    """Release a station reservation."""
    w = ws(ctx)
    my_id = ctx.context.rover_id
    stations = w.stations
    station = getattr(stations, station_name, None)
    
    if station is None:
        return {"ok": False, "error": "Unknown station name."}
    
    if station.occupied_by == my_id:
        station.occupied_by = None
        return {"ok": True, "message": f"Station {station_name} released."}
    else:
        return {"ok": False, "error": "Station not reserved by you."}


@function_tool
def update_my_status(ctx: RunContextWrapper[FarmContext], status: str, task_description: Optional[str] = None) -> Dict[str, Any]:
    """
    Update this rover's status.
    Valid statuses: idle, moving, harvesting, watering, spraying, refilling, dumping, charging
    """
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
    """Log a completed task to the global task log."""
    w = ws(ctx)
    my_id = ctx.context.rover_id
    _log_task_completion_impl(w, my_id, task_description)
    return {"ok": True, "message": "Task logged."}


# ═══════════════════════════════════════════════════════════════════════════════
# WORLD STATE QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

@function_tool
def get_world_state(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """Returns the full world-state snapshot as a plain dict."""
    return ws(ctx).model_dump()


@function_tool
def summarize_world_state(ctx: RunContextWrapper[FarmContext]) -> str:
    """Returns a compact human-readable summary of the world state for this rover."""
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


# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY & CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

@function_tool
def unlock_safety_mode(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """Disables the rover's safety lock to allow motion and actuations."""
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    rover.safety_mode = False
    return {"ok": True, "message": "Safety mode unlocked."}


@function_tool
def lock_safety_mode(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """Enables the rover's safety lock to prevent motion and actuations."""
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    rover.safety_mode = True
    return {"ok": True, "message": "Safety mode locked."}


# ═══════════════════════════════════════════════════════════════════════════════
# MOTION
# ═══════════════════════════════════════════════════════════════════════════════

@function_tool
def move_to(ctx: RunContextWrapper[FarmContext], x: float, y: float, yaw: Optional[float] = None, speed: Optional[float] = None) -> Dict[str, Any]:
    """
    Drives the rover to the target (x, y) with an optional yaw (radians).
    Preconditions: safety off, within bounds, not in no-go zone, no collision with other rovers.
    """
    w = ws(ctx)
    my_id = ctx.context.rover_id
    return _move_to_impl(w, my_id, x, y, yaw)


@function_tool
def move_home(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """Drives the rover to its configured home pose."""
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    hp = rover.home_pose
    # FIXED: Use helper function instead of calling move_to tool
    return _move_to_impl(w, my_id, hp.x, hp.y, hp.yaw)


# ═══════════════════════════════════════════════════════════════════════════════
# PLANT OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@function_tool
def harvest_fruit(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    """
    Harvests fruit from a specified plant at the rover's current position.
    Preconditions: safety off, plant exists & ripe & reserved by this rover, within tolerance, capacity ok.
    """
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
    
    # Check reservation
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
    plant.reserved_by = None  # Auto-release after harvest
    rover.status = "harvesting"
    
    # FIXED: Use helper function instead of calling log_task_completion tool
    _log_task_completion_impl(w, my_id, f"Harvested {plant.fruit_weight:.2f}kg from {plant_id}")
    
    return {
        "ok": True,
        "message": f"Harvested {plant.fruit_weight:.2f} kg from {plant_id}.",
        "hopper_load_kg": rover.hopper_load_kg,
    }


@function_tool
def water_plant(ctx: RunContextWrapper[FarmContext], plant_id: str, liters: float) -> Dict[str, Any]:
    """
    Waters a plant by a specified amount.
    Preconditions: safety off, plant exists & reserved, liters>0 and <= tank, within tolerance, moisture safe.
    """
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before watering."}
    
    if liters <= 0:
        return {"ok": False, "error": "Liters must be positive."}

    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    
    # Check reservation
    if plant.reserved_by != my_id:
        return {"ok": False, "error": f"Plant not reserved by you. Reserved by: {plant.reserved_by}"}

    if _dist_xy(rover.pose.x, rover.pose.y, plant.pose.x, plant.pose.y) > w.plant_tolerance_xy:
        return {"ok": False, "error": "Not within watering tolerance."}
    
    if rover.water_tank_l < liters:
        return {"ok": False, "error": "Not enough water in tank."}

    new_moisture = plant.moisture + liters / rover.water_tank_capacity_l
    if new_moisture > w.max_moisture:
        return {"ok": False, "error": "Moisture would exceed safe limit."}

    rover.water_tank_l -= liters
    plant.moisture = min(new_moisture, w.max_moisture)
    plant.reserved_by = None  # Auto-release after watering
    rover.status = "watering"
    
    # FIXED: Use helper function instead of calling log_task_completion tool
    _log_task_completion_impl(w, my_id, f"Watered {plant_id} with {liters:.2f}L")
    
    return {
        "ok": True,
        "message": f"Watered {plant_id} with {liters:.2f} L.",
        "water_tank_l": rover.water_tank_l,
        "plant_moisture": plant.moisture,
    }


@function_tool
def spray_pesticide(ctx: RunContextWrapper[FarmContext], plant_id: str, ml: float) -> Dict[str, Any]:
    """
    Applies pesticide to a specified plant.
    Preconditions: safety off, ml>0 and <= tank, plant exists & pest==True & reserved, within tolerance.
    """
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before spraying."}
    
    if ml <= 0:
        return {"ok": False, "error": "Milliliters must be positive."}

    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    
    # Check reservation
    if plant.reserved_by != my_id:
        return {"ok": False, "error": f"Plant not reserved by you. Reserved by: {plant.reserved_by}"}
    
    if not plant.pest:
        return {"ok": False, "error": "No pest detected on this plant."}

    if _dist_xy(rover.pose.x, rover.pose.y, plant.pose.x, plant.pose.y) > w.plant_tolerance_xy:
        return {"ok": False, "error": "Not within spraying tolerance."}
    
    if rover.pesticide_tank_ml < ml:
        return {"ok": False, "error": "Not enough pesticide in tank."}

    rover.pesticide_tank_ml -= ml
    plant.pest = False
    plant.reserved_by = None  # Auto-release after spraying
    rover.status = "spraying"
    
    # FIXED: Use helper function instead of calling log_task_completion tool
    _log_task_completion_impl(w, my_id, f"Sprayed {ml:.0f}ml pesticide on {plant_id}")
    
    return {
        "ok": True,
        "message": f"Sprayed {ml:.0f} ml pesticide on {plant_id}.",
        "pesticide_tank_ml": rover.pesticide_tank_ml,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STATION OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@function_tool
def dump_hopper(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """
    Empties the hopper at the collection bin station.
    Preconditions: safety off, within station tolerance of collection_bin, station reserved.
    """
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before dumping."}

    bin_pose = w.stations.collection_bin
    
    # Check reservation
    if bin_pose.occupied_by != my_id:
        return {"ok": False, "error": f"Collection bin not reserved by you. Occupied by: {bin_pose.occupied_by}"}
    
    if _dist_xy(rover.pose.x, rover.pose.y, bin_pose.x, bin_pose.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not at collection bin."}

    dumped = rover.hopper_load_kg
    rover.hopper_load_kg = 0.0
    rover.status = "dumping"
    
    # FIXED: Use helper function instead of calling log_task_completion tool
    _log_task_completion_impl(w, my_id, f"Dumped {dumped:.2f}kg at collection bin")
    
    return {"ok": True, "message": f"Dumped {dumped:.2f} kg at collection bin.", "dumped_kg": dumped}


@function_tool
def refill_water_tank(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """
    Refills the water tank to capacity at the water station.
    Preconditions: safety off, at water_station within tolerance, station reserved.
    """
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before refilling."}
    
    st = w.stations.water_station
    
    # Check reservation
    if st.occupied_by != my_id:
        return {"ok": False, "error": f"Water station not reserved by you. Occupied by: {st.occupied_by}"}
    
    if _dist_xy(rover.pose.x, rover.pose.y, st.x, st.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not at water station."}

    rover.water_tank_l = rover.water_tank_capacity_l
    rover.status = "refilling"
    
    # FIXED: Use helper function instead of calling log_task_completion tool
    _log_task_completion_impl(w, my_id, f"Refilled water tank to {rover.water_tank_l:.2f}L")
    
    return {"ok": True, "message": f"Water tank refilled to {rover.water_tank_l:.2f} L.", "water_tank_l": rover.water_tank_l}


@function_tool
def refill_pesticide(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """
    Refills the pesticide tank to capacity at the pesticide refill station.
    Preconditions: safety off, at pesticide_refill within tolerance, station reserved.
    """
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before refilling."}
    
    st = w.stations.pesticide_refill
    
    # Check reservation
    if st.occupied_by != my_id:
        return {"ok": False, "error": f"Pesticide station not reserved by you. Occupied by: {st.occupied_by}"}
    
    if _dist_xy(rover.pose.x, rover.pose.y, st.x, st.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not at pesticide refill station."}

    rover.pesticide_tank_ml = rover.pesticide_tank_capacity_ml
    rover.status = "refilling"
    
    # FIXED: Use helper function instead of calling log_task_completion tool
    _log_task_completion_impl(w, my_id, f"Refilled pesticide tank to {rover.pesticide_tank_ml:.0f}ml")
    
    return {
        "ok": True,
        "message": f"Pesticide tank refilled to {rover.pesticide_tank_ml:.0f} ml.",
        "pesticide_tank_ml": rover.pesticide_tank_ml,
    }


@function_tool
def recharge(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """
    Recharges the rover's battery to 100% at the charging pad.
    Preconditions: safety off, at charging_pad within tolerance, station reserved.
    """
    w = ws(ctx)
    my_id = ctx.context.rover_id
    rover = w.rovers.get(my_id)
    
    if rover is None:
        return {"ok": False, "error": "Rover not found."}
    
    if rover.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before recharging."}
    
    st = w.stations.charging_pad
    
    # Check reservation
    if st.occupied_by != my_id:
        return {"ok": False, "error": f"Charging pad not reserved by you. Occupied by: {st.occupied_by}"}
    
    if _dist_xy(rover.pose.x, rover.pose.y, st.x, st.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not at charging pad."}

    rover.battery_pct = 100.0
    rover.status = "charging"
    
    # FIXED: Use helper function instead of calling log_task_completion tool
    _log_task_completion_impl(w, my_id, "Recharged battery to 100%")
    
    return {"ok": True, "message": "Battery recharged to 100%.", "battery_pct": rover.battery_pct}


# ═══════════════════════════════════════════════════════════════════════════════
# SENSORS / READ-ONLY OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@function_tool
def sense_pose(ctx: RunContextWrapper[FarmContext]) -> Dict[str, float]:
    """Read-only. Returns the current rover pose {'x','y','yaw'}."""
    my_id = ctx.context.rover_id
    rover = ws(ctx).rovers.get(my_id)
    if rover is None:
        return {"error": "Rover not found."}
    p = rover.pose
    return {"x": p.x, "y": p.y, "yaw": p.yaw}


@function_tool
def sense_battery(ctx: RunContextWrapper[FarmContext]) -> str:
    """Read-only. Returns the current battery percentage string."""
    my_id = ctx.context.rover_id
    rover = ws(ctx).rovers.get(my_id)
    if rover is None:
        return "Error: Rover not found."
    return f"{rover.battery_pct:.1f}%"


@function_tool
def sense_hopper(ctx: RunContextWrapper[FarmContext]) -> Dict[str, float]:
    """Read-only. Returns hopper load/capacity in kg."""
    my_id = ctx.context.rover_id
    rover = ws(ctx).rovers.get(my_id)
    if rover is None:
        return {"error": "Rover not found."}
    return {"load_kg": rover.hopper_load_kg, "capacity_kg": rover.hopper_capacity_kg}


@function_tool
def list_plants(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Dict[str, Any]]:
    """Read-only. Returns all plants and attributes."""
    w = ws(ctx)
    return {pid: p.model_dump() for pid, p in w.plants.items()}


@function_tool
def scan_plant(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    """Read-only. Returns attributes for a single plant, or {'error': ...}."""
    plant = ws(ctx).plants.get(plant_id)
    if plant is None:
        return {"error": "Unknown plant id."}
    return plant.model_dump()


@function_tool
def get_plant_pose(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, float] | Dict[str, str]:
    """Read-only. Returns {'x','y'} or {'error': ...} for unknown plant."""
    plant = ws(ctx).plants.get(plant_id)
    if plant is None:
        return {"error": "Unknown plant id."}
    return {"x": plant.pose.x, "y": plant.pose.y}


@function_tool
def get_station_pose(ctx: RunContextWrapper[FarmContext], station_name: str) -> Dict[str, float] | Dict[str, str]:
    """Read-only. Returns {'x','y','yaw'} for a named station, or {'error': ...}."""
    stations = ws(ctx).stations
    st = getattr(stations, station_name, None)
    if st is None:
        return {"error": "Unknown station name."}
    return {"x": st.x, "y": st.y, "yaw": st.yaw}


@function_tool
def get_task_log(ctx: RunContextWrapper[FarmContext]) -> List[Dict[str, Any]]:
    """Read-only. Returns the global task completion log."""
    return ws(ctx).task_log


@function_tool
def get_conflict_log(ctx: RunContextWrapper[FarmContext]) -> List[Dict[str, Any]]:
    """Read-only. Returns the log of conflicts/collisions avoided."""
    return ws(ctx).conflict_log