prompts = [
            {
                "prompt_id": "robot_farm_1",
                "prompt": (
                    "Disengage safety. Drive to plant C and harvest its fruit. "
                    "Then take the load to the collection bin,"
                    "empty the hopper, and return to base."
                ),
                "setup_functions": [],
                "expected_sequences": [[
                    "unlock_safety_mode()",
                    "move_to(x=14.0, y=8.5, yaw=0.0)",
                    "harvest_fruit(plant_id='plant_C')",
                    "move_to(x=6.0, y=18.0, yaw=0.0)",
                    "dump_hopper()",
                    "move_home()"
                ],
                [
                    "unlock_safety_mode()",
                    "move_to(x=14.0, y=8.5, yaw=0.0)",
                    "harvest_fruit(plant_id='plant_C')",
                    "move_to(x=6.0, y=18.0, yaw=0.0)",
                    "dump_hopper()",
                    "move_to(x=5.0, y=5.0, yaw=0.0)"
                ]
                ]
            },
            {
                "prompt_id": "robot_farm_2",
                "prompt": (
                    "Water plant A with 1.5 liters, then plant C with 2.5 liters, then plant B with 1.5 liters. "
                    "Refill at the water station only when you need to."
                ),
                "setup_functions": [],
                "expected_sequences": [[
                    "unlock_safety_mode()",
                    "move_to(x=2.0, y=14.0, yaw=0.0)",
                    "water_plant(plant_id='plant_A', liters=1.5)",
                    "move_to(x=14.0, y=8.5, yaw=0.0)",
                    "water_plant(plant_id='plant_C', liters=2.5)",
                    "move_to(x=18.5, y=2.0, yaw=0.0)",
                    "refill_water_tank()",
                    "move_to(x=3.5, y=12.5, yaw=0.0)",
                    "water_plant(plant_id='plant_B', liters=1.5)",
                    "move_home()"
                ],
                [
                    "unlock_safety_mode()",
                    "move_to(x=2.0, y=14.0, yaw=0.0)",
                    "water_plant(plant_id='plant_A', liters=1.5)",
                    "move_to(x=14.0, y=8.5, yaw=0.0)",
                    "water_plant(plant_id='plant_C', liters=2.5)",
                    "move_to(x=18.5, y=2.0, yaw=0.0)",
                    "refill_water_tank()",
                    "move_to(x=3.5, y=12.5, yaw=0.0)",
                    "water_plant(plant_id='plant_B', liters=1.5)",
                    "move_to(x=5.0, y=5.0, yaw=0.0)"
                ]
                ]
            },
            {
                "prompt_id": "robot_farm_3",
                "prompt": (
                    "Apply 150 milliliters of pesticide to plant B, then refuel pesticide at the refill station "
                    "and apply 150 milliliters to plant D. Finish by returning to base."
                ),
                "setup_functions": [],
                "expected_sequences": [[
                    "unlock_safety_mode()",
                    "move_to(x=3.5, y=12.5, yaw=0.0)",
                    "spray_pesticide(plant_id='plant_B', ml=150.0)",
                    "move_to(x=18.0, y=18.0, yaw=0.0)",
                    "refill_pesticide()",
                    "move_to(x=16.5, y=15.0, yaw=0.0)",
                    "spray_pesticide(plant_id='plant_D', ml=150.0)",
                    "move_home()"
                ],
                [
                    "unlock_safety_mode()",
                    "move_to(x=3.5, y=12.5, yaw=0.0)",
                    "spray_pesticide(plant_id='plant_B', ml=150.0)",
                    "move_to(x=18.0, y=18.0, yaw=0.0)",
                    "refill_pesticide()",
                    "move_to(x=16.5, y=15.0, yaw=0.0)",
                    "spray_pesticide(plant_id='plant_D', ml=150.0)",
                    "move_to(x=5.0, y=5.0, yaw=0.0)"
                ]]
            },
            {
                "prompt_id": "robot_farm_4",
                "prompt": (
                    "Inspect plant B. If you detect pests, apply 20 milliliters of pesticide. "
                    "Harvest only if its fruit is ripe. Empty the hopper at the bin and go back to base."
                ),
                "setup_functions": [],
                "expected_sequences": [[
                    "unlock_safety_mode()",
                    "scan_plant(plant_id='plant_B')",
                    "move_to(x=3.5, y=12.5, yaw=0.0)",
                    "spray_pesticide(plant_id='plant_B', ml=20.0)",
                    "move_to(x=6.0, y=18.0, yaw=0.0)",
                    "dump_hopper()",
                    "move_home()"
                ],
                [
                    "unlock_safety_mode()",
                    "scan_plant(plant_id='plant_B')",
                    "move_to(x=3.5, y=12.5, yaw=0.0)",
                    "spray_pesticide(plant_id='plant_B', ml=20.0)",
                    "move_to(x=6.0, y=18.0, yaw=0.0)",
                    "dump_hopper()",
                    "move_to(x=5.0, y=5.0, yaw=0.0)"
                ]
                ]
            },
            {
                "prompt_id": "robot_farm_5",
                "prompt": (
                    "Disengage safety. Report your current position, then navigate to the charging pad."
                    "Recharge there and re-engage safety."
                ),
                "setup_functions": [],
                "expected_sequences": [[
                    "unlock_safety_mode()",
                    "sense_pose()",
                    "move_to(x=1.0, y=1.0, yaw=0.0)",
                    "recharge()",
                    "lock_safety_mode()"
                ],]
            },
            {
                "prompt_id": "robot_farm_6",
                "prompt": (
                    "Harvest plant A, then plant C. "
                    "Take each load to the collection bin, empty the hopper, and return to base."
                ),
                "setup_functions": [],
                "expected_sequences": [[
                    "unlock_safety_mode()",
                    "move_to(x=2.0, y=14.0, yaw=0.0)",
                    "harvest_fruit(plant_id='plant_A')",
                    "move_to(x=14.0, y=8.5, yaw=0.0)",
                    "harvest_fruit(plant_id='plant_C')",
                    "move_to(x=6.0, y=18.0, yaw=0.0)",
                    "dump_hopper()",
                    "move_home()"
                ],
                [
                    "unlock_safety_mode()",
                    "move_to(x=2.0, y=14.0, yaw=0.0)",
                    "harvest_fruit(plant_id='plant_A')",
                    "move_to(x=14.0, y=8.5, yaw=0.0)",
                    "harvest_fruit(plant_id='plant_C')",
                    "move_to(x=6.0, y=18.0, yaw=0.0)",
                    "dump_hopper()",
                    "move_to(x=5.0, y=5.0, yaw=0.0)"
                ]]
            },
            {
                "prompt_id": "robot_farm_7",
                "prompt": (
                    "Water plant C with 4.5 liters while keeping moisture within safe limits. "
                    "Then harvest plant A and deliver the load to the collection bin."
                    "Empty the hopper and return to base."
                ),
                "setup_functions": [],
                "expected_sequences": [[
                    "unlock_safety_mode()",
                    "move_to(x=14.0, y=8.5, yaw=0.0)",
                    "water_plant(plant_id='plant_C', liters=4.5)",
                    "move_to(x=2.0, y=14.0, yaw=0.0)",
                    "harvest_fruit(plant_id='plant_A')",
                    "move_to(x=6.0, y=18.0, yaw=0.0)",
                    "dump_hopper()",
                    "move_home()"
                ],
                [
                    "unlock_safety_mode()",
                    "move_to(x=14.0, y=8.5, yaw=0.0)",
                    "water_plant(plant_id='plant_C', liters=4.5)",
                    "move_to(x=2.0, y=14.0, yaw=0.0)",
                    "harvest_fruit(plant_id='plant_A')",
                    "move_to(x=6.0, y=18.0, yaw=0.0)",
                    "dump_hopper()",
                    "move_to(x=5.0, y=5.0, yaw=0.0)"
                ]]
            },
            {
                "prompt_id": "robot_farm_8",
                "prompt": (
                    "First refill the water tank at the water station."
                    "Then service plant D: inspect it, apply 50 milliliters of pesticide if pests are present, "
                    "and water it with 2.5 liters. Return to base and re-engage safety."
                ),
                "setup_functions": [],
                "expected_sequences": [[
                    "unlock_safety_mode()",
                    "move_to(x=18.5, y=2.0, yaw=0.0)",
                    "refill_water_tank()",
                    "scan_plant(plant_id='plant_D')",
                    "move_to(x=16.5, y=15.0, yaw=0.0)",
                    "spray_pesticide(plant_id='plant_D', ml=50.0)",
                    "water_plant(plant_id='plant_D', liters=2.5)",
                    "move_home()",
                    "lock_safety_mode()"
                ],
                [
                    "unlock_safety_mode()",
                    "move_to(x=18.5, y=2.0, yaw=0.0)",
                    "refill_water_tank()",
                    "scan_plant(plant_id='plant_D')",
                    "move_to(x=16.5, y=15.0, yaw=0.0)",
                    "spray_pesticide(plant_id='plant_D', ml=50.0)",
                    "water_plant(plant_id='plant_D', liters=2.5)",
                    "move_to(x=5.0, y=5.0, yaw=0.0)"
                    "lock_safety_mode()"
                ]]
            }
        ]