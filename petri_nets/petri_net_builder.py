# petri_nets/petri_net_builder.py
from typing import List
from petri_nets.petri_net import PetriNet, PetriTransition, TransitionType
from petri_nets.petri_net_spec import PetriNetPrompt, AgentConstraints, ResourceConstraint


def build_petri_net_from_spec(spec: PetriNetPrompt) -> PetriNet:
    """
    Build a Petri Net from a specification.
    This creates a modular net: per-agent subnets + shared resource places.
    """
    net = PetriNet()
    
    # 1. Add shared resource places
    for resource in spec.resource_constraints:
        net.add_place(
            name=f"{resource.resource_name}_available",
            tokens=resource.capacity,
            capacity=resource.capacity
        )
    
    # 2. Build per-agent subnets
    for agent_id in spec.agents:
        constraints = spec.agent_constraints.get(agent_id)
        if constraints:
            _build_agent_subnet(net, agent_id, constraints, spec.resource_constraints)
    
    # 3. Add coordination transitions
    for coord in spec.coordination_constraints:
        _add_coordination_constraint(net, coord)
    
    return net


def _build_agent_subnet(
    net: PetriNet,
    agent_id: str,
    constraints: AgentConstraints,
    resources: List[ResourceConstraint]
):
    """Build subnet for a single agent"""
    
    # Create agent state places (linearized state machine for this agent)
    for i in range(len(constraints.required_sequence) + 1):
        place_name = f"{agent_id}_state_{i}"
        tokens = 1 if i == 0 else 0  # Start in state 0
        net.add_place(place_name, tokens=tokens)
    
    # Create transitions for required sequence
    for i, (func_name, args) in enumerate(constraints.required_sequence):
        transition = PetriTransition(
            name=f"{agent_id}_{func_name}_{i}",
            agent_id=agent_id,
            function_name=func_name,
            arguments=args,
            input_places={f"{agent_id}_state_{i}": 1},
            output_places={f"{agent_id}_state_{i+1}": 1},
            transition_type=TransitionType.PROGRESS
        )
        
        # Check if this action requires a shared resource
        for resource in resources:
            if func_name in resource.mutex_actions:
                # This action needs to acquire the resource
                transition.input_places[f"{resource.resource_name}_available"] = 1
                transition.output_places[f"{resource.resource_name}_available"] = 1
        
        net.add_transition(transition)
    
    # Add read transitions (self-loops at any state)
    for read_func in constraints.optional_reads:
        for i in range(len(constraints.required_sequence) + 1):
            transition = PetriTransition(
                name=f"{agent_id}_{read_func}_read_{i}",
                agent_id=agent_id,
                function_name=read_func,
                arguments={},  # Reads typically don't have constrained args
                input_places={f"{agent_id}_state_{i}": 1},
                output_places={f"{agent_id}_state_{i}": 1},
                transition_type=TransitionType.READ
            )
            net.add_transition(transition)


def _add_coordination_constraint(net: PetriNet, coord):
    """Add coordination constraints (e.g., happens-before, mutex)"""
    # For MVP, we handle this implicitly through shared resource places
    # More complex coordination can be added later
    pass