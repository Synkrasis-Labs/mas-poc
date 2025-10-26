# petri_nets/petri_net.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import copy
from enum import Enum


class TransitionType(str, Enum):
    PROGRESS = "progress"      # advances DFA state
    READ = "read"              # neutral self-loops on state
    COORDINATION = "coord"     # explicit temporal constraints, if any


@dataclass
class Place:
    name: str
    tokens: int = 0
    capacity: Optional[int] = None  # None = unbounded

    def can_add_tokens(self, n: int) -> bool:
        """Simple capacity check (does not account for simultaneous consumption).
        Use Transition.is_enabled(...) for correct self-loop checks."""
        if self.capacity is None:
            return True
        return (self.tokens + n) <= self.capacity


@dataclass
class PetriTransition:
    name: str
    agent_id: str
    function_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    input_places: Dict[str, int] = field(default_factory=dict)   # place -> required tokens
    output_places: Dict[str, int] = field(default_factory=dict)  # place -> produced tokens
    transition_type: TransitionType = TransitionType.PROGRESS

    def matches_action(self, agent_id: str, function_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Tolerant argument matching:
        - If self.arguments is empty => wildcard (used for reads).
        - Otherwise, require that for every (k, v) in self.arguments:
            * the observed arguments contain k (or k under 'target' for x/y convenience),
            * if v is None => wildcard (accept any),
            * if v is numeric => equal within tolerance,
            * else => exact equality.
        - Extra keys in the observed arguments (e.g., yaw, speed) are ignored.
        """
        if self.agent_id != agent_id or self.function_name != function_name:
            return False

        # Wildcard: any args accepted (used for read/admin transitions)
        if not self.arguments:
            return True

        def _num_equal(a, b, eps=1e-3):
            try:
                return abs(float(a) - float(b)) <= eps
            except Exception:
                return False

        def _get_arg(args: Dict[str, Any], key: str):
            # Direct
            if key in args:
                return args[key]
            # Common nested shape for positions: {"target": {"x": ..., "y": ...}}
            if key in ("x", "y") and isinstance(args.get("target"), dict):
                return args["target"].get(key)
            return None

        for k, v in self.arguments.items():
            obs = _get_arg(arguments, k)

            # If spec wants this key but it's missing in observed args -> no match
            if obs is None:
                return False

            # None in spec = wildcard (accept any observed value)
            if v is None:
                continue

            # Numeric with tolerance
            if isinstance(v, (int, float)):
                if not _num_equal(obs, v):
                    return False
            else:
                # Exact match for non-numerics
                if obs != v:
                    return False

        return True


    def is_enabled(self, marking: Dict[str, Place]) -> bool:
        """
        A transition is enabled if:
          1) All input places exist and have enough tokens to consume.
          2) After accounting for *consumption and production together* on each place,
             no place exceeds its capacity or drops below 0.
             (This correctly handles self-loops consuming and producing on the same place.)
        """
        # 1) Must have enough tokens to consume
        for p, need in self.input_places.items():
            if p not in marking:
                return False
            if marking[p].tokens < need:
                return False

        # 2) Capacity check with net effect (consume then produce)
        #    Compute per-place delta = produced - consumed; verify final tokens within [0, capacity]
        for place_name in set(list(self.input_places.keys()) + list(self.output_places.keys())):
            consume = self.input_places.get(place_name, 0)
            produce = self.output_places.get(place_name, 0)

            if place_name not in marking:
                return False

            before = marking[place_name].tokens
            after = before - consume + produce

            if after < 0:
                return False

            cap = marking[place_name].capacity
            if cap is not None and after > cap:
                return False

        return True

    def fire(self, marking: Dict[str, Place]) -> None:
        """
        Fire the transition: atomically consume inputs then produce outputs.
        Assumes is_enabled(marking) was True.
        """
        # Consume
        for p, need in self.input_places.items():
            if p not in marking:
                raise ValueError(f"Missing place during consume: {p}")
            if marking[p].tokens < need:
                raise ValueError(f"Insufficient tokens in {p} during consume")
            marking[p].tokens -= need

        # Produce
        for p, add in self.output_places.items():
            if p not in marking:
                raise ValueError(f"Missing place during produce: {p}")
            cap = marking[p].capacity
            if cap is not None and (marking[p].tokens + add) > cap:
                raise ValueError(
                    f"Capacity exceeded in {p} during produce: "
                    f"would produce {add}, current={marking[p].tokens}, capacity={cap}"
                )
            marking[p].tokens += add


class PetriNet:
    def __init__(self):
        self.places: Dict[str, Place] = {}
        self.transitions: List[PetriTransition] = []

    # ----- construction -------------------------------------------------------

    def add_place(self, name: str, tokens: int = 0, capacity: Optional[int] = None) -> None:
        if name in self.places:
            # Update existing if re-added (idempotent for builder convenience)
            self.places[name].tokens = tokens
            self.places[name].capacity = capacity
            return
        self.places[name] = Place(name=name, tokens=tokens, capacity=capacity)

    def add_transition(self, t: PetriTransition) -> None:
        self.transitions.append(t)

    # ----- execution helpers --------------------------------------------------

    def get_initial_marking(self) -> Dict[str, Place]:
        """Return a deep copy of the places dict to act as the marking during replay."""
        return copy.deepcopy(self.places)

    # Optional utility if you ever want to look up transitions dynamically
    def find_matching_transitions(self, agent_id: str, function_name: str, arguments: Dict[str, Any]) -> List[PetriTransition]:
        return [t for t in self.transitions if t.matches_action(agent_id, function_name, arguments)]
