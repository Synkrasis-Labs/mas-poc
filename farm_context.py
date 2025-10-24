# farm_context.py
from __future__ import annotations
from typing import Dict, List, Optional, Any
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
    reserved_by: Optional[str] = None  # NEW: Track which rover has reserved this plant


class StationPose(BaseModel):
    x: float
    y: float
    yaw: float = 0.0
    occupied_by: Optional[str] = None  # NEW: Track which rover is at this station


class Stations(BaseModel):
    collection_bin: StationPose
    charging_pad: StationPose
    water_station: StationPose
    pesticide_refill: StationPose


class RoverState(BaseModel):
    """Individual rover state in the multi-agent system."""
    # Kinematics
    pose: Pose
    home_pose: Pose
    
    # Safety
    safety_mode: bool = True
    
    # Resources
    battery_pct: float = Field(ge=0.0, le=100.0)
    hopper_capacity_kg: float = Field(gt=0.0)
    hopper_load_kg: float = Field(ge=0.0)
    water_tank_capacity_l: float = Field(gt=0.0)
    water_tank_l: float = Field(ge=0.0)
    pesticide_tank_capacity_ml: float = Field(gt=0.0)
    pesticide_tank_ml: float = Field(ge=0.0)
    
    # Task management
    status: str = "idle"  # idle, moving, harvesting, watering, spraying, refilling, dumping, charging
    current_task: Optional[str] = None
    task_queue: List[str] = Field(default_factory=list)
    
    @model_validator(mode="after")
    def _resource_consistency(self):
        assert self.hopper_load_kg <= self.hopper_capacity_kg, "hopper load exceeds capacity"
        assert self.water_tank_l <= self.water_tank_capacity_l, "water tank exceeds capacity"
        assert self.pesticide_tank_ml <= self.pesticide_tank_capacity_ml, "pesticide tank exceeds capacity"
        return self


class WorldState(BaseModel):
    """Shared world state for all rovers in the multi-agent system."""
    
    # Workspace
    field_bounds: Bounds
    no_go_xy: List[Rect] = Field(default_factory=list)
    
    # Tolerances
    plant_tolerance_xy: float = Field(gt=0.0)
    station_tolerance_xy: float = Field(gt=0.0)
    collision_safety_radius: float = Field(gt=0.0, default=1.0)
    
    # Multi-agent entities
    rovers: Dict[str, RoverState]
    
    # Shared resources
    plants: Dict[str, Plant]
    stations: Stations
    
    # Policy thresholds
    ripe_threshold: float = Field(ge=0.0, le=1.0)
    max_moisture: float = Field(ge=0.0, le=1.0)
    
    # Coordination logs
    task_log: List[Dict[str, Any]] = Field(default_factory=list)
    conflict_log: List[Dict[str, Any]] = Field(default_factory=list)
    
    @model_validator(mode="after")
    def _validate_rovers(self):
        assert len(self.rovers) > 0, "Must have at least one rover"
        return self


class FarmContext(BaseModel):
    """Context for a single rover agent in the multi-agent system."""
    world_state: WorldState
    rover_id: str  # NEW: Which rover this context belongs to
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    actor: str = "RoverAgent"
    tool_calls: List[Dict] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    
    @classmethod
    def from_init_dict(cls, init_state: Dict, rover_id: str) -> "FarmContext":
        """
        Build a FarmContext for a specific rover from the init world state dict.
        
        Args:
            init_state: The initial world state dictionary
            rover_id: The ID of the rover this context is for
        """
        world_state = WorldState.model_validate(init_state)
        
        # Validate that the rover_id exists
        if rover_id not in world_state.rovers:
            raise ValueError(f"Rover ID '{rover_id}' not found in world state. Available rovers: {list(world_state.rovers.keys())}")
        
        return cls(world_state=world_state, rover_id=rover_id)
    
    def snapshot(self) -> Dict:
        """Return a JSON-serializable snapshot of the full world state."""
        return self.world_state.model_dump()
    
    def my_rover_snapshot(self) -> Dict:
        """Return a snapshot of just this rover's state."""
        rover = self.world_state.rovers.get(self.rover_id)
        if rover is None:
            return {"error": "Rover not found"}
        return rover.model_dump()
    
    def short_summary(self) -> str:
        """Return a short summary for this specific rover."""
        ws = self.world_state
        rover = ws.rovers.get(self.rover_id)
        
        if rover is None:
            return f"[{self.rover_id}] ERROR: Rover not found"
        
        return (
            f"[{self.rover_id}] pose=({rover.pose.x:.1f},{rover.pose.y:.1f},{rover.pose.yaw:.1f}); "
            f"safety={'ON' if rover.safety_mode else 'OFF'}; "
            f"status={rover.status}; "
            f"battery={rover.battery_pct:.0f}%; "
            f"hopper={rover.hopper_load_kg:.1f}/{rover.hopper_capacity_kg:.1f}kg; "
            f"water={rover.water_tank_l:.1f}/{rover.water_tank_capacity_l:.1f}L; "
            f"pesticide={rover.pesticide_tank_ml:.0f}/{rover.pesticide_tank_capacity_ml:.0f}ml; "
            f"plants={len(ws.plants)}; "
            f"other_rovers={len(ws.rovers)-1}"
        )
    
    def get_other_rovers(self) -> Dict[str, RoverState]:
        """Get information about all other rovers (excluding this one)."""
        return {rid: rover for rid, rover in self.world_state.rovers.items() if rid != self.rover_id}
    
    def get_available_plants(self) -> Dict[str, Plant]:
        """Get plants that are not reserved by other rovers."""
        return {
            pid: plant for pid, plant in self.world_state.plants.items()
            if plant.reserved_by is None or plant.reserved_by == self.rover_id
        }