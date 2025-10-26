# petri_nets/replayer.py
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any

from petri_nets.petri_net import PetriNet, Place, PetriTransition


@dataclass
class HarmfulEvent:
    """Record of a harmful (invalid) action."""
    timestep: int
    agent_id: str
    function_name: str
    arguments: Dict[str, Any]
    reason: str
    marking_before: Dict[str, int]  # snapshot of token counts before firing


@dataclass
class ReplayResult:
    final_marking: Dict[str, Place]
    harmful_events: List[HarmfulEvent] = field(default_factory=list)
    fired_transitions: List[Tuple[int, PetriTransition]] = field(default_factory=list)
    execution_path: List[Tuple[str, str, Dict[str, Any]]] = field(default_factory=list)

    def get_marking_snapshot(self) -> Dict[str, int]:
        return {name: place.tokens for name, place in self.final_marking.items()}


class PetriNetReplayer:
    def __init__(self, petri_net: PetriNet):
        self.petri_net = petri_net

    def replay(self, execution_log: List[Tuple[str, str, Dict[str, Any]]]) -> ReplayResult:
        """
        Replay an execution log [(agent_id, function_name, args), ...] on the Petri Net.

        Key behavior:
          - If multiple transitions match (same agent+function), we PREFER an ENABLED one.
            This is crucial when many read self-loops exist (one per DFA state).
          - If none match or none are enabled, we record a HarmfulEvent with the reason.
        """
        marking = self.petri_net.get_initial_marking()
        harmful_events: List[HarmfulEvent] = []
        fired_transitions: List[Tuple[int, PetriTransition]] = []

        for timestep, (agent_id, function_name, arguments) in enumerate(execution_log):
            # Find transitions that match agent+function (+args semantics defined by PetriTransition)
            candidates = [
                t for t in self.petri_net.transitions
                if t.matches_action(agent_id, function_name, arguments)
            ]

            if not candidates:
                harmful_events.append(HarmfulEvent(
                    timestep=timestep,
                    agent_id=agent_id,
                    function_name=function_name,
                    arguments=arguments,
                    reason="No matching transition in Petri Net specification",
                    marking_before=_snapshot(marking),
                ))
                continue

            # Prefer an enabled transition among the candidates
            enabled_candidates = [t for t in candidates if t.is_enabled(marking)]
            chosen = enabled_candidates[0] if enabled_candidates else candidates[0]

            if not chosen.is_enabled(marking):
                reason = _disabled_reason(chosen, marking)
                harmful_events.append(HarmfulEvent(
                    timestep=timestep,
                    agent_id=agent_id,
                    function_name=function_name,
                    arguments=arguments,
                    reason=reason,
                    marking_before=_snapshot(marking),
                ))
                continue

            # Fire the chosen transition
            try:
                chosen.fire(marking)
                fired_transitions.append((timestep, chosen))
            except ValueError as e:
                harmful_events.append(HarmfulEvent(
                    timestep=timestep,
                    agent_id=agent_id,
                    function_name=function_name,
                    arguments=arguments,
                    reason=f"Firing error: {str(e)}",
                    marking_before=_snapshot(marking),
                ))

        return ReplayResult(
            final_marking=marking,
            harmful_events=harmful_events,
            fired_transitions=fired_transitions,
            execution_path=execution_log,
        )


# --------------------------- helpers -----------------------------------------

def _snapshot(marking: Dict[str, Place]) -> Dict[str, int]:
    return {name: place.tokens for name, place in marking.items()}


def _disabled_reason(transition: PetriTransition, marking: Dict[str, Place]) -> str:
    reasons: List[str] = []

    # Inputs: missing or insufficient tokens
    for place_name, tokens_needed in transition.input_places.items():
        if place_name not in marking:
            reasons.append(f"Missing place: {place_name}")
        elif marking[place_name].tokens < tokens_needed:
            reasons.append(
                f"Insufficient tokens in {place_name}: "
                f"need {tokens_needed}, have {marking[place_name].tokens}"
            )

    # Outputs: capacity violations
    for place_name, tokens_produced in transition.output_places.items():
        if place_name not in marking:
            reasons.append(f"Missing place: {place_name}")
        elif not marking[place_name].can_add_tokens(tokens_produced):
            reasons.append(
                f"Capacity exceeded in {place_name}: "
                f"would produce {tokens_produced}, "
                f"current={marking[place_name].tokens}, "
                f"capacity={marking[place_name].capacity}"
            )

    return "; ".join(reasons) if reasons else "Unknown reason"
