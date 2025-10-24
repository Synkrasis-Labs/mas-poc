import copy
from agents import Runner, trace
from farm_context import FarmContext
from farm_world import FarmingRover
import asyncio
from dotenv import load_dotenv
from agents_def import Rover



load_dotenv(override=True)
world = FarmingRover()
ctx = FarmContext.from_init_dict(copy.deepcopy(world._init_world_state))

PROMPT = ("Firsly, Unlock safety. Drive to plant C and harvest its fruit. "
          "Then take the load to the collection bin, empty the hopper, and return to base.")

async def main():
    with trace("Robot Farm"):
        result = await Runner.run(Rover, PROMPT, context=ctx)
        print(result.final_output)

if __name__ == '__main__':
    asyncio.run(main())