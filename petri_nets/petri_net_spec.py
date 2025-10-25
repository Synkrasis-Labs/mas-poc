# petri_nets/petri_net_spec.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any


@dataclass
class AgentConstraints:
    """Constraints for a single agent (like golden path but partial order)"""
    agent_id: str
    required_sequence: List[Tuple[str, Dict[str, Any]]]  # (function_name, args)
    optional_reads: Set[str] = field(default_factory=set)  # Read-only functions allowed anywhere


@dataclass
class ResourceConstraint:
    """Constraint on shared resources"""
    resource_name: str
    capacity: int  # How many agents can access simultaneously
    mutex_actions: List[str] = field(default_factory=list)  # Actions that require exclusive access


@dataclass
class CoordinationConstraint:
    """Constraint on agent coordination"""
    constraint_type: str  # "happens_before", "mutex", "sync"
    agent_1: str
    action_1: Tuple[str, Dict[str, Any]]  # (function_name, args)
    agent_2: Optional[str] = None
    action_2: Optional[Tuple[str, Dict[str, Any]]] = None


@dataclass
class PetriNetPrompt:
    """
    Specification of a multi-agent prompt as a Petri Net.
    This is analogous to the Prompt class in DFA, but for concurrent systems.
    """
    text: str  # Natural language prompt
    agents: List[str]  # List of agent IDs
    
    # Per-agent constraints (independent sequences)
    agent_constraints: Dict[str, AgentConstraints] = field(default_factory=dict)
    
    # Shared resource constraints
    resource_constraints: List[ResourceConstraint] = field(default_factory=list)
    
    # Inter-agent coordination constraints
    coordination_constraints: List[CoordinationConstraint] = field(default_factory=list)
    
    # The actual Petri Net (built from constraints)
    petri_net: Optional[Any] = None  # Will be PetriNet, but avoid circular import
    
    # Expected properties of valid execution
    expected_final_marking: Optional[Dict[str, int]] = None
    forbidden_markings: List[Dict[str, int]] = field(default_factory=list)
    
    def __post_init__(self):
        """Build Petri Net from constraints"""
        if self.petri_net is None:
            from petri_nets.petri_net_builder import build_petri_net_from_spec
            self.petri_net = build_petri_net_from_spec(self)