# petri_nets/petri_net_builder.py
from typing import Dict, List, Any
from petri_nets.petri_net import PetriNet, PetriTransition, TransitionType
from petri_nets.petri_net_spec import PetriNetPrompt, AgentConstraints


def build_petri_net_from_spec(spec: PetriNetPrompt) -> PetriNet:
    """
    Build a Petri Net from the given specification.

    Structure (per our MAS-CORE/DFAs design):
      - Shared resource places:
          <resource>_available  (tokens = capacity)
          <resource>_reserved_by_<agent> (per agent, capacity=1)
      - Per-agent DFA state places:
          <agent>_state_0 ... <agent>_state_N
          (initial tokens: 1 in each <agent>_state_0)
      - Required actions advance DFA i -> i+1, with resource arcs:
          * reserve_plant / reserve_station: available -> reserved_by_agent
          * release_plant / release_station: reserved_by_agent -> available
          * mutex actions (harvest_fruit, water_plant, spray_pesticide, dump_hopper, recharge):
              require reserved_by_agent and SELF-LOOP that reservation (consume+produce)
      - Optional reads are neutral self-loops on every agent state:
          consume+produce same state token; no resource arcs.
    """
    net = PetriNet()

    # -------------------------------------------------------------------------
    # 1) Shared resources: availability & per-agent reservation places
    # -------------------------------------------------------------------------
    # Availability places with initial tokens = capacity
    for rc in spec.resource_constraints:
        net.add_place(
            name=f"{rc.resource_name}_available",
            tokens=rc.capacity,
            capacity=rc.capacity,
        )

    # Reservation places (per agent, capacity 1, start empty)
    for rc in spec.resource_constraints:
        for agent_id in spec.agents:
            net.add_place(
                name=f"{rc.resource_name}_reserved_by_{agent_id}",
                tokens=0,
                capacity=1,
            )

    # Map actions → resources (as declared in the spec)
    # e.g., "dump_hopper" → ["collection_bin"]
    action_to_resources: Dict[str, List[str]] = {}
    for rc in spec.resource_constraints:
        for act in rc.mutex_actions:
            action_to_resources.setdefault(act, []).append(rc.resource_name)

    # -------------------------------------------------------------------------
    # 2) Per-agent DFA subnets
    # -------------------------------------------------------------------------
    for agent_id in spec.agents:
        constraints = spec.agent_constraints.get(agent_id)
        if not constraints:
            continue
        _build_agent_subnet(
            net=net,
            agent_id=agent_id,
            constraints=constraints,
            action_to_resources=action_to_resources,
        )

    # -------------------------------------------------------------------------
    # 3) Coordination constraints hook (unused in this task)
    # -------------------------------------------------------------------------
    for coord in getattr(spec, "coordination_constraints", []):
        _add_coordination_constraint(net, coord)

    return net


def _build_agent_subnet(
    net: PetriNet,
    agent_id: str,
    constraints: AgentConstraints,
    action_to_resources: Dict[str, List[str]],
) -> None:
    """
    Build one agent's DFA + optional read self-loops and resource arcs.
    """
    num_steps = len(constraints.required_sequence)

    # --- Agent DFA places; 1 token in state_0
    for i in range(num_steps + 1):
        net.add_place(
            name=f"{agent_id}_state_{i}",
            tokens=1 if i == 0 else 0,
            capacity=1,
        )

    # --- Required sequence transitions (advance state_i -> state_{i+1})
    for i, (func_name, args) in enumerate(constraints.required_sequence):
        # Base DFA advance
        t = PetriTransition(
            name=f"{agent_id}__step_{i}__{func_name}",
            agent_id=agent_id,
            function_name=func_name,
            arguments=dict(args),  # exact match on expected args
            input_places={f"{agent_id}_state_{i}": 1},
            output_places={f"{agent_id}_state_{i+1}": 1},
            transition_type=TransitionType.PROGRESS,
        )

        # --- Resource wiring per action type ---------------------------------
        # 1) Plant reservation / release
        if func_name == "reserve_plant":
            plant_id = args.get("plant_id")
            if plant_id is not None:
                t.input_places[f"{plant_id}_available"] = 1
                t.output_places[f"{plant_id}_reserved_by_{agent_id}"] = 1

        elif func_name == "release_plant":
            plant_id = args.get("plant_id")
            if plant_id is not None:
                t.input_places[f"{plant_id}_reserved_by_{agent_id}"] = 1
                t.output_places[f"{plant_id}_available"] = 1

        # 2) Station reservation / release
        elif func_name == "reserve_station":
            station = args.get("station_name")
            if station is not None:
                t.input_places[f"{station}_available"] = 1
                t.output_places[f"{station}_reserved_by_{agent_id}"] = 1

        elif func_name == "release_station":
            station = args.get("station_name")
            if station is not None:
                t.input_places[f"{station}_reserved_by_{agent_id}"] = 1
                t.output_places[f"{station}_available"] = 1

        # 3) Mutex actions: require owned reservation and keep it (SELF-LOOP)
        #    - Plants: harvest_fruit / water_plant / spray_pesticide → need plant_id
        #    - Stations: dump_hopper / recharge → need station (if arg omitted, infer unique)
        if func_name in action_to_resources:
            if func_name in {"harvest_fruit", "water_plant", "spray_pesticide"}:
                plant_id = args.get("plant_id")
                if plant_id is not None:
                    # self-loop reservation token (require & re-produce)
                    t.input_places[f"{plant_id}_reserved_by_{agent_id}"] = (
                        t.input_places.get(f"{plant_id}_reserved_by_{agent_id}", 0) + 1
                    )
                    t.output_places[f"{plant_id}_reserved_by_{agent_id}"] = (
                        t.output_places.get(f"{plant_id}_reserved_by_{agent_id}", 0) + 1
                    )
            else:
                # Station-like (dump_hopper, recharge)
                station = args.get("station_name")
                if station is None:
                    # If spec associates exactly one station with this action, use it
                    resources = action_to_resources.get(func_name, [])
                    if len(resources) == 1:
                        station = resources[0]
                if station is not None:
                    t.input_places[f"{station}_reserved_by_{agent_id}"] = (
                        t.input_places.get(f"{station}_reserved_by_{agent_id}", 0) + 1
                    )
                    t.output_places[f"{station}_reserved_by_{agent_id}"] = (
                        t.output_places.get(f"{station}_reserved_by_{agent_id}", 0) + 1
                    )

        net.add_transition(t)

    # --- Optional reads: neutral self-loops at every state -------------------
    for read_func in constraints.optional_reads:
        for i in range(num_steps + 1):
            t_read = PetriTransition(
                name=f"{agent_id}__read_s{i}__{read_func}",
                agent_id=agent_id,
                function_name=read_func,
                arguments={},  # reads are treated as unconstrained by args
                input_places={f"{agent_id}_state_{i}": 1},
                output_places={f"{agent_id}_state_{i}": 1},
                transition_type=TransitionType.READ,
            )
            net.add_transition(t_read)


def _add_coordination_constraint(net: PetriNet, coord: Any) -> None:
    """
    Hook: implement explicit temporal constraints if needed.
    For the two_rover_harvest task, mutual exclusion is enforced via resources,
    so nothing to do here.
    """
    return
