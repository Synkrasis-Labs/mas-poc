# prompts_registry.py
"""
Central task registry and helpers (get_task, list_tasks).

Add/remove tasks by editing the imports & TASKS list below.
"""

from typing import Dict, Any

# Import task modules
from tasks.two_rover_harvest import TASK_ID as ID_HARVEST, TASK_INFO as INFO_HARVEST
from tasks.sequential_dependency import TASK_ID as ID_SEQ, TASK_INFO as INFO_SEQ
from tasks.resource_bottleneck import TASK_ID as ID_BOTTLENECK, TASK_INFO as INFO_BOTTLENECK

# Build registry
TASK_REGISTRY: Dict[str, Dict[str, Any]] = {
    ID_HARVEST: INFO_HARVEST,
    ID_SEQ: INFO_SEQ,
    ID_BOTTLENECK: INFO_BOTTLENECK,
}

def get_task(task_id: str) -> Dict[str, Any]:
    """Get task info by ID (prompts, spec, agents, etc.)."""
    if task_id not in TASK_REGISTRY:
        raise ValueError(f"Unknown task: {task_id}. Available: {list(TASK_REGISTRY.keys())}")
    return TASK_REGISTRY[task_id]

def list_tasks() -> None:
    """Print all available tasks."""
    for tid, info in TASK_REGISTRY.items():
        print(f"\n{tid}:")
        print(f"  Name: {info['name']}")
        print(f"  Description: {info['description']}")
        print(f"  Agents: {', '.join(info['agents'])}")
        print(f"  Difficulty: {info['difficulty']}")
        print(f"  Coordination: {info['coordination_type']}")
