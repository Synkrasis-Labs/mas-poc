# petri_nets/petri_net.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class TransitionType(Enum):
    """Type of transition for tracking purposes"""
    PROGRESS = "progress"      # State-changing action
    READ = "read"             # Read-only action (self-loop)
    COORDINATION = "coord"    # Synchronization between agents


@dataclass
class Place:
    """A place in the Petri Net"""
    name: str
    tokens: int = 0
    capacity: Optional[int] = None  # None = unbounded
    
    def can_add_tokens(self, n: int) -> bool:
        if self.capacity is None:
            return True
        return self.tokens + n <= self.capacity
    
    def add_tokens(self, n: int):
        if not self.can_add_tokens(n):
            raise ValueError(f"Cannot add {n} tokens to {self.name} (capacity exceeded)")
        self.tokens += n
    
    def remove_tokens(self, n: int):
        if self.tokens < n:
            raise ValueError(f"Cannot remove {n} tokens from {self.name} (insufficient tokens)")
        self.tokens -= n
    
    def __repr__(self):
        cap_str = f"/{self.capacity}" if self.capacity else ""
        return f"Place({self.name}: {self.tokens}{cap_str})"


@dataclass
class PetriTransition:
    """A transition in the Petri Net"""
    name: str
    agent_id: Optional[str]  # Which agent performs this transition (None = any)
    function_name: str
    arguments: Dict[str, Any]
    
    # Input/output arcs
    input_places: Dict[str, int] = field(default_factory=dict)   # place_name -> tokens_needed
    output_places: Dict[str, int] = field(default_factory=dict)  # place_name -> tokens_produced
    
    transition_type: TransitionType = TransitionType.PROGRESS
    
    def is_enabled(self, marking: Dict[str, Place]) -> bool:
        """Check if transition can fire given current marking"""
        for place_name, tokens_needed in self.input_places.items():
            if place_name not in marking:
                return False
            if marking[place_name].tokens < tokens_needed:
                return False
        
        # Check capacity constraints for output places
        for place_name, tokens_produced in self.output_places.items():
            if place_name not in marking:
                return False
            if not marking[place_name].can_add_tokens(tokens_produced):
                return False
        
        return True
    
    def fire(self, marking: Dict[str, Place]) -> Dict[str, Place]:
        """Fire the transition, returning new marking (modifies in place)"""
        if not self.is_enabled(marking):
            raise ValueError(f"Transition {self.name} is not enabled")
        
        # Remove tokens from input places
        for place_name, tokens_needed in self.input_places.items():
            marking[place_name].remove_tokens(tokens_needed)
        
        # Add tokens to output places
        for place_name, tokens_produced in self.output_places.items():
            marking[place_name].add_tokens(tokens_produced)
        
        return marking
    
    def matches_action(self, agent_id: str, function_name: str, arguments: Dict[str, Any]) -> bool:
        """Check if this transition matches an agent action"""
        # Check agent
        if self.agent_id is not None and self.agent_id != agent_id:
            return False
        
        # Check function name
        if self.function_name != function_name:
            return False
        
        # Check arguments (all required args must match)
        for arg_name, arg_value in self.arguments.items():
            if arg_name not in arguments:
                return False
            if arg_value is not None and arguments[arg_name] != arg_value:
                return False
        
        return True
    
    def __repr__(self):
        agent_str = f"{self.agent_id}." if self.agent_id else ""
        args_str = ", ".join(f"{k}={v}" for k, v in self.arguments.items())
        return f"Transition({agent_str}{self.function_name}({args_str}))"


@dataclass
class PetriNet:
    """A Petri Net for multi-agent evaluation"""
    places: Dict[str, Place] = field(default_factory=dict)
    transitions: List[PetriTransition] = field(default_factory=list)
    initial_marking: Dict[str, Place] = field(default_factory=dict)
    
    def add_place(self, name: str, tokens: int = 0, capacity: Optional[int] = None) -> Place:
        """Add a place to the net"""
        place = Place(name, tokens, capacity)
        self.places[name] = place
        return place
    
    def add_transition(self, transition: PetriTransition):
        """Add a transition to the net"""
        self.transitions.append(transition)
    
    def get_initial_marking(self) -> Dict[str, Place]:
        """Get a copy of the initial marking"""
        import copy
        return copy.deepcopy(self.places)
    
    def find_enabled_transitions(self, marking: Dict[str, Place]) -> List[PetriTransition]:
        """Find all transitions enabled in current marking"""
        return [t for t in self.transitions if t.is_enabled(marking)]
    
    def find_matching_transition(
        self, 
        agent_id: str, 
        function_name: str, 
        arguments: Dict[str, Any]
    ) -> Optional[PetriTransition]:
        """Find transition matching an agent action"""
        for transition in self.transitions:
            if transition.matches_action(agent_id, function_name, arguments):
                return transition
        return None
    
    def __repr__(self):
        places_str = "\n  ".join(str(p) for p in self.places.values())
        trans_str = "\n  ".join(str(t) for t in self.transitions)
        return f"PetriNet(\n Places:\n  {places_str}\n Transitions:\n  {trans_str}\n)"