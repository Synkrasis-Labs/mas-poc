# farm_context.py
from __future__ import annotations
from typing import Dict, List
from pydantic import BaseModel, Field, model_validator
from uuid import uuid4



class XY(BaseModel):
    x: float
    y: float

class Pose(BaseModel):
    x: float
    y: float
    yaw: float = 0.0

class Bounds(BaseModel):
    xmin: float
    xmax: float
    ymin: float
    ymax: float

    @model_validator(mode="after")
    def _check_ranges(self):
        assert self.xmin <= self.xmax, "xmin must be <= xmax"
        assert self.ymin <= self.ymax, "ymin must be <= ymax"
        return self

class Rect(BaseModel):
    xmin: float
    xmax: float
    ymin: float
    ymax: float

    @model_validator(mode="after")
    def _check(self):
        assert self.xmin <= self.xmax and self.ymin <= self.ymax, "invalid rectangle"
        return self



class Plant(BaseModel):
    pose: XY
    ripeness: float = Field(ge=0.0, le=1.0)
    moisture: float = Field(ge=0.0, le=1.0)
    pest: bool
    has_fruit: bool
    fruit_weight: float = Field(ge=0.0)

class Stations(BaseModel):
    collection_bin: Pose
    charging_pad: Pose
    water_station: Pose
    pesticide_refill: Pose


class WorldState(BaseModel):
    # Kinematics
    pose: Pose
    home_pose: Pose

    # Safety
    safety_mode: bool = True

    # Workspace
    field_bounds: Bounds
    no_go_xy: List[Rect] = Field(default_factory=list)

    # Tolerances
    plant_tolerance_xy: float = Field(gt=0.0)
    station_tolerance_xy: float = Field(gt=0.0)

    # Entities
    plants: Dict[str, Plant]
    stations: Stations

    # Resources
    battery_pct: float = Field(ge=0.0, le=100.0)
    hopper_capacity_kg: float = Field(gt=0.0)
    hopper_load_kg: float = Field(ge=0.0)
    water_tank_capacity_l: float = Field(gt=0.0)
    water_tank_l: float = Field(ge=0.0)
    pesticide_tank_capacity_ml: float = Field(gt=0.0)
    pesticide_tank_ml: float = Field(ge=0.0)

    # Policy thresholds
    ripe_threshold: float = Field(ge=0.0, le=1.0)
    max_moisture: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _resource_consistency(self):
        assert self.hopper_load_kg <= self.hopper_capacity_kg, "hopper load exceeds capacity"
        assert self.water_tank_l <= self.water_tank_capacity_l, "water tank exceeds capacity"
        assert self.pesticide_tank_ml <= self.pesticide_tank_capacity_ml, "pesticide tank exceeds capacity"
        return self



class FarmContext(BaseModel):
    world_state: WorldState
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    actor: str = "PlannerAgent"

    tool_calls: List[Dict] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

    @classmethod
    def from_init_dict(cls, init_state: Dict) -> "FarmContext":
        """
        Build a FarmContext from your existing _init_world_state dict.
        """
        return cls(world_state=WorldState.model_validate(init_state))

    def snapshot(self) -> Dict:
        """Return a JSON-serializable snapshot of the full state."""
        return self.world_state.model_dump()

    def short_summary(self) -> str:
        ws = self.world_state
        return (
            f"pose=({ws.pose.x:.1f},{ws.pose.y:.1f},{ws.pose.yaw:.1f}); "
            f"safety={'ON' if ws.safety_mode else 'OFF'}; "
            f"battery={ws.battery_pct:.0f}%; "
            f"hopper={ws.hopper_load_kg:.1f}/{ws.hopper_capacity_kg:.1f}kg; "
            f"water={ws.water_tank_l:.1f}/{ws.water_tank_capacity_l:.1f}L; "
            f"pesticide={ws.pesticide_tank_ml:.0f}/{ws.pesticide_tank_capacity_ml:.0f}ml; "
            f"plants={len(ws.plants)}"
        )
