# run.py
import copy
import asyncio
from agents import Runner, trace
from farm_context import FarmContext
from farm_world import FarmingRover
from agents_def import Rover1, Rover2, Rover3
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv(override=True)


async def run_rover_agent(rover_id: str, agent, prompt: str, world_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a single rover agent with its own context.
    
    Args:
        rover_id: The ID of the rover
        agent: The agent to run
        prompt: The task prompt for this rover
        world_state: The shared world state dictionary
    
    Returns:
        Dictionary containing the result and final state
    """
    # Create a context for this specific rover
    ctx = FarmContext.from_init_dict(copy.deepcopy(world_state), rover_id)
    
    print(f"\n{'='*80}")
    print(f"Starting {rover_id}: {prompt}")
    print(f"{'='*80}\n")
    
    with trace(f"{rover_id}_task"):
        result = await Runner.run(agent, prompt, context=ctx, max_turns=30)
        
        print(f"\n{'='*80}")
        print(f"{rover_id} completed task")
        print(f"Final output: {result.final_output}")
        print(f"Final state: {ctx.short_summary()}")
        print(f"{'='*80}\n")
        
        return {
            "rover_id": rover_id,
            "result": result,
            "final_state": ctx.my_rover_snapshot(),
            "world_state": ctx.snapshot(),
        }


async def run_sequential_mas():
    """
    Run multiple rover agents SEQUENTIALLY (one after another).
    This ensures no actual conflicts but tests the coordination mechanisms.
    """
    print("\n" + "="*80)
    print("SEQUENTIAL MULTI-AGENT SYSTEM EXECUTION")
    print("="*80 + "\n")
    
    world = FarmingRover()
    shared_world_state = copy.deepcopy(world._init_world_state)
    
    # Task assignments for each rover
    tasks = {
        "rover_1": (
            "Your task: Check available ripe plants. Reserve and harvest plant_A if ripe. "
            "Then deliver the harvest to the collection bin and return home. "
            "Use proper coordination - reserve resources before using them."
        ),
        "rover_2": (
            "Your task: Check available plants with pests. Reserve and spray pesticide on plant_B. "
            "If you need to refill pesticide, go to the pesticide station first. "
            "Use proper coordination - reserve resources before using them."
        ),
        "rover_3": (
            "Your task: Check available ripe plants. Reserve and harvest plant_C if ripe. "
            "Then deliver the harvest to the collection bin and return home. "
            "Use proper coordination - reserve resources before using them."
        ),
    }
    
    results = []
    
    # Run rover_1
    result1 = await run_rover_agent("rover_1", Rover1, tasks["rover_1"], shared_world_state)
    # Update shared world state from rover_1's final state
    shared_world_state = result1["world_state"]
    results.append(result1)
    
    # Run rover_2
    result2 = await run_rover_agent("rover_2", Rover2, tasks["rover_2"], shared_world_state)
    shared_world_state = result2["world_state"]
    results.append(result2)
    
    # Run rover_3
    result3 = await run_rover_agent("rover_3", Rover3, tasks["rover_3"], shared_world_state)
    shared_world_state = result3["world_state"]
    results.append(result3)
    
    # Print final summary
    print("\n" + "="*80)
    print("FINAL MULTI-AGENT SYSTEM SUMMARY")
    print("="*80 + "\n")
    
    for result in results:
        ctx = FarmContext.from_init_dict(shared_world_state, result["rover_id"])
        print(f"{result['rover_id']}: {ctx.short_summary()}")
    
    print("\n--- Task Completion Log ---")
    final_ctx = FarmContext.from_init_dict(shared_world_state, "rover_1")
    for entry in final_ctx.world_state.task_log:
        print(f"  [{entry.get('rover_id')}] {entry.get('task')} at {entry.get('timestamp')}")
    
    print("\n--- Conflict Log ---")
    if final_ctx.world_state.conflict_log:
        for entry in final_ctx.world_state.conflict_log:
            print(f"  {entry}")
    else:
        print("  No conflicts detected")
    
    print("\n--- Plant Status ---")
    for plant_id, plant in final_ctx.world_state.plants.items():
        status = "harvested" if not plant.has_fruit and plant.ripeness >= 0.7 else "available"
        pest_status = "pest-free" if not plant.pest else "has-pest"
        print(f"  {plant_id}: {status}, {pest_status}, reserved_by={plant.reserved_by}")
    
    print("\n" + "="*80 + "\n")


async def run_concurrent_mas():
    """
    Run multiple rover agents CONCURRENTLY (at the same time).
    WARNING: This may lead to race conditions with the current implementation.
    For true concurrency, you'd need proper locking mechanisms.
    """
    print("\n" + "="*80)
    print("CONCURRENT MULTI-AGENT SYSTEM EXECUTION")
    print("WARNING: This demo shows concurrent execution but may have race conditions")
    print("For production, implement proper locking/synchronization")
    print("="*80 + "\n")
    
    world = FarmingRover()
    shared_world_state = copy.deepcopy(world._init_world_state)
    
    # Task assignments
    tasks = {
        "rover_1": "Harvest all ripe plants (plant_A, plant_C, plant_E). Deliver to collection bin.",
        "rover_2": "Spray pesticide on all plants with pests (plant_B, plant_D, plant_F).",
        "rover_3": "Water any plants with moisture below 0.35 (plant_C, plant_D).",
    }
    
    # Run all rovers concurrently
    results = await asyncio.gather(
        run_rover_agent("rover_1", Rover1, tasks["rover_1"], shared_world_state),
        run_rover_agent("rover_2", Rover2, tasks["rover_2"], shared_world_state),
        run_rover_agent("rover_3", Rover3, tasks["rover_3"], shared_world_state),
    )
    
    print("\n" + "="*80)
    print("CONCURRENT EXECUTION COMPLETED")
    print("Note: Results may vary due to race conditions")
    print("="*80 + "\n")
    
    for result in results:
        print(f"\n{result['rover_id']} final state:")
        print(f"  {FarmContext.from_init_dict(result['world_state'], result['rover_id']).short_summary()}")


async def run_single_rover_demo():
    """
    Run a single rover for testing (similar to original single-agent system).
    """
    print("\n" + "="*80)
    print("SINGLE ROVER DEMO")
    print("="*80 + "\n")
    
    world = FarmingRover()
    shared_world_state = copy.deepcopy(world._init_world_state)
    
    # prompt = (
    #     "Unlock safety. Reserve and drive to plant_C, harvest its fruit. "
    #     "Then reserve the collection bin, take the load there, empty the hopper, "
    #     "release the station, and return to home base. Use proper coordination."
    # )
    
    prompt = "Water plant_C"
    
    result = await run_rover_agent("rover_1", Rover1, prompt, shared_world_state)
    
    print("\nTask Log:")
    ctx = FarmContext.from_init_dict(result["world_state"], "rover_1")
    for entry in ctx.world_state.task_log:
        print(f"  {entry}")


async def main():
    """
    Main entry point - choose which demo to run.
    """
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = "sequential"  # Default mode
    
    if mode == "single":
        await run_single_rover_demo()
    elif mode == "concurrent":
        await run_concurrent_mas()
    else:  # sequential
        await run_sequential_mas()


if __name__ == '__main__':
    print("\nUsage: python run.py [mode]")
    print("  mode: 'single' | 'sequential' | 'concurrent'")
    print("  default: sequential\n")
    
    asyncio.run(main())