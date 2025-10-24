from __future__ import annotations
from typing import Dict, Any, Optional
from math import sqrt
from agents import function_tool, RunContextWrapper
from farm_context import FarmContext

WORLD_STATE_DESCRIPTION = "Farming Rover state: {}"

FUNCTION_SYSTEM_PROMPT = """
You operate an autonomous farming rover in an outdoor field.
The rover position is (x, y) in meters and yaw in radians. There is no Z axis.
You must respect safety mode, field bounds, and no-go zones. Use the functions exactly with the parameters shown.
Harvest/water/spray actions require the rover to be within the specified tolerances of the target plant or station.
"""

DECISION_SYSTEM_PROMPT = """
Plan a safe, correct sequence for the farming rover.
Always unlock safety before motion or actuation.
Use read-only checks (e.g., sense_pose, scan_plant, get_plant_pose, get_station_pose) if needed,
but avoid unnecessary detours.
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


class FarmingRover:
    """
    Stateless facade:
    - Holds ONLY the initial world-state seed dict and prompt strings.
    - All runtime state is in the run context (ctx.context.world_state) during a Runner.run(...).
    """
    def __init__(self):
        self.world_state_description = WORLD_STATE_DESCRIPTION
        self.function_system_prompt = FUNCTION_SYSTEM_PROMPT
        self.decision_system_prompt = DECISION_SYSTEM_PROMPT

        self._init_world_state: Dict[str, Any] = {
            "pose": {"x": 5.0, "y": 5.0, "yaw": 0.0},
            "home_pose": {"x": 5.0, "y": 5.0, "yaw": 0.0},

            "safety_mode": True,

            "field_bounds": {"xmin": 0.0, "xmax": 20.0, "ymin": 0.0, "ymax": 20.0},
            "no_go_xy": [
                {"xmin": 9.0, "xmax": 11.0, "ymin": 0.0, "ymax": 6.0},
            ],

            "plant_tolerance_xy": 0.30,
            "station_tolerance_xy": 0.40,

            "plants": {
                "plant_A": {"pose": {"x": 2.0, "y": 14.0}, "ripeness": 0.85, "moisture": 0.40, "pest": False, "has_fruit": True, "fruit_weight": 1.2},
                "plant_B": {"pose": {"x": 3.5, "y": 12.5}, "ripeness": 0.45, "moisture": 0.55, "pest": True,  "has_fruit": True, "fruit_weight": 0.8},
                "plant_C": {"pose": {"x": 14.0, "y": 8.5}, "ripeness": 0.92, "moisture": 0.30, "pest": False, "has_fruit": True, "fruit_weight": 1.5},
                "plant_D": {"pose": {"x": 16.5, "y": 15.0}, "ripeness": 0.20, "moisture": 0.20, "pest": True,  "has_fruit": False, "fruit_weight": 0.0},
            },

            "stations": {
                "collection_bin":   {"x": 6.0,  "y": 18.0, "yaw": 0.0},
                "charging_pad":     {"x": 1.0,  "y": 1.0,  "yaw": 0.0},
                "water_station":    {"x": 18.5, "y": 2.0,  "yaw": 0.0},
                "pesticide_refill": {"x": 18.0, "y": 18.0, "yaw": 0.0},
            },

            "battery_pct": 80.0,
            "hopper_capacity_kg": 10.0,
            "hopper_load_kg": 0.0,
            "water_tank_capacity_l": 10.0,
            "water_tank_l": 5.0,
            "pesticide_tank_capacity_ml": 500.0,
            "pesticide_tank_ml": 200.0,

            "ripe_threshold": 0.70,
            "max_moisture": 0.80,
        }


@function_tool
def get_world_state(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """Returns the full world-state snapshot as a plain dict."""
    return ws(ctx).model_dump()

@function_tool
def summarize_world_state(ctx: RunContextWrapper[FarmContext]) -> str:
    """Returns a compact human-readable summary of the world state."""
    w = ws(ctx)
    return (
        f"pose=({w.pose.x:.1f},{w.pose.y:.1f},{w.pose.yaw:.1f}); "
        f"safety={'ON' if w.safety_mode else 'OFF'}; "
        f"battery={w.battery_pct:.0f}%; "
        f"hopper={w.hopper_load_kg:.1f}/{w.hopper_capacity_kg:.1f}kg; "
        f"water={w.water_tank_l:.1f}/{w.water_tank_capacity_l:.1f}L; "
        f"pesticide={w.pesticide_tank_ml:.0f}/{w.pesticide_tank_capacity_ml:.0f}ml; "
        f"plants={len(w.plants)}"
    )

@function_tool
def unlock_safety_mode(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """Disables the rover's safety lock to allow motion and actuations."""
    w = ws(ctx)
    w.safety_mode = False
    return {"ok": True, "message": "Safety mode unlocked."}

@function_tool
def lock_safety_mode(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """Enables the rover's safety lock to prevent motion and actuations."""
    w = ws(ctx)
    w.safety_mode = True
    return {"ok": True, "message": "Safety mode locked."}


@function_tool
def move_to(ctx: RunContextWrapper[FarmContext], x: float, y: float, yaw: Optional[float] = None, speed: Optional[float] = None) -> Dict[str, Any]:
    """
    Drives the rover to the target (x, y) with an optional yaw (radians).
    Preconditions: safety off, within bounds, not in no-go zone.
    """
    w = ws(ctx)
    if w.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before moving."}
    if not _within_bounds(w, x, y):
        return {"ok": False, "error": "Target location out of field bounds."}
    if _in_no_go_zone(w, x, y):
        return {"ok": False, "error": "Target location lies within a no-go zone."}

    w.pose.x, w.pose.y = x, y
    if yaw is not None:
        w.pose.yaw = yaw
    return {"ok": True, "pose": {"x": w.pose.x, "y": w.pose.y, "yaw": w.pose.yaw}}

@function_tool
def move_home(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """Drives the rover to the configured home pose."""
    w = ws(ctx)
    if w.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before moving."}
    hp = w.home_pose
    return move_to(ctx, hp.x, hp.y, hp.yaw)


@function_tool
def harvest_fruit(ctx: RunContextWrapper[FarmContext], plant_id: str) -> Dict[str, Any]:
    """
    Harvests fruit from a specified plant at the rover’s current position.
    Preconditions: safety off, plant exists & ripe, within tolerance, capacity ok.
    """
    w = ws(ctx)
    if w.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before harvesting."}

    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    if not plant.has_fruit:
        return {"ok": False, "error": "No harvestable fruit on this plant."}
    if plant.ripeness < w.ripe_threshold:
        return {"ok": False, "error": "Fruit not ripe enough to harvest."}

    if _dist_xy(w.pose.x, w.pose.y, plant.pose.x, plant.pose.y) > w.plant_tolerance_xy:
        return {"ok": False, "error": "Not within harvesting tolerance."}

    if w.hopper_load_kg + plant.fruit_weight > w.hopper_capacity_kg:
        return {"ok": False, "error": "Hopper capacity exceeded."}

    w.hopper_load_kg += plant.fruit_weight
    plant.has_fruit = False
    return {
        "ok": True,
        "message": f"Harvested {plant.fruit_weight:.2f} kg from {plant_id}.",
        "hopper_load_kg": w.hopper_load_kg,
    }

@function_tool
def dump_hopper(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """
    Empties the hopper at the collection bin station.
    Preconditions: safety off, within station tolerance of collection_bin.
    """
    w = ws(ctx)
    if w.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before dumping."}

    bin_pose = w.stations.collection_bin
    if _dist_xy(w.pose.x, w.pose.y, bin_pose.x, bin_pose.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not at collection bin."}

    dumped = w.hopper_load_kg
    w.hopper_load_kg = 0.0
    return {"ok": True, "message": f"Dumped {dumped:.2f} kg at collection bin.", "dumped_kg": dumped}

@function_tool
def water_plant(ctx: RunContextWrapper[FarmContext], plant_id: str, liters: float) -> Dict[str, Any]:
    """
    Waters a plant by a specified amount.
    Preconditions: safety off, plant exists, liters>0 and <= tank, within tolerance, moisture safe.
    """
    w = ws(ctx)
    if w.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before watering."}
    if liters <= 0:
        return {"ok": False, "error": "Liters must be positive."}

    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}

    if _dist_xy(w.pose.x, w.pose.y, plant.pose.x, plant.pose.y) > w.plant_tolerance_xy:
        return {"ok": False, "error": "Not within watering tolerance."}
    if w.water_tank_l < liters:
        return {"ok": False, "error": "Not enough water in tank."}

    new_moisture = plant.moisture + liters / w.water_tank_capacity_l
    if new_moisture > w.max_moisture:
        return {"ok": False, "error": "Moisture would exceed safe limit."}

    w.water_tank_l -= liters
    plant.moisture = min(new_moisture, w.max_moisture)
    return {
        "ok": True,
        "message": f"Watered {plant_id} with {liters:.2f} L.",
        "water_tank_l": w.water_tank_l,
        "plant_moisture": plant.moisture,
    }

@function_tool
def spray_pesticide(ctx: RunContextWrapper[FarmContext], plant_id: str, ml: float) -> Dict[str, Any]:
    """
    Applies pesticide to a specified plant.
    Preconditions: safety off, ml>0 and <= tank, plant exists & pest==True, within tolerance.
    """
    w = ws(ctx)
    if w.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before spraying."}
    if ml <= 0:
        return {"ok": False, "error": "Milliliters must be positive."}

    plant = w.plants.get(plant_id)
    if plant is None:
        return {"ok": False, "error": "Unknown plant id."}
    if not plant.pest:
        return {"ok": False, "error": "No pest detected on this plant."}

    if _dist_xy(w.pose.x, w.pose.y, plant.pose.x, plant.pose.y) > w.plant_tolerance_xy:
        return {"ok": False, "error": "Not within spraying tolerance."}
    if w.pesticide_tank_ml < ml:
        return {"ok": False, "error": "Not enough pesticide in tank."}

    w.pesticide_tank_ml -= ml
    plant.pest = False
    return {
        "ok": True,
        "message": f"Sprayed {ml:.0f} ml pesticide on {plant_id}.",
        "pesticide_tank_ml": w.pesticide_tank_ml,
    }

@function_tool
def refill_water_tank(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """
    Refills the water tank to capacity at the water station.
    Preconditions: safety off, at water_station within tolerance.
    """
    w = ws(ctx)
    if w.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before refilling."}
    st = w.stations.water_station
    if _dist_xy(w.pose.x, w.pose.y, st.x, st.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not at water station."}

    w.water_tank_l = w.water_tank_capacity_l
    return {"ok": True, "message": f"Water tank refilled to {w.water_tank_l:.2f} L.", "water_tank_l": w.water_tank_l}

@function_tool
def refill_pesticide(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """
    Refills the pesticide tank to capacity at the pesticide refill station.
    Preconditions: safety off, at pesticide_refill within tolerance.
    """
    w = ws(ctx)
    if w.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before refilling."}
    st = w.stations.pesticide_refill
    if _dist_xy(w.pose.x, w.pose.y, st.x, st.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not at pesticide refill station."}

    w.pesticide_tank_ml = w.pesticide_tank_capacity_ml
    return {
        "ok": True,
        "message": f"Pesticide tank refilled to {w.pesticide_tank_ml:.0f} ml.",
        "pesticide_tank_ml": w.pesticide_tank_ml,
    }

@function_tool
def recharge(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Any]:
    """
    Recharges the rover's battery to 100% at the charging pad.
    Preconditions: safety off, at charging_pad within tolerance.
    """
    w = ws(ctx)
    if w.safety_mode:
        return {"ok": False, "error": "Safety mode is enabled. Unlock before recharging."}
    st = w.stations.charging_pad
    if _dist_xy(w.pose.x, w.pose.y, st.x, st.y) > w.station_tolerance_xy:
        return {"ok": False, "error": "Not at charging pad."}

    w.battery_pct = 100.0
    return {"ok": True, "message": "Battery recharged to 100%.", "battery_pct": w.battery_pct}

# ───────────── Sensors / Reads

@function_tool
def sense_pose(ctx: RunContextWrapper[FarmContext]) -> Dict[str, float]:
    """Read-only. Returns the current rover pose {'x','y','yaw'}."""
    p = ws(ctx).pose
    return {"x": p.x, "y": p.y, "yaw": p.yaw}

@function_tool
def sense_battery(ctx: RunContextWrapper[FarmContext]) -> str:
    """Read-only. Returns the current battery percentage string."""
    return f"{ws(ctx).battery_pct:.1f}%"

@function_tool
def sense_hopper(ctx: RunContextWrapper[FarmContext]) -> Dict[str, float]:
    """Read-only. Returns hopper load/capacity in kg."""
    w = ws(ctx)
    return {"load_kg": w.hopper_load_kg, "capacity_kg": w.hopper_capacity_kg}

@function_tool
def list_plants(ctx: RunContextWrapper[FarmContext]) -> Dict[str, Dict[str, Any]]:
    """Read-only. Returns all plants and attributes."""
    w = ws(ctx)
    # Convert Pydantic models to plain dicts
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
