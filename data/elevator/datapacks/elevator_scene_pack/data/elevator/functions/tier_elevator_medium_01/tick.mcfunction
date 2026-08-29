# Tick logic for scene: tier_elevator_medium_01
execute if block 460 -58 7 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:air
execute if block 460 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:air
execute if block 460 -58 9 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:air
execute if block 461 -58 7 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:air
execute if block 461 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:air
execute if block 461 -58 9 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:air
execute if block 462 -58 7 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:air
execute if block 462 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:air
execute if block 462 -58 9 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:air
execute unless block 460 -58 7 minecraft:stone_pressure_plate[powered=true] unless block 460 -58 8 minecraft:stone_pressure_plate[powered=true] unless block 460 -58 9 minecraft:stone_pressure_plate[powered=true] unless block 461 -58 7 minecraft:stone_pressure_plate[powered=true] unless block 461 -58 8 minecraft:stone_pressure_plate[powered=true] unless block 461 -58 9 minecraft:stone_pressure_plate[powered=true] unless block 462 -58 7 minecraft:stone_pressure_plate[powered=true] unless block 462 -58 8 minecraft:stone_pressure_plate[powered=true] unless block 462 -58 9 minecraft:stone_pressure_plate[powered=true] run fill 460 -58 12 461 -56 12 minecraft:light_gray_concrete
